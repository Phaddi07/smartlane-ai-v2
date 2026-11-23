
from types import SimpleNamespace

from smartlane.models import BoundingBox, VehicleType
from smartlane.tracking.identity import TrackIdentityAssociator
from smartlane.tracking.models import FrameTracks, TrackedVehicle


def make_vehicle(track_id, bbox):
    return TrackedVehicle(
        track_id=track_id,
        vehicle_type=VehicleType.CAR,
        bbox=BoundingBox(*bbox),
        confidence=0.9,
        center_x=(bbox[0] + bbox[2]) / 2,
        center_y=(bbox[1] + bbox[3]) / 2,
    )


def make_output(frames, track_ids):
    return SimpleNamespace(
        metadata=SimpleNamespace(width=1920, height=1080),
        frame_tracks=frames,
        vehicle_tracks={track_id: None for track_id in track_ids},
    )


def test_duplicate_tracks_merge_after_repeated_overlap():
    frames = [
        FrameTracks(
            frame_number=i,
            timestamp_seconds=i / 20,
            vehicles=[
                make_vehicle(12, (400, 300, 800, 700)),
                make_vehicle(64, (410, 310, 790, 690)),
            ],
        )
        for i in range(2)
    ]

    output = make_output(frames, [12, 64])

    identity_map = TrackIdentityAssociator().associate(output)

    assert identity_map == {12: 12, 64: 12}
    assert all(
        vehicle.identity_id == 12
        for frame in frames
        for vehicle in frame.vehicles
    )


def test_unrelated_vehicles_remain_separate():
    frames = [
        FrameTracks(
            frame_number=i,
            timestamp_seconds=i / 20,
            vehicles=[
                make_vehicle(12, (100, 300, 300, 500)),
                make_vehicle(64, (1000, 300, 1200, 500)),
            ],
        )
        for i in range(3)
    ]

    output = make_output(frames, [12, 64])

    identity_map = TrackIdentityAssociator().associate(output)

    assert identity_map == {12: 12, 64: 64}


def test_single_frame_overlap_does_not_merge():
    frames = [
        FrameTracks(
            frame_number=0,
            timestamp_seconds=0.0,
            vehicles=[
                make_vehicle(12, (400, 300, 800, 700)),
                make_vehicle(64, (410, 310, 790, 690)),
            ],
        )
    ]

    output = make_output(frames, [12, 64])

    identity_map = TrackIdentityAssociator().associate(output)

    assert identity_map == {12: 12, 64: 64}


def test_empty_tracking_output_returns_empty_map():
    output = make_output([], [])

    identity_map = TrackIdentityAssociator().associate(output)

    assert identity_map == {}
