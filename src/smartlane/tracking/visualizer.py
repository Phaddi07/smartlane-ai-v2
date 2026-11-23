
from pathlib import Path

import cv2

from smartlane.ingestion import iter_frames


def annotate_tracking_video(
    video_path: str | Path,
    tracking_output,
    output_path: str | Path = "data/processed/tracking_demo.mp4",
    incidents: list | None = None,
    lane_contexts: list | None = None,
    behavior_events: list | None = None,
) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tracks_by_frame = {
        frame_tracks.frame_number: frame_tracks
        for frame_tracks in tracking_output.frame_tracks
    }

    lanes_by_frame = {
        context.frame_number: context
        for context in (lane_contexts or [])
    }

    events_by_frame = {}

    for event in behavior_events or []:
        for frame in range(event.start_frame, event.end_frame + 1):
            events_by_frame.setdefault(frame, []).append(event)

    incidents = incidents or []

    fps = tracking_output.metadata.fps
    if not fps or fps <= 0:
        raise ValueError("Video FPS must be greater than zero.")

    writer = None
    frames_written = 0
    total_boxes = 0
    incident_frames = 0

    try:
        for frame_state, frame in iter_frames(video_path):
            if writer is None:
                height, width = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(
                    str(output_path),
                    fourcc,
                    fps,
                    (width, height),
                )

                if not writer.isOpened():
                    raise RuntimeError(
                        f"Could not create output video: {output_path}"
                    )

            frame_number = frame_state.frame_number
            timestamp = frame_state.timestamp_seconds

            frame_tracks = tracks_by_frame.get(frame_number)
            vehicles = frame_tracks.vehicles if frame_tracks else []

            # Draw detected lane-boundary candidates.
            lane_context = lanes_by_frame.get(frame_number)

            if lane_context:
                for boundary in lane_context.lane_boundaries:
                    points = boundary.points

                    for first, second in zip(points, points[1:]):
                        cv2.line(
                            frame,
                            (int(first.x), int(first.y)),
                            (int(second.x), int(second.y)),
                            (0, 255, 0),
                            4,
                        )

            active_events = events_by_frame.get(frame_number, [])

            active_incidents = [
                incident
                for incident in incidents
                if incident.start_frame <= frame_number <= incident.end_frame
            ]

            highlighted_ids = {
                vehicle_id
                for incident in active_incidents
                for vehicle_id in incident.involved_vehicle_ids
            }

            for vehicle in vehicles:
                x1 = int(vehicle.bbox.x1)
                y1 = int(vehicle.bbox.y1)
                x2 = int(vehicle.bbox.x2)
                y2 = int(vehicle.bbox.y2)

                highlighted = vehicle.track_id in highlighted_ids

                if highlighted:
                    color = (0, 0, 255)
                    thickness = 4
                else:
                    color = (
                        (vehicle.track_id * 37) % 200 + 55,
                        (vehicle.track_id * 67) % 200 + 55,
                        (vehicle.track_id * 97) % 200 + 55,
                    )
                    thickness = 2

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    thickness,
                )

                vehicle_type = getattr(
                    vehicle.vehicle_type,
                    "value",
                    str(vehicle.vehicle_type),
                )

                label = (
                    f"ID {vehicle.track_id} | "
                    f"{vehicle_type} | "
                    f"{vehicle.confidence:.2f}"
                )

                if highlighted:
                    label = f"INCIDENT | {label}"

                label_y = max(20, y1 - 8)

                cv2.putText(
                    frame,
                    label,
                    (x1, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

            overlay = (
                f"Frame: {frame_number} | "
                f"Time: {timestamp:.2f}s | "
                f"Vehicles: {len(vehicles)}"
            )

            cv2.putText(
                frame,
                overlay,
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

            # Display behavior candidates, not confirmed violations.
            labels = set()

            for event in active_events:
                behavior = str(event.behavior_type).lower()

                if "following" in behavior:
                    labels.add("FOLLOWING CANDIDATE")

                elif "braking" in behavior:
                    labels.add("POSSIBLE DECELERATION")

            for index, label in enumerate(sorted(labels)):
                cv2.putText(
                    frame,
                    label,
                    (20, 145 + index * 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 200, 255),
                    2,
                )

            if active_incidents:
                incident_frames += 1

                banner = "COLLISION CANDIDATE DETECTED"

                cv2.rectangle(
                    frame,
                    (10, 55),
                    (min(frame.shape[1] - 10, 660), 115),
                    (0, 0, 180),
                    -1,
                )

                cv2.putText(
                    frame,
                    banner,
                    (25, 82),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2,
                )

                cv2.putText(
                    frame,
                    "Fault not determined",
                    (25, 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                )

            writer.write(frame)
            frames_written += 1
            total_boxes += len(vehicles)

    finally:
        if writer is not None:
            writer.release()

    if frames_written == 0:
        raise RuntimeError("No video frames were written.")

    return {
        "output_path": str(output_path),
        "frames_written": frames_written,
        "total_boxes": total_boxes,
        "incident_frames": incident_frames,
    }
