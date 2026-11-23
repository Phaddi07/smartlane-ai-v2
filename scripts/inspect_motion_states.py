
import json
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent

path = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "test_drive_motion_state.json"
)

with path.open(encoding="utf-8") as file:
    data = json.load(file)

groups = defaultdict(list)

for item in data["measurements"]:
    timestamp = item["timestamp_seconds"]

    if timestamp is not None and 10.0 <= timestamp <= 21.5:
        bucket = int(timestamp * 2) / 2
        groups[bucket].append(item)

print("TIME | COUNT | STATIONARY | MOVING | ACCEL | DECEL | UNKNOWN")

for timestamp, items in sorted(groups.items()):
    counts = Counter(
        item["motion_state_candidate"]
        for item in items
    )

    print(
        f"{timestamp:4.1f} | "
        f"{len(items):5} | "
        f"{counts['stationary']:10} | "
        f"{counts['moving']:6} | "
        f"{counts['accelerating']:5} | "
        f"{counts['decelerating']:5} | "
        f"{counts['unknown']:7}"
    )
