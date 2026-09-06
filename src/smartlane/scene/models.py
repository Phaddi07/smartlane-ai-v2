from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RoadType(str, Enum):
    UNKNOWN = "unknown"
    URBAN = "urban"
    HIGHWAY = "highway"
    INTERSECTION = "intersection"
    RAMP = "ramp"


class TrafficDensity(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONGESTED = "congested"


@dataclass
class SceneState:
    frame_number: int
    timestamp_seconds: float

    road_type: RoadType = RoadType.UNKNOWN
    traffic_density: TrafficDensity = TrafficDensity.UNKNOWN

    lane_count: Optional[int] = None

    construction_present: bool = False
    intersection_present: bool = False
    merge_present: bool = False
    split_present: bool = False

    confidence: float = 0.0

    evidence: dict = field(default_factory=dict)