
from types import SimpleNamespace

from smartlane.models import (
    BehaviorType,
    IncidentType,
)
from smartlane.scoring.engine import ScoringEngine
from smartlane.models import (
    BehaviorSeverity,
    BehaviorValidationStatus,
    BehaviorType,
    IncidentType,
    ValidatedBehavior,
)


def make_event():
    return SimpleNamespace(
        event_id="following_001",
        behavior_type=BehaviorType.FOLLOWING,
        confidence=0.4,
        start_time_seconds=2.0,
        end_time_seconds=4.0,
    )


def make_incident():
    return SimpleNamespace(
        incident_id="collision_001",
        confidence=0.0,
        incident_type=IncidentType.COLLISION_CANDIDATE,
    )


def test_empty_evidence_returns_unevaluated_score():
    result = ScoringEngine().calculate([])

    assert result.score is None
    assert result.rating is None
    assert result.scoring_status == "not_evaluated"
    assert result.evidence_coverage == 0.0
    assert result.penalties == []


def test_candidate_behavior_is_recorded_without_penalty():
    result = ScoringEngine().calculate([make_event()])

    assert len(result.evidence) == 2
    assert result.evidence[0].type == "following"
    assert result.evidence[0].value["classification"] == "observed_candidate"
    assert result.evidence[0].value["scoring_status"] == "not_penalized"
    assert result.penalties == []


def test_collision_candidate_is_recorded_without_penalty():
    result = ScoringEngine().calculate([], [make_incident()])

    incident_evidence = result.evidence[0]

    assert incident_evidence.type == "incident_observation"
    assert incident_evidence.value["classification"] == "collision_candidate"
    assert incident_evidence.value["scoring_status"] == "not_penalized"
    assert result.penalties == []


def test_insufficient_evidence_keeps_all_scores_unevaluated():
    result = ScoringEngine().calculate(
        [make_event()],
        [make_incident()],
    )

    assert result.score is None
    assert result.rating is None

    assert result.following_score is None
    assert result.braking_score is None
    assert result.acceleration_score is None
    assert result.lane_behavior_score is None
    assert result.interaction_score is None
    assert result.incident_score is None


def test_evidence_coverage_remains_zero():
    result = ScoringEngine().calculate(
        [make_event()],
        [make_incident()],
    )

    assert result.evidence_coverage == 0.0
    assert result.scoring_status == "not_evaluated"


def test_scoring_status_is_included_in_evidence():
    result = ScoringEngine().calculate([])

    status = result.evidence[-1]

    assert status.type == "scoring_status"
    assert status.value["classification"] == "not_evaluated"
    assert status.value["evaluated_categories"] == 0
    assert status.value["total_categories"] == 6
def make_validated(event_id, status, severity=None):
    return ValidatedBehavior(
        event_id=event_id,
        validation_status=status,
        reasoning="Test validation",
        severity=severity,
    )


def test_confirmed_mistake_applies_severity_penalty():
    result = ScoringEngine().calculate(
        [make_event()],
        validated_behaviors=[
            make_validated(
                "following_001",
                BehaviorValidationStatus.CONFIRMED_MISTAKE,
                BehaviorSeverity.MODERATE,
            )
        ],
    )

    assert result.score == 950
    assert result.following_score == 950
    assert len(result.penalties) == 1
    assert result.penalties[0].points == 50
    assert result.scoring_status == "evaluated"


def test_rejected_behavior_receives_no_penalty():
    result = ScoringEngine().calculate(
        [make_event()],
        validated_behaviors=[
            make_validated(
                "following_001",
                BehaviorValidationStatus.REJECTED,
            )
        ],
    )

    assert result.penalties == []
    assert result.score is None


def test_duplicate_validation_does_not_double_penalize():
    validation = make_validated(
        "following_001",
        BehaviorValidationStatus.CONFIRMED_MISTAKE,
        BehaviorSeverity.SEVERE,
    )

    result = ScoringEngine().calculate(
        [make_event()],
        validated_behaviors=[validation, validation],
    )

    assert len(result.penalties) == 1
    assert result.score == 900


def test_score_never_drops_below_zero():
    events = [
        SimpleNamespace(
            event_id=f"following_{i}",
            behavior_type=BehaviorType.FOLLOWING,
            confidence=0.9,
            start_time_seconds=float(i),
            end_time_seconds=float(i + 1),
        )
        for i in range(11)
    ]

    validations = [
        make_validated(
            event.event_id,
            BehaviorValidationStatus.CONFIRMED_MISTAKE,
            BehaviorSeverity.SEVERE,
        )
        for event in events
    ]

    result = ScoringEngine().calculate(
        events,
        validated_behaviors=validations,
    )

    assert result.score == 0
