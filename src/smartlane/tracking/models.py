from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from smartlane.models import BoundingBox, VehicleType


@dataclass
class TrackedVehicle:
    track_id: int
    vehicle_type: VehicleType

    bbox: BoundingBox

    confidence: float

    center_x: float
    center_y: float

    speed_mps: Optional[float] = None
    acceleration_mps2: Optional[float] = None

    lane_id: Optional[int] = None

    is_ego: bool = False


@dataclass
class FrameTracks:
    frame_number: int
    timestamp_seconds: float

    vehicles: list[TrackedVehicle] = field(default_factory=list)