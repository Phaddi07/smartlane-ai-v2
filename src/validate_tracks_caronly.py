from pathlib import Path
import pandas as pd
import numpy as np


CSV_PATH = Path("data/processed/tracks_caronly.csv")


def calculate_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)

    intersection = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)

    union = area_a + area_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def main():

    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    df = pd.read_csv(CSV_PATH)

    print("=" * 70)
    print("SMARTLANE TRACK VALIDATION")
    print("=" * 70)

    print(f"Rows: {len(df)}")
    print(f"Frames: {df['frame'].nunique()}")

    valid = df[df["track_id"] >= 0].copy()

    # --------------------------------------------------------
    # 1. Class instability
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("1. CLASS INSTABILITY")
    print("=" * 70)

    class_counts = (
        valid
        .groupby(["track_id", "class"])
        .size()
        .unstack(fill_value=0)
    )

    unstable_tracks = []

    for track_id, row in class_counts.iterrows():

        classes = row[row > 0]

        if len(classes) > 1:

            unstable_tracks.append({
                "track_id": track_id,
                "classes": ", ".join(
                    f"{cls}={count}"
                    for cls, count in classes.items()
                )
            })

    if unstable_tracks:

        print(
            f"Tracks with multiple detected classes: "
            f"{len(unstable_tracks)}"
        )

        for item in unstable_tracks:
            print(
                f"Track {item['track_id']}: "
                f"{item['classes']}"
            )

    else:
        print("No class instability detected.")

    # --------------------------------------------------------
    # 2. Duplicate overlapping detections
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("2. OVERLAPPING TRACKS")
    print("=" * 70)

    duplicate_events = []

    for frame, group in valid.groupby("frame"):

        records = group.to_dict("records")

        for i in range(len(records)):

            for j in range(i + 1, len(records)):

                a = records[i]
                b = records[j]

                if a["track_id"] == b["track_id"]:
                    continue

                box_a = (
                    a["bbox_x1"],
                    a["bbox_y1"],
                    a["bbox_x2"],
                    a["bbox_y2"],
                )

                box_b = (
                    b["bbox_x1"],
                    b["bbox_y1"],
                    b["bbox_x2"],
                    b["bbox_y2"],
                )

                iou = calculate_iou(box_a, box_b)

                if iou >= 0.70:

                    duplicate_events.append({
                        "frame": int(frame),
                        "track_a": int(a["track_id"]),
                        "track_b": int(b["track_id"]),
                        "class_a": a["class"],
                        "class_b": b["class"],
                        "iou": iou,
                    })

    print(
        f"High-overlap track pairs: "
        f"{len(duplicate_events)}"
    )

    if duplicate_events:

        print()
        print("Top suspicious overlaps:")

        duplicate_events.sort(
            key=lambda x: x["iou"],
            reverse=True
        )

        for event in duplicate_events[:30]:

            print(
                f"Frame {event['frame']:4d} | "
                f"Track {event['track_a']:4d} "
                f"({event['class_a']}) ↔ "
                f"Track {event['track_b']:4d} "
                f"({event['class_b']}) | "
                f"IoU={event['iou']:.3f}"
            )

    # --------------------------------------------------------
    # 3. Track continuity
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("3. TRACK CONTINUITY")
    print("=" * 70)

    continuity_rows = []

    for track_id, group in valid.groupby("track_id"):

        frames = sorted(
            group["frame"].astype(int).unique()
        )

        if not frames:
            continue

        first = frames[0]
        last = frames[-1]

        expected = last - first + 1
        actual = len(frames)

        continuity = actual / expected

        gaps = []

        for previous, current in zip(
            frames[:-1],
            frames[1:]
        ):

            gap = current - previous - 1

            if gap > 0:
                gaps.append(gap)

        continuity_rows.append({
            "track_id": int(track_id),
            "first_frame": first,
            "last_frame": last,
            "detections": actual,
            "continuity": continuity,
            "max_gap": max(gaps) if gaps else 0,
            "total_missing": expected - actual,
        })

    continuity_df = pd.DataFrame(
        continuity_rows
    )

    suspicious_continuity = continuity_df[
        (continuity_df["detections"] >= 10) &
        (continuity_df["continuity"] < 0.75)
    ].sort_values(
        "continuity"
    )

    if len(suspicious_continuity):

        print(
            "Tracks with significant gaps:"
        )

        print(
            suspicious_continuity
            .head(30)
            .to_string(index=False)
        )

    else:

        print(
            "No major continuity problems "
            "found using current threshold."
        )

    # --------------------------------------------------------
    # 4. Spatial jumps
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("4. SPATIAL JUMPS")
    print("=" * 70)

    jump_events = []

    for track_id, group in valid.groupby("track_id"):

        group = group.sort_values("frame")

        previous = None

        for _, row in group.iterrows():

            if previous is not None:

                frame_delta = (
                    int(row["frame"])
                    - int(previous["frame"])
                )

                if frame_delta > 0:

                    dx = (
                        row["center_x"]
                        - previous["center_x"]
                    )

                    dy = (
                        row["center_y"]
                        - previous["center_y"]
                    )

                    distance = np.sqrt(
                        dx ** 2 + dy ** 2
                    )

                    # Large image-space movement per frame.
                    # This is only a diagnostic threshold.
                    movement_per_frame = (
                        distance / frame_delta
                    )

                    if movement_per_frame > 250:

                        jump_events.append({
                            "track_id": int(track_id),
                            "frame": int(row["frame"]),
                            "movement": movement_per_frame,
                            "dx": dx,
                            "dy": dy,
                        })

            previous = row

    print(
        f"Large spatial jumps: {len(jump_events)}"
    )

    for event in jump_events[:30]:

        print(
            f"Track {event['track_id']:4d} | "
            f"Frame {event['frame']:4d} | "
            f"Movement={event['movement']:.1f}px/frame | "
            f"dx={event['dx']:.1f} | "
            f"dy={event['dy']:.1f}"
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    print(
        f"Valid tracks: "
        f"{valid['track_id'].nunique()}"
    )

    print(
        f"Class-unstable tracks: "
        f"{len(unstable_tracks)}"
    )

    print(
        f"High-overlap events: "
        f"{len(duplicate_events)}"
    )

    print(
        f"Large spatial jumps: "
        f"{len(jump_events)}"
    )


if __name__ == "__main__":
    main()