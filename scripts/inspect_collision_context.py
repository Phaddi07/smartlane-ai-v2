
from smartlane.tracking import VehicleTracker

tracking = VehicleTracker().process_video(
    "data/raw/test_drive.mp4"
)

width = tracking.metadata.width
height = tracking.metadata.height

print(
    "TIME | TRACK | CENTER X | CENTER Y | WIDTH | HEIGHT | AREA"
)

for frame in tracking.frame_tracks:
    t = frame.timestamp_seconds

    if not 14.0 <= t <= 18.5:
        continue

    for vehicle in frame.vehicles:
        if vehicle.track_id not in (12, 64):
            continue

        bbox = vehicle.bbox

        print(
            f"{t:5.2f} | "
            f"{vehicle.track_id:5} | "
            f"{bbox.center_x / width:8.3f} | "
            f"{bbox.center_y / height:8.3f} | "
            f"{bbox.width / width:5.3f} | "
            f"{bbox.height / height:6.3f} | "
            f"{bbox.width * bbox.height / (width * height):6.4f}"
        )
