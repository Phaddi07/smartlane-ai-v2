
from __future__ import annotations

from smartlane.models import (
    BehaviorEvent,
    BehaviorSubject,
    BehaviorType,
)


class FollowingAnalyzer:
    """
    Selects plausible lead-vehicle candidates using image-space
    position and apparent bounding-box size.

    Stops candidate segments after sustained stationary-state evidence.

    Does not confirm lane membership, physical distance,
    headway, or unsafe following.
    """

    def __init__(
        self,
        min_observations: int = 5,
        min_duration_seconds: float = 0.5,
        max_gap_frames: int = 2,
        horizontal_corridor: tuple[float, float] = (0.30, 0.70),
        stationary_persistence_seconds: float = 0.5,
        max_motion_state_gap_seconds: float = 0.20,
    ) -> None:
        self.min_observations = min_observations
        self.min_duration_seconds = min_duration_seconds
        self.max_gap_frames = max_gap_frames
        self.horizontal_corridor = horizontal_corridor
        self.stationary_persistence_seconds = (
            stationary_persistence_seconds
        )
        self.max_motion_state_gap_seconds = (
            max_motion_state_gap_seconds
        )

    def analyze(
        self,
        tracking_output,
        motion_state_results: dict | None = None,
    ) -> list[BehaviorEvent]:

        width = tracking_output.metadata.width
        height = tracking_output.metadata.height

        if width <= 0 or height <= 0:
            raise ValueError("Video dimensions must be positive.")

        stationary_frames = set()

        if motion_state_results:
            measurements = motion_state_results.get("measurements", [])

            stationary_start = None
            stationary_run_frames = []
            previous_timestamp = None

            for item in measurements:
                timestamp = item.get("timestamp_seconds")
                frame_number = item.get("frame_number")

                if (
                    not item.get("reliable", False)
                    or timestamp is None
                    or frame_number is None
                    or (
                        previous_timestamp is not None
                        and timestamp - previous_timestamp
                        > self.max_motion_state_gap_seconds
                    )
                ):
                    stationary_start = None
                    stationary_run_frames = []
                    previous_timestamp = None

                if not item.get("reliable", False):
                    continue

                previous_timestamp = timestamp

                if item.get("motion_state_candidate") == "stationary":
                    if stationary_start is None:
                        stationary_start = timestamp
                        stationary_run_frames = []

                    stationary_run_frames.append(frame_number)

                    if (
                        timestamp - stationary_start
                        >= self.stationary_persistence_seconds
                    ):
                        stationary_frames.update(stationary_run_frames)

                else:
                    stationary_start = None
                    stationary_run_frames = []

        selected = []

        for frame in tracking_output.frame_tracks:

            if frame.frame_number in stationary_frames:
                selected.append(
                    (frame.frame_number, frame.timestamp_seconds, None)
                )
                continue

            candidates = []

            for vehicle in frame.vehicles:
                bbox = vehicle.bbox
                center_x = bbox.center_x / width

                if not (
                    self.horizontal_corridor[0]
                    <= center_x
                    <= self.horizontal_corridor[1]
                ):
                    continue

                bottom_y = bbox.y2 / height

                area = (
                    max(0.0, bbox.width)
                    * max(0.0, bbox.height)
                    / (width * height)
                )

                proximity_score = (
                    0.65 * bottom_y + 0.35 * area
                )

                candidates.append((proximity_score, vehicle))

            if candidates:
                _, lead = max(
                    candidates,
                    key=lambda item: item[0],
                )
            else:
                lead = None

            selected.append(
                (
                    frame.frame_number,
                    frame.timestamp_seconds,
                    lead,
                )
            )

        segments = []
        current = []

        for frame_number, timestamp, vehicle in selected:

            if vehicle is None:
                if current:
                    self._finish_segment(segments, current)
                    current = []
                continue

            if current:
                previous_frame, _, previous_vehicle = current[-1]

                previous_identity = (
                    previous_vehicle.identity_id
                    if previous_vehicle.identity_id is not None
                    else previous_vehicle.track_id
                )
                current_identity = (
                    vehicle.identity_id
                    if vehicle.identity_id is not None
                    else vehicle.track_id
                )

                gap = frame_number - previous_frame

                if (
                    current_identity != previous_identity
                    or gap > self.max_gap_frames
                ):
                    self._finish_segment(segments, current)
                    current = []

            current.append((frame_number, timestamp, vehicle))

        self._finish_segment(segments, current)

        merged_segments = []

        for segment in segments:
            if not merged_segments:
                merged_segments.append(segment)
                continue

            previous = merged_segments[-1]

            previous_vehicle = previous[-1][2]
            current_vehicle = segment[0][2]

            previous_identity = (
                previous_vehicle.identity_id
                if previous_vehicle.identity_id is not None
                else previous_vehicle.track_id
            )

            current_identity = (
                current_vehicle.identity_id
                if current_vehicle.identity_id is not None
                else current_vehicle.track_id
            )

            gap = segment[0][0] - previous[-1][0] - 1

            gap_has_stationary_state = any(
                frame in stationary_frames
                for frame in range(
                    previous[-1][0] + 1,
                    segment[0][0],
                )
            )

            if (
                previous_identity == current_identity
                and gap <= 5
                and not gap_has_stationary_state
            ):
                previous.extend(segment)
            else:
                merged_segments.append(segment)

        segments = merged_segments

        events = []
        for segment in segments:
            if len(segment) < self.min_observations:
                continue

            start_frame, start_time, first_vehicle = segment[0]
            end_frame, end_time, _ = segment[-1]

            duration = end_time - start_time

            if duration < self.min_duration_seconds:
                continue

            identity_id = (
                first_vehicle.identity_id
                if first_vehicle.identity_id is not None
                else first_vehicle.track_id
            )

            related_track_ids = sorted({
                item[2].track_id
                for item in segment
            })

            missing_frames = sum(
                max(
                    0,
                    segment[index][0]
                    - segment[index - 1][0]
                    - 1,
                )
                for index in range(1, len(segment))
            )

            events.append(
                BehaviorEvent(
                    event_id=(
                        f"following_candidate_{identity_id}_{start_frame}"
                    ),
                    behavior_type=BehaviorType.FOLLOWING,
                    subject=BehaviorSubject(type="ego", id=None),
                    start_frame=start_frame,
                    end_frame=end_frame,
                    start_time_seconds=start_time,
                    end_time_seconds=end_time,
                    magnitude=None,
                    confidence=0.40,
                    related_vehicle_ids=related_track_ids,
                    evidence={
                        "classification": "candidate_lead_vehicle",
                        "selection_method": (
                            "central_corridor_and_image_proximity"
                        ),
                        "observation_count": len(segment),
                        "bridged_missing_frames": missing_frames,
                        "duration_seconds": round(duration, 3),
                        "stable_identity_id": identity_id,
                        "raw_tracker_ids": related_track_ids,
                        "limitations": [
                            "Lane membership is not confirmed.",
                            "Following behavior is not confirmed.",
                            "Real-world distance is unavailable.",
                            "Time headway is unavailable.",
                            "Unsafe following distance is not established.",
                        ],
                    },
                )
            )

        return events

    @staticmethod
    def _finish_segment(segments, current):
        if current:
            segments.append(current)
