import pandas as pd
from pathlib import Path


INPUT = Path("data/processed/incident_interactions.csv")
OUTPUT = Path("data/processed/incident_timeline.csv")


df = pd.read_csv(INPUT)

df = df.sort_values(
    ["other_track_id", "frame"]
).copy()


# =========================================================
# TEMPORAL CHANGES
# =========================================================

df["distance_change"] = (
    df.groupby("other_track_id")["normalized_distance"]
    .diff()
)

df["iou_change"] = (
    df.groupby("other_track_id")["iou"]
    .diff()
)


# Negative distance change = getting closer
# Positive distance change = getting farther away

df["approaching"] = df["distance_change"] < -0.005
df["separating"] = df["distance_change"] > 0.005


# =========================================================
# INTERACTION STATE
# =========================================================

def classify_state(row):

    distance = row["normalized_distance"]
    overlap = row["iou"]

    if overlap >= 0.40:
        return "HIGH_OVERLAP"

    if overlap >= 0.10:
        return "OVERLAP"

    if distance <= 0.20 and row["approaching"]:
        return "CLOSING"

    if distance <= 0.30 and row["separating"]:
        return "SEPARATING"

    if distance <= 0.40:
        return "NEAR"

    return "DISTANT"


df["state"] = df.apply(classify_state, axis=1)


# =========================================================
# PRINT TIMELINE FOR EACH INTERACTING VEHICLE
# =========================================================

print("=" * 70)
print("SMARTLANE INCIDENT TIMELINE")
print("=" * 70)

for track_id, group in df.groupby("other_track_id"):

    print()
    print("-" * 70)
    print(f"INTERACTING TRACK: {track_id}")
    print("-" * 70)

    print(
        group[
            [
                "frame",
                "normalized_distance",
                "iou",
                "distance_change",
                "state",
            ]
        ].to_string(index=False)
    )


# =========================================================
# SUMMARY
# =========================================================

summary = (
    df.groupby("other_track_id")
    .agg(
        first_frame=("frame", "min"),
        last_frame=("frame", "max"),
        frames=("frame", "count"),
        min_distance=("normalized_distance", "min"),
        max_iou=("iou", "max"),
        mean_iou=("iou", "mean"),
        max_horizontal_offset=("horizontal_offset", "max"),
        min_horizontal_offset=("horizontal_offset", "min"),
    )
)

summary["interaction_strength"] = (
    (1 / (1 + summary["min_distance"]))
    + summary["max_iou"] * 2
)

summary = summary.sort_values(
    "interaction_strength",
    ascending=False
)


print()
print("=" * 70)
print("INTERACTION SUMMARY")
print("=" * 70)

print(summary.to_string())


# =========================================================
# SAVE
# =========================================================

df.to_csv(OUTPUT, index=False)

print()
print("=" * 70)
print(f"Saved: {OUTPUT}")
print("=" * 70)