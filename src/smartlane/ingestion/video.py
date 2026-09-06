from __future__ import annotations

import cv2
from pathlib import Path

from smartlane.models import VideoMetadata, FrameState


SUPPORTED_FORMATS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}


def validate_video_path(video_path: str | Path) -> Path:
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported video format: {path.suffix}. "
            f"Supported formats: {sorted(SUPPORTED_FORMATS)}"
        )

    return path


def read_video_metadata(video_path: str | Path) -> VideoMetadata:
    path = validate_video_path(video_path)

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    capture.release()

    if fps <= 0:
        raise ValueError("Video reports an invalid FPS.")

    duration_seconds = frame_count / fps

    return VideoMetadata(
        video_id=path.stem,
        source_path=str(path),
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=duration_seconds,
    )


def iter_frames(video_path: str | Path):
    path = validate_video_path(video_path)

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))

    if fps <= 0:
        capture.release()
        raise ValueError("Video reports an invalid FPS.")

    frame_number = 0

    try:
        while True:
            success, frame = capture.read()

            if not success:
                break

            timestamp_seconds = frame_number / fps

            state = FrameState(
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
                width=width,
                height=height,
            )

            yield state, frame

            frame_number += 1

    finally:
        capture.release()