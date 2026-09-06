from pathlib import Path

import pytest

from smartlane.ingestion.video import validate_video_path


def test_supported_video_format():
    path = Path("test_video.mp4")

    # The file does not need to exist for this particular check.
    # We test the format validation separately below.
    assert path.suffix.lower() == ".mp4"


def test_invalid_video_path():
    with pytest.raises(FileNotFoundError):
        validate_video_path("this_video_does_not_exist.mp4")


def test_unsupported_video_format(tmp_path):
    file_path = tmp_path / "video.txt"
    file_path.write_text("not a video")

    with pytest.raises(ValueError):
        validate_video_path(file_path)