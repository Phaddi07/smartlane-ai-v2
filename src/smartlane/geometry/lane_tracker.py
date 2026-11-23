
from __future__ import annotations

from smartlane.models import LaneBoundary, LaneContext, LaneBoundaryPoint


class LaneTemporalTracker:
    """Track lane boundaries and validate corridor consistency."""

    def __init__(
        self,
        smoothing: float = 0.35,
        max_missing_frames: int = 2,
        max_normalized_jump: float = 0.12,
        max_corridor_center_shift: float = 0.06,
        max_corridor_width_change: float = 0.20,
    ):
        self.smoothing = smoothing
        self.max_missing_frames = max_missing_frames
        self.max_normalized_jump = max_normalized_jump

        self.max_corridor_center_shift = max_corridor_center_shift
        self.max_corridor_width_change = max_corridor_width_change

        self.previous = {}
        self.missing_counts = {}
        self.previous_corridor = None

    @staticmethod
    def _bottom_x(boundary):
        if not boundary.points:
            return None

        return float(
            max(boundary.points, key=lambda point: point.y).x
        )

    def _is_plausible_match(
        self,
        previous_points,
        current_points,
        frame_width: int,
    ) -> bool:
        if len(previous_points) != len(current_points):
            return False

        if frame_width <= 0:
            return False

        movements = [
            abs(current.x - previous.x) / frame_width
            for current, previous in zip(current_points, previous_points)
        ]

        return max(movements, default=0.0) <= self.max_normalized_jump

    def _validate_corridor(self, boundaries, frame_width):
        if len(boundaries) != 2 or frame_width <= 0:
            return {
                "valid": None,
                "reason": "insufficient_boundaries",
            }

        positions = [
            self._bottom_x(boundary)
            for boundary in boundaries
        ]

        if any(position is None for position in positions):
            return {
                "valid": None,
                "reason": "missing_boundary_points",
            }

        left_x, right_x = sorted(positions)
        width = right_x - left_x
        center = (left_x + right_x) / 2.0

        if width <= 0:
            return {
                "valid": False,
                "reason": "invalid_corridor_width",
            }

        current = {
            "center": center,
            "width": width,
        }

        previous = self.previous_corridor

        if previous is None:
            self.previous_corridor = current

            return {
                "valid": True,
                "reason": "initial_reference",
            }

        center_shift = abs(
            center - previous["center"]
        ) / frame_width

        width_change = abs(
            width - previous["width"]
        ) / previous["width"]

        valid = (
            center_shift <= self.max_corridor_center_shift
            and width_change <= self.max_corridor_width_change
        )

        if valid:
            self.previous_corridor = current
            reason = "consistent"
        else:
            reason = "abrupt_corridor_change"

        return {
            "valid": valid,
            "reason": reason,
            "center_shift_normalized": round(center_shift, 5),
            "width_change_ratio": round(width_change, 5),
        }

    def update(
        self,
        context: LaneContext,
        frame_width: int,
    ) -> LaneContext:

        updated_boundaries = []
        rejected_ids = []

        for boundary in context.lane_boundaries:
            boundary_id = boundary.boundary_id
            current_points = boundary.points

            if boundary_id in self.previous:
                previous_points = self.previous[boundary_id]

                if self._is_plausible_match(
                    previous_points,
                    current_points,
                    frame_width,
                ):
                    smoothed_points = [
                        LaneBoundaryPoint(
                            x=(
                                self.smoothing * current.x
                                + (1 - self.smoothing) * previous.x
                            ),
                            y=(
                                self.smoothing * current.y
                                + (1 - self.smoothing) * previous.y
                            ),
                        )
                        for current, previous in zip(
                            current_points,
                            previous_points,
                        )
                    ]
                else:
                    smoothed_points = current_points
                    rejected_ids.append(boundary_id)
            else:
                smoothed_points = current_points

            self.previous[boundary_id] = smoothed_points
            self.missing_counts[boundary_id] = 0

            updated_boundaries.append(
                LaneBoundary(
                    boundary_id=boundary_id,
                    points=smoothed_points,
                    confidence=boundary.confidence,
                )
            )

        detected_ids = {
            boundary.boundary_id
            for boundary in context.lane_boundaries
        }

        for boundary_id in list(self.previous):
            if boundary_id not in detected_ids:
                self.missing_counts[boundary_id] = (
                    self.missing_counts.get(boundary_id, 0) + 1
                )

                if self.missing_counts[boundary_id] > self.max_missing_frames:
                    del self.previous[boundary_id]
                    del self.missing_counts[boundary_id]

        corridor_check = self._validate_corridor(
            updated_boundaries,
            frame_width,
        )

        return LaneContext(
            frame_number=context.frame_number,
            timestamp_seconds=context.timestamp_seconds,
            lane_count=context.lane_count,
            ego_lane_id=context.ego_lane_id,
            lane_boundaries=updated_boundaries,
            confidence=context.confidence,
            evidence={
                **context.evidence,
                "temporal_tracking": True,
                "smoothing": self.smoothing,
                "max_missing_frames": self.max_missing_frames,
                "rejected_boundary_matches": rejected_ids,
                "jump_validation": True,
                "frame_width": frame_width,
                "corridor_temporal_check": corridor_check,
            },
        )
