from smartlane.models import (
    BehaviorEvent,
    BehaviorSubject,
    BoundingBox,
    DriverRating,
    DriverScore,
    EgoState,
    Incident,
    IncidentSeverity,
    IncidentType,
    Interaction,
    LaneBoundary,
    LaneBoundaryPoint,
    LaneContext,
    MotionState,
    ResponsibilityAssessment,
    ResponsibilityClass,
    VehicleObservation,
    VehicleTrack,
    VehicleType,
)


def test_vehicle_track_model():
    observation = VehicleObservation(
        frame_number=180,
        timestamp_seconds=8.67,
        bbox=BoundingBox(820, 390, 1040, 610),
        confidence=0.94,
        vehicle_type=VehicleType.CAR,
    )

    track = VehicleTrack(
        track_id=24,
        vehicle_type=VehicleType.CAR,
        is_ego=False,
        observations=[observation],
        first_frame=180,
        last_frame=180,
    )

    assert track.track_id == 24
    assert track.is_ego is False
    assert track.observations[0].bbox.width == 220
    assert track.observations[0].bbox.height == 220


def test_ego_state_model():
    state = EgoState(
        frame_number=220,
        timestamp_seconds=10.60,
        speed_mps=11.8,
        acceleration_mps2=-4.8,
        lane_id=2,
        motion_state=MotionState.DECELERATING,
        confidence=0.96,
    )

    assert state.frame_number == 220
    assert state.motion_state == MotionState.DECELERATING
    assert state.acceleration_mps2 == -4.8


def test_lane_geometry_model():
    boundary = LaneBoundary(
        boundary_id=1,
        points=[
            LaneBoundaryPoint(0.12, 0.95),
            LaneBoundaryPoint(0.35, 0.45),
        ],
        confidence=0.91,
    )

    lane = LaneContext(
        frame_number=220,
        timestamp_seconds=10.60,
        lane_count=3,
        ego_lane_id=2,
        lane_boundaries=[boundary],
        confidence=0.89,
    )

    assert lane.lane_count == 3
    assert lane.ego_lane_id == 2
    assert lane.lane_boundaries[0].points[1].x == 0.35


def test_behavior_event_model():
    event = BehaviorEvent(
        event_id="BE-001",
        behavior_type="braking",
        subject=BehaviorSubject(type="ego", id=None),
        start_frame=210,
        end_frame=225,
        start_time_seconds=10.12,
        end_time_seconds=10.84,
        magnitude=-4.8,
        confidence=0.94,
        related_vehicle_ids=[24],
    )

    assert event.event_id == "BE-001"
    assert event.subject.type == "ego"
    assert event.subject.id is None
    assert 24 in event.related_vehicle_ids


def test_interaction_model():
    interaction = Interaction(
        interaction_id="INT-001",
        ego_vehicle_id=0,
        other_vehicle_id=24,
        start_frame=180,
        end_frame=235,
        start_time_seconds=8.67,
        end_time_seconds=11.33,
        min_distance_m=2.4,
        min_normalized_distance=0.18,
        relative_speed_mps=5.2,
        closing_rate_mps=5.2,
        time_headway_seconds=0.91,
        interaction_type="closing_then_separating",
        confidence=0.93,
        related_behavior_event_ids=["BE-001"],
    )

    assert interaction.ego_vehicle_id == 0
    assert interaction.other_vehicle_id == 24
    assert interaction.time_headway_seconds == 0.91
    assert "BE-001" in interaction.related_behavior_event_ids


def test_incident_model():
    incident = Incident(
        incident_id="INC-001",
        start_frame=205,
        end_frame=228,
        start_time_seconds=9.88,
        end_time_seconds=10.99,
        involved_vehicle_ids=[0, 24],
        incident_type=IncidentType.NEAR_COLLISION,
        severity=IncidentSeverity.HIGH,
        confidence=0.91,
        related_behavior_event_ids=["BE-001"],
        related_interaction_ids=["INT-001"],
    )

    assert incident.incident_type == IncidentType.NEAR_COLLISION
    assert incident.severity == IncidentSeverity.HIGH
    assert incident.involved_vehicle_ids == [0, 24]


def test_responsibility_model():
    assessment = ResponsibilityAssessment(
        incident_id="INC-001",
        classification=ResponsibilityClass.POV_PRIMARY,
        confidence=0.84,
        reasoning="The ego vehicle approached the lead vehicle too quickly.",
    )

    assert assessment.incident_id == "INC-001"
    assert assessment.classification == ResponsibilityClass.POV_PRIMARY
    assert assessment.confidence == 0.84


def test_driver_score_model():
    score = DriverScore(
        score=850,
        following_score=82,
        braking_score=74,
        acceleration_score=100,
        lane_behavior_score=100,
        interaction_score=86,
        incident_score=82,
        rating=DriverRating.GOOD,
    )

    assert score.score == 850
    assert score.rating == DriverRating.GOOD
    assert score.braking_score == 74
