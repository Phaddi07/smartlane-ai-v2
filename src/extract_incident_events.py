import pandas as pd
from pathlib import Path


INPUT = Path("data/processed/incident_timeline.csv")
OUTPUT = Path("data/processed/incidents.csv")


# =========================================================
# CONFIG
# =========================================================

MIN_IOU = 0.10
HIGH_IOU = 0.40

# Maximum frame gap allowed when grouping observations
MAX_FRAME_GAP = 5


# =========================================================
# LOAD
# =========================================================

df = pd.read_csv(INPUT)

df = df.sort_values(
    ["other_track_id", "frame"]
).copy()


if df.empty:
    raise RuntimeError("incident_timeline.csv is empty.")


# =========================================================
# DETERMINE STRONG INTERACTION
# =========================================================

df["strong_interaction"] = (
    (df["iou"] >= MIN_IOU)
    | (df["normalized_distance"] <= 0.20)
)


# Only keep frames where an interaction is actually present
interaction_df = df[df["strong_interaction"]].copy()


if interaction_df.empty:
    print("No strong interactions detected.")
    pd.DataFrame().to_csv(OUTPUT, index=False)
    raise SystemExit


# =========================================================
# GROUP CONTIGUOUS INTERACTIONS
# =========================================================

events = []

for other_track_id, group in interaction_df.groupby("other_track_id"):

    group = group.sort_values("frame")

    current = []
    previous_frame = None

    for _, row in group.iterrows():

        frame = int(row["frame"])

        if (
            previous_frame is not None
            and frame - previous_frame > MAX_FRAME_GAP
        ):
            if current:
                events.append(current)

            current = []

        current.append(row)
        previous_frame = frame

    if current:
        events.append(current)


# =========================================================
# BUILD EVENT SUMMARIES
# =========================================================

event_rows = []

for event_id, rows in enumerate(events, start=1):

    event = pd.DataFrame(rows)

    peak_iou_idx = event["iou"].idxmax()
    peak_distance_idx = event["normalized_distance"].idxmin()

    peak_iou_row = event.loc[peak_iou_idx]
    peak_distance_row = event.loc[peak_distance_idx]

    start_frame = int(event["frame"].min())
    end_frame = int(event["frame"].max())

    peak_iou = float(event["iou"].max())
    min_distance = float(event["normalized_distance"].min())

    # -----------------------------------------------------
    # Determine basic interaction classification
    # -----------------------------------------------------

    if peak_iou >= HIGH_IOU:
        classification = "HIGH_INTERACTION"

    elif peak_iou >= MIN_IOU:
        classification = "INTERACTION"

    else:
        classification = "PROXIMITY_EVENT"

    # -----------------------------------------------------
    # Determine temporal trend
    # -----------------------------------------------------

    first_distance = float(
        event.iloc[0]["normalized_distance"]
    )

    last_distance = float(
        event.iloc[-1]["normalized_distance"]
    )

    if last_distance < first_distance - 0.02:
        trend = "CLOSING"

    elif last_distance > first_distance + 0.02:
        trend = "SEPARATING"

    else:
        trend = "STABLE"

    event_rows.append({
        "incident_id": event_id,
        "accident_track_id": 125,
        "other_track_id": int(event["other_track_id"].iloc[0]),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "duration_frames": end_frame - start_frame + 1,
        "observations": len(event),
        "peak_iou": peak_iou,
        "peak_iou_frame": int(
            peak_iou_row["frame"]
        ),
        "min_normalized_distance": min_distance,
        "min_distance_frame": int(
            peak_distance_row["frame"]
        ),
        "initial_distance": first_distance,
        "final_distance": last_distance,
        "trend": trend,
        "classification": classification,
    })


# =========================================================
# SAVE
# =========================================================

incidents = pd.DataFrame(event_rows)

incidents = incidents.sort_values(
    "peak_iou",
    ascending=False
).reset_index(drop=True)

# Re-number incident IDs after sorting
incidents["incident_id"] = range(
    1,
    len(incidents) + 1
)

incidents.to_csv(
    OUTPUT,
    index=False
)


# =========================================================
# DISPLAY
# =========================================================

print("=" * 70)
print("SMARTLANE INCIDENT EVENT EXTRACTION")
print("=" * 70)

print()
print(f"Interactions examined: {len(df)}")
print(f"Incident events found: {len(incidents)}")

print()
print("=" * 70)
print("INCIDENT EVENTS")
print("=" * 70)

print(
    incidents.to_string(index=False)
)

print()
print("=" * 70)
print(f"Saved: {OUTPUT}")
print("=" * 70)