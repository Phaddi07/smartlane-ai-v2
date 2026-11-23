from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from smartlane.tracking.identity import TrackIdentityAssociator
from smartlane.ingestion import iter_frames, read_video_metadata
from smartlane.models import (
    VehicleObservation,
    VehicleTrack,
    VideoMetadata,
)
from smartlane.tracking.detector import VehicleDetector
from smartlane.tracking.models import FrameTracks


@dataclass
class TrackingOutput:
    metadata: VideoMetadata
    frame_tracks: list[FrameTracks] = field(default_factory=list)
    vehicle_tracks: dict[int, VehicleTrack] = field(default_factory=dict)
    identity_map: dict[int, int] = field(default_factory=dict)


class VehicleTracker:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.40,
        tracker_config: str = "bytetrack.yaml",
    ) -> None:
        self.detector = VehicleDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            tracker_config=tracker_config,
        )

    def process_video(self, video_path: str | Path) -> TrackingOutput:
        metadata = read_video_metadata(video_path)

        output = TrackingOutput(metadata=metadata)

        for frame_state, frame in iter_frames(video_path):
            vehicles = self.detector.track_frame(frame)

            frame_result = FrameTracks(
                frame_number=frame_state.frame_number,
                timestamp_seconds=frame_state.timestamp_seconds,
                vehicles=vehicles,
            )

            output.frame_tracks.append(frame_result)

            for vehicle in vehicles:
                observation = VehicleObservation(
                    frame_number=frame_state.frame_number,
                    timestamp_seconds=frame_state.timestamp_seconds,
                    bbox=vehicle.bbox,
                    confidence=vehicle.confidence,
                    vehicle_type=vehicle.vehicle_type,
                )

                existing_track = output.vehicle_tracks.get(vehicle.track_id)

                if existing_track is None:
                    existing_track = VehicleTrack(
                        track_id=vehicle.track_id,
                        vehicle_type=vehicle.vehicle_type,
                    )
                    output.vehicle_tracks[vehicle.track_id] = existing_track

                existing_track.observations.append(observation)

                if existing_track.first_frame is None:
                    existing_track.first_frame = frame_state.frame_number

                existing_track.last_frame = frame_state.frame_number

            output.identity_map = TrackIdentityAssociator().associate(output)

        return output
