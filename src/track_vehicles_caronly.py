from pathlib import Path
import cv2
import pandas as pd
from ultralytics import YOLO


# ============================================================
# CONFIG
# ============================================================

VIDEO_PATH = Path("data/raw/test_drive.mp4")

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUTPUT_DIR / "tracks_caronly.csv"
DEBUG_VIDEO_PATH = OUTPUT_DIR / "tracking_debug_caronly.mp4"

# YOLO model.
# Start with the small model for development speed.
MODEL_NAME = "yolo11n.pt"

# COCO vehicle classes:
# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck
VEHICLE_CLASSES = {2}

CONFIDENCE_THRESHOLD = 0.30

# Tracker configuration.
# ByteTrack is a good first baseline.
TRACKER = "bytetrack.yaml"


# ============================================================
# HELPERS
# ============================================================

def get_class_name(class_id: int) -> str:
    names = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    }

    return names.get(class_id, "unknown")


# ============================================================
# MAIN
# ============================================================

def main():

    if not VIDEO_PATH.exists():
        raise FileNotFoundError(
            f"Input video not found: {VIDEO_PATH}"
        )

    print("=" * 70)
    print("SMARTLANE VEHICLE DETECTION + TRACKING")
    print("=" * 70)

    print(f"Input:  {VIDEO_PATH}")
    print(f"Model:  {MODEL_NAME}")
    print(f"Tracker: {TRACKER}")
    print()

    # --------------------------------------------------------
    # Open video
    # --------------------------------------------------------

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {VIDEO_PATH}"
        )

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video FPS:    {fps}")
    print(f"Video size:   {width} x {height}")

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print()
    print("Loading YOLO model...")

    model = YOLO(MODEL_NAME)

    print("Model loaded.")
    print()

    # --------------------------------------------------------
    # Debug video writer
    # --------------------------------------------------------

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        str(DEBUG_VIDEO_PATH),
        fourcc,
        fps,
        (width, height)
    )

    if not writer.isOpened():
        raise RuntimeError(
            f"Could not create debug video: {DEBUG_VIDEO_PATH}"
        )

    # --------------------------------------------------------
    # Tracking loop
    # --------------------------------------------------------

    rows = []

    frame_index = 0

    while True:

        success, frame = cap.read()

        if not success:
            break

        timestamp = frame_index / fps if fps > 0 else 0.0

        # ----------------------------------------------------
        # YOLO tracking
        # ----------------------------------------------------

        results = model.track(
            frame,
            persist=True,
            tracker=TRACKER,
            classes=list(VEHICLE_CLASSES),
            conf=CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        result = results[0]

        # ----------------------------------------------------
        # Extract detections
        # ----------------------------------------------------

        if result.boxes is not None:

            boxes = result.boxes

            xyxy = boxes.xyxy.cpu().numpy()

            confidences = boxes.conf.cpu().numpy()

            class_ids = boxes.cls.cpu().numpy().astype(int)

            if boxes.id is not None:
                track_ids = boxes.id.cpu().numpy().astype(int)
            else:
                track_ids = [-1] * len(xyxy)

            for bbox, confidence, class_id, track_id in zip(
                xyxy,
                confidences,
                class_ids,
                track_ids
            ):

                if class_id not in VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = bbox

                width_box = x2 - x1
                height_box = y2 - y1

                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                rows.append({
                    "frame": frame_index,
                    "timestamp": timestamp,

                    "track_id": int(track_id),

                    "class": get_class_name(class_id),
                    "class_id": int(class_id),

                    "confidence": float(confidence),

                    "bbox_x1": float(x1),
                    "bbox_y1": float(y1),
                    "bbox_x2": float(x2),
                    "bbox_y2": float(y2),

                    "center_x": float(center_x),
                    "center_y": float(center_y),

                    "width": float(width_box),
                    "height": float(height_box),
                })

        # ----------------------------------------------------
        # Draw tracking result
        # ----------------------------------------------------

        annotated = result.plot()

        writer.write(annotated)

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if frame_index % 50 == 0:

            print(
                f"Processed frame {frame_index}"
            )

        frame_index += 1

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    cap.release()
    writer.release()

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    df = pd.DataFrame(rows)

    df.to_csv(
        CSV_PATH,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TRACKING COMPLETE")
    print("=" * 70)

    print(f"Frames processed: {frame_index}")
    print(f"Detection rows:   {len(df)}")

    if len(df) > 0:

        valid_ids = df.loc[
            df["track_id"] >= 0,
            "track_id"
        ]

        print(
            f"Unique tracks:    {valid_ids.nunique()}"
        )

        print()
        print("Vehicle classes:")

        print(
            df["class"].value_counts().to_string()
        )

    print()
    print(f"CSV:   {CSV_PATH}")
    print(f"Video: {DEBUG_VIDEO_PATH}")


if __name__ == "__main__":
    main()