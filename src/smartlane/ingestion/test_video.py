from pathlib import Path

from smartlane.ingestion.video import (
    iter_frames,
    read_video_metadata,
)


def inspect_video(video_path: str) -> None:
    print("=" * 60)
    print("SMARTLANE VIDEO INGESTION TEST")
    print("=" * 60)

    metadata = read_video_metadata(video_path)

    print(f"Video ID:       {metadata.video_id}")
    print(f"Resolution:     {metadata.width}x{metadata.height}")
    print(f"FPS:            {metadata.fps:.3f}")
    print(f"Frames:         {metadata.frame_count}")
    print(f"Duration:       {metadata.duration_seconds:.3f}s")
    print()

    frames_read = 0
    first_frame_shape = None
    last_timestamp = 0.0

    for frame_state, frame in iter_frames(video_path):
        frames_read += 1
        last_timestamp = frame_state.timestamp_seconds

        if first_frame_shape is None:
            first_frame_shape = frame.shape

        if frames_read >= metadata.frame_count:
            break

    print(f"Frames decoded: {frames_read}")
    print(f"First frame shape: {first_frame_shape}")
    print(f"Last timestamp: {last_timestamp:.3f}s")

    if frames_read != metadata.frame_count:
        print(
            f"WARNING: metadata reports {metadata.frame_count} frames "
            f"but {frames_read} were decoded."
        )
    else:
        print("Frame count check: PASS")

    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage:")
        print("python -m smartlane.ingestion.test_video <video_path>")
        raise SystemExit(1)

    inspect_video(sys.argv[1])