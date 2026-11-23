
from __future__ import annotations

from statistics import median

from smartlane.models import (
    Incident,
    IncidentSeverity,
    IncidentType,
)


class CollisionDetector:
    """
    Detect possible POV collision events using:
    - Rapid apparent expansion of a tracked lead vehicle.
    - Sustained POV stationary motion shortly afterward.

    Produces candidates, not confirmed collision or fault findings.
    """

    def __init__(
        self,
        expansion_ratio: float = 1.8,
        minimum_area_increase: float = 0.02,
        baseline_window_seconds: float = 0.9,
        minimum_baseline_samples: int = 5,
        stationary_confirmation_seconds: float = 0.35,
        stationary_search_seconds: float = 4.0,
    ) -> None:
        self.expansion_ratio = expansion_ratio
        self.minimum_area_increase = minimum_area_increase
        self.baseline_window_seconds = baseline_window_seconds
        self.minimum_baseline_samples = minimum_baseline_samples
        self.stationary_confirmation_seconds = (
            stationary_confirmation_seconds
        )
        self.stationary_search_seconds = stationary_search_seconds

    def analyze(
        self,
        tracking_output,
        motion_state_results: dict,
    ) -> list[Incident]:

        width = tracking_output.metadata.width
        height = tracking_output.metadata.height
        fps = tracking_output.metadata.fps

        if width <= 0 or height <= 0 or fps <= 0:
            return []

        # Allow minor timestamp variation while rejecting meaningful gaps.
        max_stationary_gap = 1.5 / fps

        trajectories = {}
        identity_track_ids = {}

        for frame in tracking_output.frame_tracks:
            timestamp = frame.timestamp_seconds

            for vehicle in frame.vehicles:
                bbox = vehicle.bbox
                track_id = vehicle.track_id

                identity_id = (
                    vehicle.identity_id
                    if vehicle.identity_id is not None
                    else tracking_output.identity_map.get(track_id, track_id)
                )

                identity_track_ids.setdefault(identity_id, set()).add(track_id)


                center_x = bbox.center_x / width
                center_y = bbox.center_y / height
                box_width = bbox.width / width
                box_height = bbox.height / height
                area = box_width * box_height

                if not (
                    0.30 <= center_x <= 0.70
                    and 0.40 <= center_y <= 0.95
                    and 0.005 <= area <= 0.15
                ):
                    continue

                trajectories.setdefault(identity_id, []).append({
                    "frame_number": frame.frame_number,
                    "timestamp": timestamp,
                    "area": area,
                    "track_id": track_id,
                })

        expansion_candidates = []

        for identity_id, observations in trajectories.items():
            observations.sort(key=lambda item: item["timestamp"])

            raw_track_ids = sorted(
                identity_track_ids.get(
                    identity_id,
                    {item["track_id"] for item in observations},
                )
            )

            for current in observations:
                timestamp = current["timestamp"]

                previous = [
                    item["area"]
                    for item in observations
                    if (
                        timestamp - self.baseline_window_seconds
                        <= item["timestamp"]
                        < timestamp - 0.15
                    )
                ]

                if len(previous) < self.minimum_baseline_samples:
                    continue

                baseline_area = median(previous)
                current_area = current["area"]

                if baseline_area <= 0:
                    continue

                ratio = current_area / baseline_area
                increase = current_area - baseline_area

                if (
                    ratio >= self.expansion_ratio
                    and increase >= self.minimum_area_increase
                ):
                    expansion_candidates.append({
                        "identity_id": identity_id,
                        "raw_track_ids": raw_track_ids,
                        "track_id": current["track_id"],
                        "frame_number": current["frame_number"],
                        "timestamp": timestamp,
                        "baseline_area": baseline_area,
                        "expanded_area": current_area,
                        "expansion_ratio": ratio,
                    })
                    break

        if not expansion_candidates:
            return []

        states = motion_state_results.get("measurements", [])

        stationary_states = sorted(
            [
                item
                for item in states
                if (
                    item.get("reliable", False)
                    and item.get("motion_state_candidate") == "stationary"
                    and isinstance(
                        item.get("timestamp_seconds"), (int, float)
                    )
                )
            ],
            key=lambda item: item["timestamp_seconds"],
        )

        for candidate in sorted(
            expansion_candidates,
            key=lambda item: item["timestamp"],
        ):
            onset = candidate["timestamp"]
            search_end = onset + self.stationary_search_seconds

            relevant = [
                item
                for item in stationary_states
                if onset <= item["timestamp_seconds"] <= search_end
            ]

            # Find a continuous run of reliable stationary measurements.
            run_start = None
            previous = None
            confirmation = None

            for item in relevant:
                timestamp = item["timestamp_seconds"]

                if (
                    previous is None
                    or timestamp - previous["timestamp_seconds"]
                    > max_stationary_gap
                ):
                    run_start = item

                duration = (
                    timestamp - run_start["timestamp_seconds"]
                )

                if duration >= self.stationary_confirmation_seconds:
                    confirmation = {
                        "start": run_start,
                        "end": item,
                        "duration": duration,
                    }
                    break

                previous = item

            if confirmation is None:
                continue

            first = confirmation["start"]
            last = confirmation["end"]
            actual_duration = confirmation["duration"]

            return [
                Incident(
                    incident_id="collision_candidate_001",
                    start_frame=candidate["frame_number"],
                    end_frame=last["frame_number"],
                    start_time_seconds=onset,
                    end_time_seconds=last["timestamp_seconds"],
                    involved_vehicle_ids=candidate["raw_track_ids"],
                    incident_type=IncidentType.COLLISION_CANDIDATE,
                    severity=IncidentSeverity.UNKNOWN,
                    confidence=None,
                    evidence={
                        "lead_vehicle_identity_id": (
                            candidate["identity_id"]
                        ),
                        "lead_vehicle_track_id": candidate["track_id"],
                        "lead_vehicle_raw_track_ids": (
                            candidate["raw_track_ids"]
                        ),
                        "lead_vehicle_area_before": (
                            candidate["baseline_area"]
                        ),
                        "lead_vehicle_area_after": (
                            candidate["expanded_area"]
                        ),
                        "lead_vehicle_expansion_ratio": (
                            candidate["expansion_ratio"]
                        ),
                        "expansion_timestamp": onset,
                        "stationary_run_start_timestamp": (
                            first["timestamp_seconds"]
                        ),
                        "stationary_confirmation_timestamp": (
                            last["timestamp_seconds"]
                        ),
                        "stationary_confirmation_duration_seconds": (
                            actual_duration
                        ),
                        "stationary_measurement_count": (
                            relevant.index(last) + 1
                        ),
                        "confidence_status": "unavailable_uncalibrated",
                        "detection_basis": [
                            "rapid_lead_vehicle_bbox_expansion",
                            "continuous_reliable_pov_stationary_state",
                        ],
                        "limitations": [
                            "Bounding-box expansion is an image-space proxy.",
                            "Stationary motion is not proof of collision.",
                            "Track identity may be affected by occlusion or detector errors.",
                            "Confidence is not calibrated.",
                            "Collision responsibility is not assessed.",
                        ],
                    },
                )
            ]

        return []
