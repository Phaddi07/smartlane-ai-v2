from __future__ import annotations

import cv2
import numpy as np

from smartlane.models import (
    LaneBoundary,
    LaneBoundaryPoint,
    LaneContext,
)


class LaneDetector:
    """Detect and filter lane-boundary candidates using OpenCV."""

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 35,
        min_line_length: int = 35,
        max_line_gap: int = 80,
        cluster_threshold: float = 0.10,
    ):
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.cluster_threshold = cluster_threshold

    def _select_dominant_cluster(self, segments, frame_width):
        """Select the most strongly supported group of similar segments."""

        if not segments:
            return []

        threshold = frame_width * self.cluster_threshold

        best_cluster = []
        best_weight = -1.0

        for seed in segments:
            cluster = [
                segment
                for segment in segments
                if max(
                    abs(segment["x_top"] - seed["x_top"]),
                    abs(segment["x_bottom"] - seed["x_bottom"]),
                ) <= threshold
            ]

            cluster_weight = sum(
                segment["weight"] for segment in cluster
            )

            if cluster_weight > best_weight:
                best_weight = cluster_weight
                best_cluster = cluster

        return best_cluster

    def detect(
        self,
        frame: np.ndarray,
        frame_number: int = 0,
        timestamp_seconds: float = 0.0,
    ) -> LaneContext:

        if frame is None or frame.size == 0:
            raise ValueError("Input frame is empty.")

        height, width = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        edges = cv2.Canny(
            blurred,
            self.canny_low,
            self.canny_high,
        )

        roi_top = int(height * 0.58)
        roi_bottom = height - 1

        polygon = np.array(
            [[
                (int(width * 0.08), roi_bottom),
                (int(width * 0.42), roi_top),
                (int(width * 0.58), roi_top),
                (int(width * 0.92), roi_bottom),
            ]],
            dtype=np.int32,
        )

        mask = np.zeros_like(edges)
        cv2.fillPoly(mask, polygon, 255)

        masked_edges = cv2.bitwise_and(edges, mask)

        lines = cv2.HoughLinesP(
            masked_edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )

        top_y = int(height * 0.62)
        bottom_y = int(height * 0.96)
        image_center = width / 2

        candidates = {
            "left": [],
            "right": [],
        }

        rejected_orientation = {
            "left": 0,
            "right": 0,
        }

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = np.asarray(line).reshape(-1)[:4]

                delta_y = y2 - y1

                if abs(delta_y) < 10:
                    continue

                delta_x = x2 - x1
                dx_dy = abs(delta_x / delta_y)

                if not 0.08 <= dx_dy <= 1.8:
                    continue

                x_top = x1 + (
                    (top_y - y1) * delta_x / delta_y
                )

                x_bottom = x1 + (
                    (bottom_y - y1) * delta_x / delta_y
                )

                if not (
                    0 <= x_top < width
                    and 0 <= x_bottom < width
                ):
                    continue

                side = (
                    "left"
                    if x_bottom < image_center
                    else "right"
                )

                # Check expected perspective orientation.
                if side == "left" and x_top < x_bottom:
                    rejected_orientation[side] += 1
                    continue

                if side == "right" and x_top > x_bottom:
                    rejected_orientation[side] += 1
                    continue

                length = float(np.hypot(delta_x, delta_y))

                coverage = abs(delta_y) / height

                candidates[side].append({
                    "x_top": float(x_top),
                    "x_bottom": float(x_bottom),
                    "weight": length,
                    "coverage": coverage,
                })

        boundaries = []
        selected_counts = {}

        for boundary_id, side in enumerate(("left", "right")):
            segments = candidates[side]

            selected = self._select_dominant_cluster(
                segments,
                width,
            )

            selected_counts[side] = len(selected)

            if not selected:
                continue

            weights = np.array(
                [segment["weight"] for segment in selected],
                dtype=np.float64,
            )

            x_top = float(np.average(
                [segment["x_top"] for segment in selected],
                weights=weights,
            ))

            x_bottom = float(np.average(
                [segment["x_bottom"] for segment in selected],
                weights=weights,
            ))

            average_coverage = float(np.average(
                [segment["coverage"] for segment in selected],
                weights=weights,
            ))

            confidence = min(
                0.85,
                average_coverage / 0.35 * 0.65
                + min(len(selected), 5) * 0.04,
            )

            boundaries.append(
                LaneBoundary(
                    boundary_id=boundary_id,
                    points=[
                        LaneBoundaryPoint(
                            x=x_top,
                            y=float(top_y),
                        ),
                        LaneBoundaryPoint(
                            x=(x_top + x_bottom) / 2,
                            y=float((top_y + bottom_y) / 2),
                        ),
                        LaneBoundaryPoint(
                            x=x_bottom,
                            y=float(bottom_y),
                        ),
                    ],
                    confidence=confidence,
                )
            )

        corridor_valid = False

        if len(boundaries) == 2:
            left = boundaries[0]
            right = boundaries[1]

            top_gap = (
                right.points[0].x - left.points[0].x
            )

            bottom_gap = (
                right.points[-1].x - left.points[-1].x
            )

            perspective_ratio = (
                top_gap / bottom_gap
                if bottom_gap > 0
                else -1.0
            )

            corridor_valid = (
                top_gap > 0
                and bottom_gap > 0
                and bottom_gap <= width * 0.85
                and bottom_gap >= width * 0.08
                and 0 < perspective_ratio <= 0.65
            )

        side_confidences = [
            boundary.confidence
            for boundary in boundaries
        ]

        overall_confidence = (
            float(np.mean(side_confidences))
            if len(side_confidences) == 2
            else (
                side_confidences[0] * 0.5
                if side_confidences
                else 0.0
            )
        )

        if len(boundaries) == 2 and not corridor_valid:
            overall_confidence *= 0.5

        return LaneContext(
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            lane_count=None,
            ego_lane_id=None,
            lane_boundaries=boundaries,
            confidence=overall_confidence,
            evidence={
                "method": "canny_hough_clustered_detection",
                "candidate_segments": {
                    "left": len(candidates["left"]),
                    "right": len(candidates["right"]),
                },
                "selected_segments": selected_counts,
                "rejected_orientation": rejected_orientation,
                "corridor_geometry_valid": corridor_valid,
                "coordinate_system": "image_pixels",
                "lane_count_estimated": False,
                "ego_lane_estimated": False,
                "limitations": [
                    "Lane markings are candidate detections.",
                    "Intersection markings may still produce false candidates.",
                    "Curved roads may require curve-aware fitting.",
                    "Corridor validity is a geometric plausibility check, not lane verification.",
                    "No real-world distance or calibration is available.",
                ],
            },
        )