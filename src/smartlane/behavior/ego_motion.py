
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from smartlane.ingestion import iter_frames


class EgoMotionEstimator:
    """
    Estimate relative camera motion using background optical flow.

    Produces image-space measurements, not calibrated vehicle speed
    or acceleration.
    """

    def __init__(
        self,
        max_features: int = 700,
        min_features: int = 25,
        min_inliers: int = 15,
        min_inlier_ratio: float = 0.35,
        min_radial_features: int = 12,
    ) -> None:
        self.max_features = max_features
        self.min_features = min_features
        self.min_inliers = min_inliers
        self.min_inlier_ratio = min_inlier_ratio
        self.min_radial_features = min_radial_features

    def _build_background_mask(
        self,
        frame: np.ndarray,
        frame_tracks,
    ) -> np.ndarray:
        height, width = frame.shape[:2]
        mask = np.full((height, width), 255, dtype=np.uint8)

        if frame_tracks is not None:
            for vehicle in frame_tracks.vehicles:
                box = vehicle.bbox

                box_width = box.x2 - box.x1
                box_height = box.y2 - box.y1

                padding_x = box_width * 0.15
                padding_y = box_height * 0.15

                x1 = max(0, int(box.x1 - padding_x))
                y1 = max(0, int(box.y1 - padding_y))
                x2 = min(width, int(box.x2 + padding_x))
                y2 = min(height, int(box.y2 + padding_y))

                cv2.rectangle(
                    mask,
                    (x1, y1),
                    (x2, y2),
                    0,
                    thickness=-1,
                )

        # Exclude the outer image border, where optical flow is
        # particularly vulnerable to tracking errors.
        margin_x = int(width * 0.02)
        margin_y = int(height * 0.02)

        mask[:margin_y, :] = 0
        mask[-margin_y:, :] = 0
        mask[:, :margin_x] = 0
        mask[:, -margin_x:] = 0

        return mask


    @staticmethod
    def _estimate_foe(
        old: np.ndarray,
        flow: np.ndarray,
        width: int,
        height: int,
    ) -> dict:
        """
        Estimate a shared 2D focus of expansion using least squares.

        Diagnostic image-space estimate only. Not calibrated speed.
        """
        result = {
            "foe_x_normalized": None,
            "foe_y_normalized": None,
            "radial_flow_median": None,
            "radial_feature_count": 0,
            "foe_valid": False,
        }

        if len(old) < 12:
            return result

        x = old[:, 0].astype(np.float64)
        y = old[:, 1].astype(np.float64)
        u = flow[:, 0].astype(np.float64)
        v = flow[:, 1].astype(np.float64)

        # Model:
        # u = k*x + c_x
        # v = k*y + c_y
        #
        # Both directions share the same expansion coefficient k.
        A = np.zeros((2 * len(old), 3), dtype=np.float64)
        b = np.zeros(2 * len(old), dtype=np.float64)

        A[0::2, 0] = x
        A[0::2, 1] = 1.0
        b[0::2] = u

        A[1::2, 0] = y
        A[1::2, 2] = 1.0
        b[1::2] = v

        try:
            solution, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        except np.linalg.LinAlgError:
            return result

        k, cx, cy = solution

        if not np.isfinite(k) or abs(k) < 1e-6:
            return result

        foe_x = -cx / k
        foe_y = -cy / k

        if not np.isfinite(foe_x) or not np.isfinite(foe_y):
            return result

        # Reject estimates outside a generous image boundary.
        if not (
            -0.25 * width <= foe_x <= 1.25 * width
            and -0.25 * height <= foe_y <= 1.25 * height
        ):
            return result

        dx = x - foe_x
        dy = y - foe_y

        radial_distance = np.sqrt(dx ** 2 + dy ** 2)

        radial_flow = (
            u * dx + v * dy
        ) / np.maximum(radial_distance, 1.0)

        if not np.all(np.isfinite(radial_flow)):
            return result

        result.update({
            "foe_x_normalized": float(foe_x / width),
            "foe_y_normalized": float(foe_y / height),
            "radial_flow_median": float(np.median(radial_flow)),
            "radial_feature_count": int(len(old)),
            "foe_valid": True,
        })

        return result


    def _estimate_pair(
        self,
        previous_gray: np.ndarray,
        current_gray: np.ndarray,
        previous_mask: np.ndarray,
        current_mask: np.ndarray,
        timestamp_seconds: float,
        frame_number: int,
    ) -> dict:
        height, width = current_gray.shape

        result = {
            "frame_number": frame_number,
            "timestamp_seconds": timestamp_seconds,
            "valid": False,
            "feature_count": 0,
            "inlier_count": 0,
            "inlier_ratio": 0.0,
            "confidence": 0.0,
            "translation_x_normalized": None,
            "translation_y_normalized": None,
            "rotation_degrees": None,
            "apparent_scale_change": None,
            "foe_x_normalized": None,
            "foe_y_normalized": None,
            "radial_flow_median": None,
            "radial_feature_count": 0,
            "foe_valid": False,
            "limitations": [
                "Image-space camera motion only",
                "FOE is an approximate diagnostic estimate",
                "Not calibrated vehicle speed or acceleration",
                "Perspective and camera rotation can affect radial flow",
            ],
        }

        points = cv2.goodFeaturesToTrack(
            previous_gray,
            maxCorners=self.max_features,
            qualityLevel=0.01,
            minDistance=8,
            mask=previous_mask,
            blockSize=7,
        )

        if points is None or len(points) < self.min_features:
            return result

        next_points, status, _ = cv2.calcOpticalFlowPyrLK(
            previous_gray,
            current_gray,
            points,
            None,
            winSize=(21, 21),
            maxLevel=3,
        )

        if next_points is None or status is None:
            return result

        old = points.reshape(-1, 2)
        new = next_points.reshape(-1, 2)

        good = status.reshape(-1) == 1
        old = old[good]
        new = new[good]

        inside = (
            (new[:, 0] >= 0)
            & (new[:, 0] < width)
            & (new[:, 1] >= 0)
            & (new[:, 1] < height)
        )

        old = old[inside]
        new = new[inside]

        if len(old) < self.min_features:
            return result

        current_values = current_mask[
            np.clip(new[:, 1].astype(int), 0, height - 1),
            np.clip(new[:, 0].astype(int), 0, width - 1),
        ]

        background = current_values > 0
        old = old[background]
        new = new[background]

        if len(old) < self.min_features:
            return result

        flow = new - old

        transform, inliers = cv2.estimateAffinePartial2D(
            old,
            new,
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
            maxIters=1000,
            confidence=0.99,
        )

        if transform is None or inliers is None:
            return result

        inlier_mask = inliers.reshape(-1).astype(bool)
        inlier_count = int(inlier_mask.sum())
        inlier_ratio = inlier_count / len(old)

        result["feature_count"] = int(len(old))
        result["inlier_count"] = inlier_count
        result["inlier_ratio"] = float(inlier_ratio)

        if (
            inlier_count < self.min_inliers
            or inlier_ratio < self.min_inlier_ratio
        ):
            return result

        a = float(transform[0, 0])
        b = float(transform[1, 0])
        tx = float(transform[0, 2])
        ty = float(transform[1, 2])

        scale = float(np.sqrt(a * a + b * b))
        rotation = float(np.degrees(np.arctan2(b, a)))

        if not np.isfinite(scale) or scale <= 0:
            return result

        # Use RANSAC inliers for the FOE estimate.
        foe_result = self._estimate_foe(
            old=old[inlier_mask],
            flow=flow[inlier_mask],
            width=width,
            height=height,
        )

        result.update({
            "valid": True,
            "translation_x_normalized": tx / width,
            "translation_y_normalized": ty / height,
            "rotation_degrees": rotation,
            "apparent_scale_change": scale - 1.0,
            "confidence": float(
                inlier_ratio * min(inlier_count / 50.0, 1.0)
            ),
            **foe_result,
        })

        return result

    def process_video(
        self,
        video_path: str | Path,
        frame_tracks=None,
    ) -> dict:
        tracks_by_frame = {}

        if frame_tracks is not None:
            tracks_by_frame = {
                item.frame_number: item
                for item in frame_tracks
            }

        previous_gray = None
        previous_mask = None
        previous_timestamp = None

        measurements = []

        for frame_state, frame in iter_frames(video_path):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            mask = self._build_background_mask(
                frame,
                tracks_by_frame.get(frame_state.frame_number),
            )

            if previous_gray is not None:
                measurement = self._estimate_pair(
                    previous_gray=previous_gray,
                    current_gray=gray,
                    previous_mask=previous_mask,
                    current_mask=mask,
                    timestamp_seconds=frame_state.timestamp_seconds,
                    frame_number=frame_state.frame_number,
                )

                dt = (
                    frame_state.timestamp_seconds
                    - previous_timestamp
                )

                measurement["interval_seconds"] = dt

                measurements.append(measurement)

            previous_gray = gray
            previous_mask = mask
            previous_timestamp = frame_state.timestamp_seconds

        valid = [
            item for item in measurements
            if item["valid"]
        ]

        foe_valid = [
            item for item in valid
            if item["foe_valid"]
        ]

        return {
            "frames_processed": len(measurements) + (
                1 if measurements else 0
            ),
            "motion_measurement_count": len(measurements),
            "valid_measurement_count": len(valid),
            "coverage": (
                len(valid) / len(measurements)
                if measurements else 0.0
            ),
            "foe_valid_measurement_count": len(foe_valid),
            "foe_coverage": (
                len(foe_valid) / len(measurements)
                if measurements else 0.0
            ),
            "measurements": measurements,
            "interpretation": (
                "Relative image-space camera motion with approximate "
                "FOE and radial-flow diagnostics. "
                "Not calibrated speed or acceleration."
            ),
        }
