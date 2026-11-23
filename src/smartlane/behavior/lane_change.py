
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from smartlane.models import LaneContext


@dataclass
class LanePositionSample:
    frame_number: int
    timestamp_seconds: float
    lane_center_x: float
    lane_width_px: float
    camera_center_x: float
    normalized_offset: float
    confidence: float


class EgoLanePositionAnalyzer:
    """
    Estimates the camera's relative horizontal position inside
    the corridor formed by two detected lane boundaries.

    Image-space diagnostic only. Not a physical lane position.
    """

    def __init__(
        self,
        smoothing: float = 0.25,
        minimum_lane_width_ratio: float = 0.08,
    ):
        self.smoothing = smoothing
        self.minimum_lane_width_ratio = minimum_lane_width_ratio

    @staticmethod
    def _bottom_x(boundary) -> Optional[float]:
        if not boundary.points:
            return None

        bottom_point = max(boundary.points, key=lambda point: point.y)
        return float(bottom_point.x)

    def analyze(
        self,
        contexts: list[LaneContext],
        frame_width: int,
    ) -> dict:
        samples: list[LanePositionSample] = []
        previous_offset: Optional[float] = None
        previous_frame: Optional[int] = None
        rejected_corridor_frames = 0

        for context in contexts:
            corridor_check = context.evidence.get(
                "corridor_temporal_check", {}
            )

            if corridor_check.get("valid") is False:
                rejected_corridor_frames += 1
                previous_offset = None
                previous_frame = None
                continue

            if len(context.lane_boundaries) < 2:
                previous_offset = None
                previous_frame = None
                continue

            boundaries = sorted(
                context.lane_boundaries,
                key=lambda boundary: (
                    self._bottom_x(boundary)
                    if self._bottom_x(boundary) is not None
                    else float("inf")
                ),
            )

            left_x = self._bottom_x(boundaries[0])
            right_x = self._bottom_x(boundaries[-1])

            if left_x is None or right_x is None:
                continue

            lane_width = right_x - left_x

            if lane_width <= frame_width * self.minimum_lane_width_ratio:
                previous_offset = None
                previous_frame = None
                continue

            lane_center = (left_x + right_x) / 2.0
            camera_center = frame_width / 2.0

            raw_offset = (
                camera_center - lane_center
            ) / lane_width

            if (
                previous_offset is None
                or previous_frame is None
                or context.frame_number - previous_frame > 2
            ):
                smoothed_offset = raw_offset
            else:
                smoothed_offset = (
                    self.smoothing * raw_offset
                    + (1.0 - self.smoothing) * previous_offset
                )

            previous_offset = smoothed_offset
            previous_frame = context.frame_number

            samples.append(
                LanePositionSample(
                    frame_number=context.frame_number,
                    timestamp_seconds=context.timestamp_seconds,
                    lane_center_x=lane_center,
                    lane_width_px=lane_width,
                    camera_center_x=camera_center,
                    normalized_offset=smoothed_offset,
                    confidence=context.confidence,
                )
            )

        candidates = self._detect_candidates(samples)

        return {
            "frames_analyzed": len(contexts),
            "frames_with_position": len(samples),
            "coverage": (
                len(samples) / len(contexts)
                if contexts else 0.0
            ),
            "rejected_corridor_frames": rejected_corridor_frames,
            "validated_position_coverage": (
                len(samples) / len(contexts)
                if contexts else 0.0
            ),
            "measurement_type": "normalized_image_space_lateral_offset",
            "interpretation": (
                "Positive offset: camera center is right of corridor center. "
                "Negative offset: camera center is left of corridor center."
            ),
            "lane_change_candidates": candidates,
            "candidate_count": len(candidates),
            "limitations": [
                "Not a physical distance measurement.",
                "Does not establish an ego lane ID.",
                "Road curvature and camera movement can affect the offset.",
                "Two boundaries do not establish adjacent-lane topology.",
                "Candidates are not confirmed lane changes.",
                "Turning and intersection geometry can create false candidates.",
            ],
            "samples": [
                {
                    "frame_number": sample.frame_number,
                    "timestamp_seconds": sample.timestamp_seconds,
                    "lane_center_x": sample.lane_center_x,
                    "lane_width_px": sample.lane_width_px,
                    "camera_center_x": sample.camera_center_x,
                    "normalized_offset": sample.normalized_offset,
                    "confidence": sample.confidence,
                }
                for sample in samples
            ],
        }

    @staticmethod
    def _detect_candidates(
        samples: list[LanePositionSample],
    ) -> list[dict]:
        """
        Finds sustained lateral-position transitions.

        These are candidates only. Corridor movement does not prove
        that the vehicle crossed a lane marking.
        """

        if len(samples) < 8:
            return []

        candidates = []

        minimum_change = 0.12
        minimum_duration = 0.8
        maximum_duration = 5.0
        minimum_confidence = 0.20

        index = 0

        while index < len(samples) - 5:
            start = samples[index]

            if start.confidence < minimum_confidence:
                index += 1
                continue

            baseline = start.normalized_offset
            found = False

            for end_index in range(index + 5, len(samples)):
                end = samples[end_index]

                duration = (
                    end.timestamp_seconds - start.timestamp_seconds
                )

                if duration > maximum_duration:
                    break

                if end.confidence < minimum_confidence:
                    continue

                change = end.normalized_offset - baseline

                if abs(change) < minimum_change:
                    continue

                window = samples[index:end_index + 1]

                if any(
                    window[i].frame_number - window[i - 1].frame_number > 2
                    for i in range(1, len(window))
                ):
                    continue

                midpoint = window[len(window) // 2].normalized_offset

                if change > 0 and midpoint < baseline + change * 0.35:
                    continue

                if change < 0 and midpoint > baseline + change * 0.35:
                    continue

                if duration < minimum_duration:
                    continue

                candidates.append({
                    "start_frame": start.frame_number,
                    "end_frame": end.frame_number,
                    "start_time": start.timestamp_seconds,
                    "end_time": end.timestamp_seconds,
                    "direction": (
                        "rightward_image_shift"
                        if change > 0
                        else "leftward_image_shift"
                    ),
                    "offset_change": round(change, 4),
                    "confidence": round(
                        min(
                            start.confidence,
                            end.confidence,
                        ),
                        3,
                    ),
                    "classification": "lateral_movement_candidate",
                    "confirmed_lane_change": False,
                })

                index = end_index + 1
                found = True
                break

            if not found:
                index += 1

        return candidates
