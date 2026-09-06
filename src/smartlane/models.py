from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VehicleType(str, Enum):
    CAR = "car"
    TRUCK = "truck"
    BUS = "bus"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    UNKNOWN = "unknown"


class MotionState(str, Enum):
    STATIONARY = "stationary"
    MOVING = "moving"
    ACCELERATING = "accelerating"
    DECELERATING = "decelerating"
    UNKNOWN = "unknown"


class BehaviorType(str, Enum):
    BRAKING = "braking"
    ACCELERATION = "acceleration"
    LANE_CHANGE = "lane_change"
    FOLLOWING = "following"
    CUT_IN = "cut_in"
    MERGE = "merge"
    SUDDEN_MOVEMENT = "sudden_movement"


class ResponsibilityClass(str, Enum):
    POV_PRIMARY = "pov_primary"
    OTHER_VEHICLE_PRIMARY = "other_vehicle_primary"
    SHARED_CONTRIBUTION = "shared_contribution"
    NO_CONTRIBUTION_BY_POV = "no_contribution_by_pov"
    INDETERMINATE = "indeterminate"


@dataclass
class VideoMetadata:
    video_id: str
    source_path: str

    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float

    processing_mode: str = "batch"


@dataclass
class FrameState:
    frame_number: int
    timestamp_seconds: float

    width: int
    height: int


@dataclass
class EgoState:
    frame_number: int
    timestamp_seconds: float

    speed_mps: Optional[float] = None
    acceleration_mps2: Optional[float] = None
    heading_degrees: Optional[float] = None

    lane_id: Optional[int] = None
    motion_state: MotionState = MotionState.UNKNOWN

    confidence: float = 0.0


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass
class VehicleObservation:
    frame_number: int
    timestamp_seconds: float

    bbox: BoundingBox

    confidence: float
    vehicle_type: VehicleType = VehicleType.UNKNOWN


@dataclass
class VehicleTrack:
    track_id: int
    vehicle_type: VehicleType

    observations: list[VehicleObservation] = field(default_factory=list)

    first_frame: Optional[int] = None
    last_frame: Optional[int] = None


@dataclass
class LaneContext:
    frame_number: int
    timestamp_seconds: float

    lane_count: Optional[int] = None
    ego_lane_id: Optional[int] = None

    lane_boundaries: list = field(default_factory=list)

    confidence: float = 0.0


@dataclass
class BehaviorEvent:
    event_id: str
    behavior_type: BehaviorType

    subject_id: int
    start_frame: int
    end_frame: int

    start_time_seconds: float
    end_time_seconds: float

    magnitude: Optional[float] = None
    confidence: float = 0.0

    evidence: dict = field(default_factory=dict)


@dataclass
class Interaction:
    interaction_id: str

    ego_vehicle_id: int
    other_vehicle_id: int

    start_frame: int
    end_frame: int

    min_distance_m: Optional[float] = None
    relative_speed_mps: Optional[float] = None
    closing_rate_mps: Optional[float] = None
    time_headway_seconds: Optional[float] = None

    interaction_type: Optional[str] = None

    confidence: float = 0.0
    evidence: dict = field(default_factory=dict)


@dataclass
class Incident:
    incident_id: str

    start_frame: int
    end_frame: int

    start_time_seconds: float
    end_time_seconds: float

    involved_vehicle_ids: list[int] = field(default_factory=list)

    incident_type: Optional[str] = None

    severity: Optional[str] = None

    evidence: dict = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ResponsibilityAssessment:
    incident_id: str

    classification: ResponsibilityClass

    confidence: float

    reasoning: str

    evidence: dict = field(default_factory=dict)


@dataclass
class DriverScore:
    score: float

    following_score: float
    braking_score: float
    acceleration_score: float
    lane_behavior_score: float
    interaction_score: float
    incident_score: float

    evidence: list[dict] = field(default_factory=list)


@dataclass
class DriverReport:
    video_id: str

    score: DriverScore

    behavior_events: list[BehaviorEvent] = field(default_factory=list)
    incidents: list[Incident] = field(default_factory=list)
    responsibility_assessments: list[ResponsibilityAssessment] = field(
        default_factory=list
    )

    summary: str = ""