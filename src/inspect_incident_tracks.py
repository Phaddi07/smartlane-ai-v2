import pandas as pd
import numpy as np

CSV_PATH = "data/processed/tracks_caronly.csv"

START_FRAME = 300
END_FRAME = 447

df = pd.read_csv(CSV_PATH)

# Ignore unassigned tracker IDs
df = df[df["track_id"] != -1].copy()

# Restrict to accident/end sequence
incident = df[
    (df["frame"] >= START_FRAME) &
    (df["frame"] <= END_FRAME)
].copy()

print("=" * 70)
print("SMARTLANE INCIDENT TRACK INSPECTION")
print("=" * 70)

print(f"Frames inspected: {START_FRAME} -> {END_FRAME}")
print(f"Rows: {len(incident)}")
print()

# Track summary
summary = (
    incident.groupby("track_id")
    .agg(
    	first_frame=("frame", "min"),
    	last_frame=("frame", "max"),
    	detections=("frame", "count"),
    	mean_confidence=("confidence", "mean"),
    	min_x=("bbox_x1", "min"),
    	max_x=("bbox_x2", "max"),
    	min_y=("bbox_y1", "min"),
    	max_y=("bbox_y2", "max"),
    )
    .sort_values(["detections", "first_frame"], ascending=[False, True])
)

print("=" * 70)
print("TRACKS PRESENT DURING END SEQUENCE")
print("=" * 70)

print(summary.to_string())

print()
print("=" * 70)
print("TRACKS REACHING THE FINAL 30 FRAMES")
print("=" * 70)

final_tracks = summary[summary["last_frame"] >= 417]

if len(final_tracks) == 0:
    print("No tracks detected in final 30 frames.")
else:
    print(final_tracks.to_string())

print()
print("=" * 70)
print("TRACK CONTINUITY THROUGH INCIDENT")
print("=" * 70)

for track_id in final_tracks.index:
    t = incident[incident["track_id"] == track_id].sort_values("frame")

    frames = t["frame"].to_numpy()

    if len(frames) > 1:
        gaps = np.diff(frames)
        max_gap = gaps.max()
        missing = np.sum(gaps - 1)
    else:
        max_gap = 0
        missing = 0

    print(
        f"Track {int(track_id):>4}: "
        f"{int(t['frame'].min())}-{int(t['frame'].max())} | "
        f"detections={len(t):>3} | "
        f"max_gap={max_gap:>2} | "
        f"missing={missing:>3}"
    )

print()
print("=" * 70)
print("FINAL FRAME TRACKS")
print("=" * 70)

last_frame = incident["frame"].max()

last = incident[incident["frame"] == last_frame].copy()

if len(last) == 0:
    print("No detections on final frame.")
else:
    columns = [
        "track_id",
        "class",
        "confidence",
        "bbox_x1",
    	"bbox_y1",
    	"bbox_x2",
    	"bbox_y2",
    ]

    print(last[columns].to_string(index=False))

print()
print("=" * 70)
print("DONE")
print("=" * 70)