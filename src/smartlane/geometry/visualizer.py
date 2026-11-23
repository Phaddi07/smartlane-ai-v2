from smartlane.geometry.lane_tracker import LaneTemporalTracker

from pathlib import Path

import cv2

from smartlane.geometry.lane_detector import LaneDetector


def annotate_lane_video(
    video_path: str | Path,
    output_path: str | Path,
) -> dict:

    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    detector = LaneDetector()
    tracker = LaneTemporalTracker()
    frame_number = 0
    detected_frames = 0

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            timestamp = frame_number / fps if fps > 0 else 0.0

            context = tracker.update(
            detector.detect(
                frame,
                frame_number,
                timestamp,
            )
            )

            if context.lane_boundaries:
                detected_frames += 1

            for boundary in context.lane_boundaries:
                points = boundary.points

                for first, second in zip(points, points[1:]):
                    p1 = (int(first.x), int(first.y))
                    p2 = (int(second.x), int(second.y))

                    cv2.line(
                        frame,
                        p1,
                        p2,
                        (0, 255, 0),
                        5,
                    )

                for point in points:
                    cv2.circle(
                        frame,
                        (int(point.x), int(point.y)),
                        5,
                        (0, 0, 255),
                        -1,
                    )

            cv2.putText(
                frame,
                f"Lane candidates: {len(context.lane_boundaries)}",
                (30, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )

            writer.write(frame)
            frame_number += 1

    finally:
        cap.release()
        writer.release()

    return {
        "output_path": str(output_path),
        "frames_processed": frame_number,
        "frames_with_candidates": detected_frames,
        "detection_rate": (
            detected_frames / frame_number
            if frame_number else 0.0
        ),
    }
