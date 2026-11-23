
from __future__ import annotations

from statistics import median
from collections import deque
import math


class MotionSignalAnalyzer:
    """
    Derive smoothed image-space motion signals from background
    optical flow.

    Radial-flow reduction is a possible deceleration indicator,
    not a physical braking measurement.
    """

    def __init__(
        self,
        smoothing_window_seconds: float = 0.25,
        min_confidence: float = 0.50,
        trend_window_seconds: float = 0.50,
        relative_drop_threshold: float = 0.20,
        min_radial_samples: int = 3,
        persistence_seconds: float = 0.15,
        max_radial_gap_seconds: float = 0.20,
    ) -> None:
        self.smoothing_window_seconds = smoothing_window_seconds
        self.min_confidence = min_confidence
        self.trend_window_seconds = trend_window_seconds
        self.relative_drop_threshold = relative_drop_threshold
        self.min_radial_samples = min_radial_samples
        self.persistence_seconds = persistence_seconds
        self.max_radial_gap_seconds = max_radial_gap_seconds

    def analyze(self, ego_motion: dict) -> dict:
        measurements = ego_motion.get("measurements", [])

        history = deque()
        radial_history = deque()

        last_radial_timestamp = None
        pending_since = None

        results = []

        for item in measurements:
            timestamp = item.get("timestamp_seconds")
            interval = item.get("interval_seconds")

            result = {
                "frame_number": item.get("frame_number"),
                "timestamp_seconds": timestamp,
                "valid": False,
                "reliable": False,
                "scale_rate": None,
                "vertical_flow_rate": None,
                "horizontal_flow_rate": None,
                "rotation_rate": None,
                "smoothed_scale_rate": None,
                "smoothed_vertical_flow_rate": None,
                "radial_flow_rate": None,
                "smoothed_radial_flow_rate": None,
                "radial_relative_change": None,
                "radial_previous_samples": 0,
                "radial_recent_samples": 0,
                "raw_deceleration_candidate": False,
                "deceleration_candidate": False,
            }

            valid = (
                item.get("valid", False)
                and isinstance(interval, (int, float))
                and interval > 0
                and isinstance(timestamp, (int, float))
            )

            if not valid:
                results.append(result)
                continue

            confidence = item.get("confidence", 0.0)
            reliable = confidence >= self.min_confidence

            result["valid"] = True
            result["reliable"] = reliable

            scale = item.get("apparent_scale_change")
            vertical = item.get("translation_y_normalized")
            horizontal = item.get("translation_x_normalized")
            rotation = item.get("rotation_degrees")
            radial = item.get("radial_flow_median")

            if scale is not None:
                result["scale_rate"] = scale / interval

            if vertical is not None:
                result["vertical_flow_rate"] = vertical / interval

            if horizontal is not None:
                result["horizontal_flow_rate"] = horizontal / interval

            if rotation is not None:
                result["rotation_rate"] = rotation / interval

            if (
                reliable
                and radial is not None
                and item.get("foe_valid", False)
                and math.isfinite(radial)
            ):
                radial_rate = radial / interval
                result["radial_flow_rate"] = radial_rate

                if (
                    last_radial_timestamp is not None
                    and timestamp - last_radial_timestamp
                    > self.max_radial_gap_seconds
                ):
                    radial_history.clear()
                    pending_since = None

                radial_history.append({
                    "timestamp": timestamp,
                    "radial": radial_rate,
                })

                last_radial_timestamp = timestamp

            # Expire stale radial measurements even when current
            # frame has no valid radial-flow estimate.
            if (
                last_radial_timestamp is not None
                and timestamp - last_radial_timestamp
                > self.max_radial_gap_seconds
            ):
                radial_history.clear()
                pending_since = None

            if reliable:
                history.append({
                    "timestamp": timestamp,
                    "scale": result["scale_rate"],
                    "vertical": result["vertical_flow_rate"],
                })

            cutoff = timestamp - self.smoothing_window_seconds

            while history and history[0]["timestamp"] < cutoff:
                history.popleft()

            scale_values = [
                entry["scale"]
                for entry in history
                if entry["scale"] is not None
            ]

            vertical_values = [
                entry["vertical"]
                for entry in history
                if entry["vertical"] is not None
            ]

            if len(scale_values) >= 3:
                result["smoothed_scale_rate"] = median(scale_values)

            if len(vertical_values) >= 3:
                result["smoothed_vertical_flow_rate"] = median(
                    vertical_values
                )

            previous_start = timestamp - 2 * self.trend_window_seconds
            recent_start = timestamp - self.trend_window_seconds

            previous_values = [
                entry["radial"]
                for entry in radial_history
                if previous_start <= entry["timestamp"] < recent_start
            ]

            recent_values = [
                entry["radial"]
                for entry in radial_history
                if recent_start <= entry["timestamp"] <= timestamp
            ]

            result["radial_previous_samples"] = len(previous_values)
            result["radial_recent_samples"] = len(recent_values)

            raw_candidate = False

            if (
                len(previous_values) >= self.min_radial_samples
                and len(recent_values) >= self.min_radial_samples
            ):
                previous_median = median(previous_values)
                recent_median = median(recent_values)

                if previous_median > 0:
                    relative_change = (
                        recent_median - previous_median
                    ) / previous_median

                    result["smoothed_radial_flow_rate"] = recent_median
                    result["radial_relative_change"] = relative_change

                    raw_candidate = (
                        relative_change <= -self.relative_drop_threshold
                    )

            result["raw_deceleration_candidate"] = raw_candidate

            if raw_candidate:
                if pending_since is None:
                    pending_since = timestamp

                result["deceleration_candidate"] = (
                    timestamp - pending_since
                    >= self.persistence_seconds
                )
            else:
                pending_since = None

            results.append(result)

        reliable_count = sum(
            item["reliable"] for item in results
        )

        radial_count = sum(
            item["radial_flow_rate"] is not None
            for item in results
        )

        candidate_count = sum(
            item["deceleration_candidate"]
            for item in results
        )

        return {
            "measurement_count": len(results),
            "reliable_measurement_count": reliable_count,
            "reliable_coverage": (
                reliable_count / len(results) if results else 0.0
            ),
            "radial_measurement_count": radial_count,
            "deceleration_candidate_count": candidate_count,
            "trend_window_seconds": self.trend_window_seconds,
            "relative_drop_threshold": self.relative_drop_threshold,
            "persistence_seconds": self.persistence_seconds,
            "measurements": results,
            "interpretation": (
                "Persistent radial background-flow reduction is a "
                "possible deceleration indicator. It is not calibrated "
                "vehicle braking, speed, or acceleration."
            ),
        }
