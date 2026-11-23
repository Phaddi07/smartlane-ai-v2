
from smartlane.models import (
    BoundingBox,
    VideoMetadata,
    VehicleType,
)
from smartlane.tracking.models import FrameTracks, TrackedVehicle
from smartlane.tracking.tracker import TrackingOutput
from smartlane.incidents.collision_detector import CollisionDetector


def make_vehicle(track_id, area):
    width = 1920
    height = 1080

    box_width = (area * width * height) ** 0.5
    box_height = box_width

    center_x = width * 0.5
    center_y = height * 0.65

    bbox = BoundingBox(
        center_x - box_width / 2,
        center_y - box_height / 2,
        center_x + box_width / 2,
        center_y + box_height / 2,
    )

    return TrackedVehicle(
        track_id=track_id,
        vehicle_type=VehicleType.CAR,
        bbox=bbox,
        confidence=0.9,
        center_x=center_x,
        center_y=center_y,
        identity_id=track_id,
    )


def make_tracking_output(expansion=True, fps=20.0):
    metadata = VideoMetadata(
        video_id="test",
        source_path="synthetic.mp4",
        width=1920,
        height=1080,
        fps=fps,
        frame_count=40,
        duration_seconds=2.0,
    )

    frames = []

    for frame_number in range(30):
        timestamp = frame_number / fps

        area = 0.02
        if expansion and timestamp >= 1.0:
            area = 0.04

        frames.append(
            FrameTracks(
                frame_number=frame_number,
                timestamp_seconds=timestamp,
                vehicles=[make_vehicle(12, area)],
            )
        )

    return TrackingOutput(
        metadata=metadata,
        frame_tracks=frames,
        vehicle_tracks={},
    )


def make_stationary_states(timestamps):
    return {
        "measurements": [
            {
                "timestamp_seconds": timestamp,
                "frame_number": round(timestamp * 20),
                "motion_state_candidate": "stationary",
                "reliable": True,
            }
            for timestamp in timestamps
        ]
    }


def test_expansion_and_sustained_stationary_produce_candidate():
    tracking = make_tracking_output()

    states = make_stationary_states(
        [1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40]
    )

    incidents = CollisionDetector().analyze(tracking, states)

    assert len(incidents) == 1
    assert incidents[0].incident_type.value == "collision_candidate"
    assert incidents[0].confidence is None
    assert (
            incidents[0].evidence["confidence_status"]
            == "unavailable_uncalibrated"
    )
    assert incidents[0].evidence["lead_vehicle_identity_id"] == 12


def test_expansion_without_stationary_confirmation_produces_no_candidate():
    tracking = make_tracking_output()

    states = make_stationary_states(
        [1.0, 1.05, 1.10, 1.15, 1.20]
    )

    incidents = CollisionDetector().analyze(tracking, states)

    assert incidents == []


def test_broken_stationary_sequence_produces_no_candidate():
    tracking = make_tracking_output()

    states = make_stationary_states(
        [1.0, 1.05, 1.10, 1.30, 1.35, 1.40]
    )

    incidents = CollisionDetector().analyze(tracking, states)

    assert incidents == []


def test_invalid_video_metadata_produces_no_candidate():
    tracking = make_tracking_output()
    tracking.metadata.fps = 0

    states = make_stationary_states(
        [1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40]
    )

    incidents = CollisionDetector().analyze(tracking, states)

    assert incidents == []
