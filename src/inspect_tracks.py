from pathlib import Path
import pandas as pd


CSV_PATH = Path("data/processed/tracks.csv")


def main():

    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    df = pd.read_csv(CSV_PATH)

    print("=" * 70)
    print("SMARTLANE TRACKING INSPECTION")
    print("=" * 70)

    print(f"Rows: {len(df)}")
    print(f"Frames: {df['frame'].nunique()}")
    print(f"Unique track IDs: {df['track_id'].nunique()}")

    valid = df[df["track_id"] >= 0].copy()

    print()
    print("Valid tracks:", valid["track_id"].nunique())

    print()
    print("Class counts:")
    print(valid["class"].value_counts().to_string())

    print()
    print("Track duration summary:")

    track_summary = (
        valid
        .groupby("track_id")
        .agg(
            first_frame=("frame", "min"),
            last_frame=("frame", "max"),
            detections=("frame", "count"),
            mean_confidence=("confidence", "mean"),
            class_name=("class", lambda x: x.mode().iloc[0])
        )
        .sort_values("detections", ascending=False)
    )

    print(track_summary.head(30).to_string())

    print()
    print("Longest tracks:")

    longest = track_summary.head(15)

    for track_id, row in longest.iterrows():

        duration = (
            row["last_frame"] - row["first_frame"] + 1
        )

        continuity = (
            row["detections"] / duration
            if duration > 0
            else 0
        )

        print(
            f"Track {track_id:4d} | "
            f"class={row['class_name']:10s} | "
            f"frames={row['detections']:4.0f} | "
            f"range={row['first_frame']:4.0f}-{row['last_frame']:4.0f} | "
            f"continuity={continuity:.2%} | "
            f"confidence={row['mean_confidence']:.3f}"
        )


if __name__ == "__main__":
    main()