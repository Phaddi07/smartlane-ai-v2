
from __future__ import annotations

from collections import deque
from statistics import median

from smartlane.models import MotionState


class MotionStateAnalyzer:
    """
    Classify apparent POV motion using smoothed image-space signals.

    State transitions require temporal persistence to reduce
    classification changes caused by brief optical-flow fluctuations.

    These remain image-space candidates, not calibrated
    physical speed, acceleration, or braking measurements.
    """

    def __init__(
        self,
        stationary_threshold: float = 0.005,
        trend_threshold: float = 0.02,
        trend_window_seconds: float = 0.5,
        min_reliable_samples: int = 3,
        transition_persistence_seconds: float = 0.15,
        stationary_persistence_seconds: float = 0.25,
        max_measurement_gap_seconds: float = 0.20,
    ) -> None:
        self.stationary_threshold = stationary_threshold
        self.trend_threshold = trend_threshold
        self.trend_window_seconds = trend_window_seconds
        self.min_reliable_samples = min_reliable_samples
        self.transition_persistence_seconds = (
            transition_persistence_seconds
        )
        self.stationary_persistence_seconds = (
            stationary_persistence_seconds
        )
        self.max_measurement_gap_seconds = (
            max_measurement_gap_seconds
        )

    def analyze(self, motion_signal: dict) -> dict:
        measurements = motion_signal.get("measurements", [])

        history = deque()
        results = []

        current_state = MotionState.UNKNOWN
        pending_state = None
        pending_since = None
        last_reliable_timestamp = None

        for item in measurements:
            timestamp = item.get("timestamp_seconds")
            scale = item.get("smoothed_scale_rate")

            result = {
                "frame_number": item.get("frame_number"),
                "timestamp_seconds": timestamp,
                "motion_state_candidate": MotionState.UNKNOWN.value,
                "instantaneous_state_candidate": MotionState.UNKNOWN.value,
                "reliable": False,
                "apparent_scale_rate": scale,
                "trend": None,
                "transition_confirmed": False,
            }

            if (
                not item.get("reliable", False)
                or not isinstance(timestamp, (int, float))
                or scale is None
            ):
                results.append(result)
                continue

            if (
                last_reliable_timestamp is not None
                and timestamp - last_reliable_timestamp
                > self.max_measurement_gap_seconds
            ):
                history.clear()
                current_state = MotionState.UNKNOWN
                pending_state = None
                pending_since = None

            last_reliable_timestamp = timestamp
            result["reliable"] = True

            history.append({
                "timestamp": timestamp,
                "scale": scale,
            })

            cutoff = timestamp - self.trend_window_seconds

            while history and history[0]["timestamp"] < cutoff:
                history.popleft()

            if len(history) < self.min_reliable_samples:
                results.append(result)
                continue

            values = [entry["scale"] for entry in history]
            current_rate = median(values)

            previous = [
                entry["scale"]
                for entry in history
                if entry["timestamp"] < timestamp - 0.2
            ]

            previous_rate = median(previous) if previous else None

            if abs(current_rate) <= self.stationary_threshold:
                instantaneous_state = MotionState.STATIONARY

            elif (
                previous_rate is not None
                and current_rate - previous_rate >= self.trend_threshold
            ):
                instantaneous_state = MotionState.ACCELERATING

            elif (
                previous_rate is not None
                and previous_rate - current_rate >= self.trend_threshold
            ):
                instantaneous_state = MotionState.DECELERATING

            else:
                instantaneous_state = MotionState.MOVING

            result["instantaneous_state_candidate"] = (
                instantaneous_state.value
            )

            if previous_rate is not None:
                result["trend"] = current_rate - previous_rate

            if instantaneous_state == current_state:
                pending_state = None
                pending_since = None

            else:
                if instantaneous_state != pending_state:
                    pending_state = instantaneous_state
                    pending_since = timestamp

                persistence = (
                    self.stationary_persistence_seconds
                    if pending_state == MotionState.STATIONARY
                    else self.transition_persistence_seconds
                )

                if (
                    pending_since is not None
                    and timestamp - pending_since >= persistence
                ):
                    current_state = pending_state
                    pending_state = None
                    pending_since = None
                    result["transition_confirmed"] = True

            result["motion_state_candidate"] = current_state.value
            results.append(result)

        state_counts = {}

        for state in MotionState:
            state_counts[state.value] = sum(
                1
                for item in results
                if item["motion_state_candidate"] == state.value
            )

        return {
            "measurement_count": len(results),
            "state_counts": state_counts,
            "measurements": results,
            "interpretation": (
                "Temporally stabilized candidate motion states derived "
                "from apparent image-space expansion. These are not "
                "calibrated speed, acceleration, or confirmed braking."
            ),
        }
