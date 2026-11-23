
from pathlib import Path

import cv2
import numpy as np

from smartlane.geometry.lane_detector import LaneDetector
from smartlane.geometry.lane_tracker import LaneTemporalTracker


class GeometryAnalyzer:

    def __init__(self):
        self.detector = LaneDetector()
        self.tracker = LaneTemporalTracker()

    @staticmethod
    def _boundary_x_at_y(boundary, target_y):
        if not boundary.points:
            return None

        points = sorted(boundary.points, key=lambda p: p.y)

        if target_y < points[0].y or target_y > points[-1].y:
            return None

        for first, second in zip(points, points[1:]):
            if first.y <= target_y <= second.y:
                dy = second.y - first.y

                if abs(dy) < 1e-6:
                    return float(first.x)

                ratio = (target_y - first.y) / dy

                return float(
                    first.x + ratio * (second.x - first.x)
                )

        return float(points[-1].x)

    @classmethod
    def _measure_road_geometry(cls, context, frame_width, frame_height):
        if len(context.lane_boundaries) < 2:
            return None

        boundaries = sorted(
            context.lane_boundaries,
            key=lambda boundary: (
                max((p.x for p in boundary.points), default=float("inf"))
            ),
        )

        # Select the leftmost and rightmost detected boundaries.
        left = min(
            boundaries,
            key=lambda b: cls._boundary_x_at_y(
                b, frame_height * 0.90
            ) if cls._boundary_x_at_y(
                b, frame_height * 0.90
            ) is not None else float("inf"),
        )

        right = max(
            boundaries,
            key=lambda b: cls._boundary_x_at_y(
                b, frame_height * 0.90
            ) if cls._boundary_x_at_y(
                b, frame_height * 0.90
            ) is not None else float("-inf"),
        )

        sample_y = [
            frame_height * 0.65,
            frame_height * 0.75,
            frame_height * 0.90,
        ]

        centers = []

        for y in sample_y:
            left_x = cls._boundary_x_at_y(left, y)
            right_x = cls._boundary_x_at_y(right, y)

            if left_x is None or right_x is None:
                return None

            if right_x <= left_x:
                return None

            centers.append((left_x + right_x) / 2.0)

        # Compare corridor center at different image heights.
        upper_shift = (
            centers[0] - centers[1]
        ) / frame_width

        lower_shift = (
            centers[1] - centers[2]
        ) / frame_width

        curvature_indicator = upper_shift - lower_shift

        return {
            "corridor_center_top": round(centers[0], 2),
            "corridor_center_middle": round(centers[1], 2),
            "corridor_center_bottom": round(centers[2], 2),
            "upper_shift_normalized": round(upper_shift, 5),
            "lower_shift_normalized": round(lower_shift, 5),
            "curvature_indicator": round(curvature_indicator, 5),
            "confidence": round(float(context.confidence), 3),
        }

    @staticmethod
    def _classify_road_segments(measurements):
        """
        Classifies sustained image-space geometry patterns.

        These are road-geometry indicators, not confirmed turns.
        """

        results = []

        if not measurements:
            return results

        minimum_confidence = 0.20
        smoothing_window = 5

        for index, measurement in enumerate(measurements):
            if measurement is None:
                results.append(None)
                continue

            start = max(0, index - smoothing_window + 1)

            window = [
                item for item in measurements[start:index + 1]
                if item is not None
                and item["confidence"] >= minimum_confidence
            ]

            if len(window) < 3:
                results.append({
                    "classification": "uncertain",
                    "confidence": 0.0,
                })
                continue

            curvature = float(np.median([
                item["curvature_indicator"]
                for item in window
            ]))

            if curvature > 0.003:
                classification = "curvature_pattern_positive"
            elif curvature < -0.003:
                classification = "curvature_pattern_negative"
            else:
                classification = "approximately_straight_geometry"

            results.append({
                "classification": classification,
                "curvature_indicator": round(curvature, 5),
                "confidence": round(
                    float(np.mean([
                        item["confidence"] for item in window
                    ])),
                    3,
                ),
            })

        return results

    def process_video(self, video_path: str | Path):

        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise RuntimeError(
                f"Cannot open video: {video_path}"
            )

        fps = cap.get(cv2.CAP_PROP_FPS)

        self.tracker = LaneTemporalTracker()

        contexts = []
        geometry_measurements = []
        frame_number = 0

        try:
            while True:
                ok, frame = cap.read()

                if not ok:
                    break

                frame_height, frame_width = frame.shape[:2]

                timestamp = (
                    frame_number / fps
                    if fps > 0
                    else 0.0
                )

                context = self.detector.detect(
                    frame,
                    frame_number,
                    timestamp,
                )

                context = self.tracker.update(
                    context,
                    frame_width,
                )

                contexts.append(context)

                measurement = self._measure_road_geometry(
                    context,
                    frame_width,
                    frame_height,
                )

                geometry_measurements.append(measurement)

                frame_number += 1

        finally:
            cap.release()

        detected_frames = sum(
            bool(context.lane_boundaries)
            for context in contexts
        )

        road_geometry = self._classify_road_segments(
            geometry_measurements
        )

        return {
            "contexts": contexts,
            "frames_processed": frame_number,
            "frames_with_boundaries": detected_frames,
            "detection_rate": (
                detected_frames / frame_number
                if frame_number else 0.0
            ),
            "road_geometry": road_geometry,
            "geometry_measurement_count": sum(
                item is not None
                for item in geometry_measurements
            ),
        }
