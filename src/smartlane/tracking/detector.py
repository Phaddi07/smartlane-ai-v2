from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

from smartlane.models import BoundingBox, VehicleType
from smartlane.tracking.models import TrackedVehicle


# COCO vehicle class IDs used by YOLO.
COCO_VEHICLE_CLASSES = {
    2: VehicleType.CAR,
    3: VehicleType.MOTORCYCLE,
    5: VehicleType.BUS,
    7: VehicleType.TRUCK,
}


class VehicleDetector:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.40,
        tracker_config: str = "bytetrack.yaml",
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1.")

        if not Path(tracker_config).is_file():
            # Ultralytics also accepts its built-in tracker config names.
            if tracker_config not in {"bytetrack.yaml", "botsort.yaml"}:
                raise FileNotFoundError(
                    f"Tracker configuration not found: {tracker_config}"
                )

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.tracker_config = tracker_config

    def track_frame(self, frame) -> list[TrackedVehicle]:
        results = self.model.track(
            frame,
            persist=True,
            tracker=self.tracker_config,
            classes=list(COCO_VEHICLE_CLASSES),
            conf=self.confidence_threshold,
            verbose=False,
        )

        if not results:
            return []

        boxes = results[0].boxes

        if boxes is None or boxes.id is None:
            return []

        tracked_vehicles: list[TrackedVehicle] = []

        xyxy_values = boxes.xyxy.cpu().tolist()
        confidence_values = boxes.conf.cpu().tolist()
        class_values = boxes.cls.cpu().tolist()
        track_ids = boxes.id.int().cpu().tolist()

        for coordinates, confidence, class_id, track_id in zip(
            xyxy_values,
            confidence_values,
            class_values,
            track_ids,
        ):
            vehicle_type = COCO_VEHICLE_CLASSES.get(int(class_id))

            # Never turn a missing or invalid tracker ID into a persistent track.
            if vehicle_type is None or track_id < 0:
                continue

            bbox = BoundingBox(
                x1=float(coordinates[0]),
                y1=float(coordinates[1]),
                x2=float(coordinates[2]),
                y2=float(coordinates[3]),
            )

            tracked_vehicles.append(
                TrackedVehicle(
                    track_id=int(track_id),
                    vehicle_type=vehicle_type,
                    bbox=bbox,
                    confidence=float(confidence),
                    center_x=bbox.center_x,
                    center_y=bbox.center_y,
                )
            )

        return tracked_vehicles