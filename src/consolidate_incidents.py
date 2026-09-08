import pandas as pd
from pathlib import Path


# ============================================================
# SMARTLANE INCIDENT CONSOLIDATION
# ============================================================

INPUT_FILE = Path("data/processed/incidents.csv")
OUTPUT_FILE = Path("data/processed/consolidated_incidents.csv")

GAP_THRESHOLD = 15
OVERLAP_THRESHOLD = 0


def load_incidents():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    if df.empty:
        raise ValueError("incidents.csv is empty.")

    required_columns = [
        "incident_id",
        "accident_track_id",
        "other_track_id",
        "start_frame",
        "end_frame",
        "duration_frames",
        "observations",
        "peak_iou",
        "peak_iou_frame",
        "min_normalized_distance",
        "min_distance_frame",
        "initial_distance",
        "final_distance",
        "trend",
        "classification",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    return df


def incidents_are_related(a, b):
    """
    Determine whether two extracted interaction events
    belong to the same broader incident.

    They are considered related when:
    - they involve the same accident vehicle, and
    - their time windows overlap or are close together.
    """

    same_accident_vehicle = (
        a["accident_track_id"] == b["accident_track_id"]
    )

    if not same_accident_vehicle:
        return False

    a_end = int(a["end_frame"])
    b_start = int(b["start_frame"])

    b_end = int(b["end_frame"])
    a_start = int(a["start_frame"])

    # Distance between the two time windows.
    if a_end < b_start:
        gap = b_start - a_end
    elif b_end < a_start:
        gap = a_start - b_end
    else:
        gap = 0

    return gap <= GAP_THRESHOLD


def build_groups(df):
    """
    Group related interaction events into broader incidents.
    """

    df = df.sort_values(
        ["start_frame", "end_frame"]
    ).reset_index(drop=True)

    groups = []

    for _, row in df.iterrows():

        placed = False

        for group in groups:

            # Compare against the most recent event
            # in the group.
            last_event = group[-1]

            if incidents_are_related(last_event, row):
                group.append(row)
                placed = True
                break

        if not placed:
            groups.append([row])

    return groups


def consolidate_group(group, consolidated_id):
    """
    Convert multiple interaction events into one
    incident-level record.
    """

    group_df = pd.DataFrame(group)

    start_frame = int(group_df["start_frame"].min())
    end_frame = int(group_df["end_frame"].max())

    accident_track_id = int(
        group_df["accident_track_id"].iloc[0]
    )

    other_tracks = sorted(
        set(
            int(track)
            for track in group_df["other_track_id"]
        )
    )

    peak_iou_idx = group_df["peak_iou"].idxmax()
    peak_iou = float(
        group_df.loc[peak_iou_idx, "peak_iou"]
    )
    peak_iou_frame = int(
        group_df.loc[peak_iou_idx, "peak_iou_frame"]
    )

    min_distance_idx = group_df[
        "min_normalized_distance"
    ].idxmin()

    min_distance = float(
        group_df.loc[
            min_distance_idx,
            "min_normalized_distance"
        ]
    )

    min_distance_frame = int(
        group_df.loc[
            min_distance_idx,
            "min_distance_frame"
        ]
    )

    classifications = sorted(
        set(group_df["classification"].astype(str))
    )

    trends = sorted(
        set(group_df["trend"].astype(str))
    )

    return {
        "consolidated_incident_id": consolidated_id,
        "accident_track_id": accident_track_id,
        "other_track_ids": ",".join(
            str(track) for track in other_tracks
        ),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "duration_frames": end_frame - start_frame + 1,
        "interaction_events": len(group_df),
        "peak_iou": peak_iou,
        "peak_iou_frame": peak_iou_frame,
        "min_normalized_distance": min_distance,
        "min_distance_frame": min_distance_frame,
        "classifications": "|".join(classifications),
        "trends": "|".join(trends),
    }


def main():

    print("=" * 70)
    print("SMARTLANE INCIDENT CONSOLIDATION")
    print("=" * 70)

    df = load_incidents()

    print()
    print(f"Interaction events loaded: {len(df)}")
    print()

    groups = build_groups(df)

    print(f"Consolidated incidents: {len(groups)}")
    print()

    consolidated = []

    for incident_id, group in enumerate(groups, start=1):

        record = consolidate_group(
            group,
            incident_id
        )

        consolidated.append(record)

    result = pd.DataFrame(consolidated)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("=" * 70)
    print("CONSOLIDATED INCIDENTS")
    print("=" * 70)

    print(result.to_string(index=False))

    print()
    print("=" * 70)
    print(f"Saved: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()