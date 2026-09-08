import pandas as pd
import numpy as np
from pathlib import Path


INPUT = Path("data/processed/tracks_caronly.csv")
OUTPUT = Path("data/processed/incident_interactions.csv")

ACCIDENT_TRACK_ID = 125
START_FRAME = 340
END_FRAME = 447

IOU_THRESHOLD = 0.05


def iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)

    intersection = iw * ih

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)

    union = area_a + area_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def center(row):
    return (
        (row["bbox_x1"] + row["bbox_x2"]) / 2.0,
        (row["bbox_y1"] + row["bbox_y2"]) / 2.0,
    )


print("=" * 70)
print("SMARTLANE INCIDENT INTERACTION ANALYSIS")
print("=" * 70)

df = pd.read_csv(INPUT)

df = df[
    (df["frame"] >= START_FRAME)
    & (df["frame"] <= END_FRAME)
].copy()

accident = df[df["track_id"] == ACCIDENT_TRACK_ID].copy()

if accident.empty:
    raise RuntimeError(
        f"Accident track {ACCIDENT_TRACK_ID} not found "
        f"in frames {START_FRAME}-{END_FRAME}"
    )

print(f"Accident track: {ACCIDENT_TRACK_ID}")
print(f"Frames: {START_FRAME} -> {END_FRAME}")
print(f"Accident detections: {len(accident)}")

other_tracks = sorted(
    set(df["track_id"].unique()) - {ACCIDENT_TRACK_ID}
)

print(f"Other tracks examined: {len(other_tracks)}")

records = []

for frame in range(START_FRAME, END_FRAME + 1):

    accident_rows = accident[accident["frame"] == frame]

    if accident_rows.empty:
        continue

    a = accident_rows.iloc[0]

    a_box = (
        a["bbox_x1"],
        a["bbox_y1"],
        a["bbox_x2"],
        a["bbox_y2"],
    )

    ax, ay = center(a)

    frame_rows = df[
        (df["frame"] == frame)
        & (df["track_id"] != ACCIDENT_TRACK_ID)
    ]

    for _, other in frame_rows.iterrows():

        b_box = (
            other["bbox_x1"],
            other["bbox_y1"],
            other["bbox_x2"],
            other["bbox_y2"],
        )

        bx, by = center(other)

        dx = bx - ax
        dy = by - ay

        center_distance = float(np.sqrt(dx * dx + dy * dy))

        overlap = iou(a_box, b_box)

        accident_width = a["bbox_x2"] - a["bbox_x1"]
        accident_height = a["bbox_y2"] - a["bbox_y1"]

        scale = max(
            1.0,
            np.sqrt(accident_width ** 2 + accident_height ** 2)
        )

        normalized_distance = center_distance / scale

        records.append({
            "frame": frame,
            "accident_track_id": ACCIDENT_TRACK_ID,
            "other_track_id": int(other["track_id"]),
            "center_distance": center_distance,
            "normalized_distance": normalized_distance,
            "horizontal_offset": dx,
            "vertical_offset": dy,
            "iou": overlap,
            "other_confidence": other["confidence"],
        })


if not records:
    raise RuntimeError("No interactions found in the incident window.")

result = pd.DataFrame(records)

# A lower normalized distance and higher IoU indicate stronger interaction.
result["interaction_score"] = (
    1.0 / (1.0 + result["normalized_distance"])
    + result["iou"] * 2.0
)

result = result.sort_values(
    ["frame", "interaction_score"],
    ascending=[True, False]
)

result.to_csv(OUTPUT, index=False)

print()
print("=" * 70)
print("STRONGEST INTERACTING TRACKS")
print("=" * 70)

summary = (
    result.groupby("other_track_id")
    .agg(
        frames=("frame", "count"),
        first_frame=("frame", "min"),
        last_frame=("frame", "max"),
        min_distance=("normalized_distance", "min"),
        max_iou=("iou", "max"),
        mean_iou=("iou", "mean"),
        max_interaction=("interaction_score", "max"),
    )
    .sort_values(
        ["max_interaction", "max_iou"],
        ascending=False
    )
)

print(summary.to_string())

print()
print("=" * 70)
print("TOP INTERACTION EVENTS")
print("=" * 70)

top = result.nlargest(20, "interaction_score")

print(
    top[
        [
            "frame",
            "other_track_id",
            "normalized_distance",
            "iou",
            "horizontal_offset",
            "vertical_offset",
            "interaction_score",
        ]
    ].to_string(index=False)
)

print()
print("=" * 70)
print(f"Saved: {OUTPUT}")
print("=" * 70)