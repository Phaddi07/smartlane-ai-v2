
import json
from pathlib import Path
from collections import defaultdict
from statistics import median

PROJECT_ROOT = Path(__file__).resolve().parent.parent

path = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "test_drive_motion_signal.json"
)

with path.open(encoding="utf-8") as file:
    data = json.load(file)

groups = defaultdict(list)

# Inspect the transition from 13.5 to 18.5 seconds
# using half-second intervals.
for item in data["measurements"]:
    if not item["reliable"]:
        continue

    timestamp = item["timestamp_seconds"]

    if 13.5 <= timestamp <= 18.5:
        half_second = int(timestamp * 2) / 2
        groups[half_second].append(item)

print("TIME  | COUNT | SCALE RATE | VERTICAL FLOW")

for timestamp, items in sorted(groups.items()):
    scale = [
        x["smoothed_scale_rate"]
        for x in items
        if x["smoothed_scale_rate"] is not None
    ]

    vertical = [
        x["smoothed_vertical_flow_rate"]
        for x in items
        if x["smoothed_vertical_flow_rate"] is not None
    ]

    scale_value = median(scale) if scale else float("nan")
    vertical_value = median(vertical) if vertical else float("nan")

    print(
        f"{timestamp:4.1f} | {len(items):5} | "
        f"{scale_value:10.6f} | {vertical_value:14.6f}"
    )
