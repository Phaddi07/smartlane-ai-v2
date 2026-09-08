import pandas as pd
from pathlib import Path


# ============================================================
# SMARTLANE INCIDENT CHARACTERIZATION
# ============================================================

INPUT_FILE = Path(
    "data/processed/consolidated_incidents.csv"
)

OUTPUT_FILE = Path(
    "data/processed/incident_characterization.csv"
)

FPS = 20.754


def load_incidents():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    if df.empty:
        raise ValueError(
            "consolidated_incidents.csv is empty."
        )

    required_columns = [
        "consolidated_incident_id",
        "accident_track_id",
        "other_track_ids",
        "start_frame",
        "end_frame",
        "duration_frames",
        "interaction_events",
        "peak_iou",
        "peak_iou_frame",
        "min_normalized_distance",
        "min_distance_frame",
        "classifications",
        "trends",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    return df


def classify_interaction_intensity(peak_iou):
    """
    Classify interaction intensity from maximum
    bounding-box overlap.

    These are engineering categories, not ground-truth
    collision labels.
    """

    if peak_iou >= 0.50:
        return "VERY_HIGH"

    if peak_iou >= 0.25:
        return "HIGH"

    if peak_iou >= 0.10:
        return "MODERATE"

    return "LOW"


def classify_distance_proximity(min_distance):
    """
    Classify how close the normalized vehicle
    centers became.
    """

    if min_distance <= 0.10:
        return "VERY_CLOSE"

    if min_distance <= 0.20:
        return "CLOSE"

    if min_distance <= 0.35:
        return "MODERATE"

    return "DISTANT"


def determine_event_type(row):
    """
    Determine an incident-level candidate type from
    the available numerical interaction evidence.

    This does NOT claim that a collision definitely occurred.
    """

    peak_iou = float(row["peak_iou"])
    min_distance = float(
        row["min_normalized_distance"]
    )

    classifications = str(
        row["classifications"]
    )

    if peak_iou >= 0.50 and min_distance <= 0.20:
        return "COLLISION_CANDIDATE"

    if peak_iou >= 0.25 or min_distance <= 0.20:
        return "NEAR_COLLISION_CANDIDATE"

    if "HIGH_INTERACTION" in classifications:
        return "HIGH_INTERACTION"

    return "GENERAL_INTERACTION"


def determine_motion_pattern(trends):
    """
    Convert the collection of interaction trends
    into a simple incident-level motion pattern.
    """

    trends = str(trends)

    has_separating = "SEPARATING" in trends
    has_approaching = "APPROACHING" in trends
    has_stable = "STABLE" in trends

    if has_approaching and has_separating:
        return "APPROACHING_THEN_SEPARATING"

    if has_approaching:
        return "APPROACHING"

    if has_separating:
        return "SEPARATING"

    if has_stable:
        return "STABLE"

    return "UNKNOWN"


def build_description(row, event_type, intensity, proximity, motion):
    """
    Generate a concise machine-readable incident description.
    """

    accident_track = int(
        row["accident_track_id"]
    )

    other_tracks = str(
        row["other_track_ids"]
    )

    duration = float(
        row["duration_frames"]
    ) / FPS

    return (
        f"Track {accident_track} interacted with "
        f"track(s) {other_tracks} over approximately "
        f"{duration:.2f} seconds. "
        f"Peak overlap was {float(row['peak_iou']):.3f}, "
        f"with minimum normalized distance "
        f"{float(row['min_normalized_distance']):.3f}. "
        f"Interaction intensity: {intensity}. "
        f"Proximity: {proximity}. "
        f"Motion pattern: {motion}. "
        f"Event type: {event_type}."
    )


def characterize_incident(row):

    duration_seconds = (
        float(row["duration_frames"]) / FPS
    )

    intensity = classify_interaction_intensity(
        float(row["peak_iou"])
    )

    proximity = classify_distance_proximity(
        float(row["min_normalized_distance"])
    )

    event_type = determine_event_type(row)

    motion_pattern = determine_motion_pattern(
        row["trends"]
    )

    description = build_description(
        row,
        event_type,
        intensity,
        proximity,
        motion_pattern,
    )

    return {
        "incident_id": int(
            row["consolidated_incident_id"]
        ),
        "accident_track_id": int(
            row["accident_track_id"]
        ),
        "other_track_ids": str(
            row["other_track_ids"]
        ),
        "start_frame": int(
            row["start_frame"]
        ),
        "end_frame": int(
            row["end_frame"]
        ),
        "duration_frames": int(
            row["duration_frames"]
        ),
        "duration_seconds": round(
            duration_seconds,
            3
        ),
        "interaction_events": int(
            row["interaction_events"]
        ),
        "peak_iou": round(
            float(row["peak_iou"]),
            4
        ),
        "peak_iou_frame": int(
            row["peak_iou_frame"]
        ),
        "min_normalized_distance": round(
            float(row["min_normalized_distance"]),
            4
        ),
        "min_distance_frame": int(
            row["min_distance_frame"]
        ),
        "interaction_intensity": intensity,
        "proximity_level": proximity,
        "motion_pattern": motion_pattern,
        "event_type": event_type,
        "evidence_classifications": str(
            row["classifications"]
        ),
        "evidence_trends": str(
            row["trends"]
        ),
        "description": description,
    }


def main():

    print("=" * 70)
    print("SMARTLANE INCIDENT CHARACTERIZATION")
    print("=" * 70)

    df = load_incidents()

    print()
    print(f"Incidents loaded: {len(df)}")
    print()

    characterized = []

    for _, row in df.iterrows():
        characterized.append(
            characterize_incident(row)
        )

    result = pd.DataFrame(characterized)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("=" * 70)
    print("CHARACTERIZED INCIDENTS")
    print("=" * 70)

    print(
        result.to_string(index=False)
    )

    print()
    print("=" * 70)
    print(f"Saved: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()