
from smartlane.models import (
    Incident,
    IncidentType,
    ResponsibilityClass,
)
from smartlane.responsibility.assessor import ResponsibilityAssessor


def make_incident(incident_type):
    return Incident(
        incident_id="incident_001",
        start_frame=100,
        end_frame=150,
        start_time_seconds=5.0,
        end_time_seconds=7.5,
        involved_vehicle_ids=[12, 64],
        incident_type=incident_type,
        confidence=0.0,
        evidence={"test_evidence": True},
    )


def test_collision_candidate_is_indeterminate():
    assessments = ResponsibilityAssessor().analyze(
        [make_incident(IncidentType.COLLISION_CANDIDATE)]
    )

    assert len(assessments) == 1
    assert assessments[0].classification == ResponsibilityClass.INDETERMINATE


def test_responsibility_confidence_remains_zero():
    assessments = ResponsibilityAssessor().analyze(
        [make_incident(IncidentType.COLLISION_CANDIDATE)]
    )

    assert assessments[0].confidence == 0.0


def test_missing_evidence_is_explicitly_reported():
    assessments = ResponsibilityAssessor().analyze(
        [make_incident(IncidentType.COLLISION_CANDIDATE)]
    )

    evidence = assessments[0].evidence

    assert evidence["missing_evidence"]
    assert evidence["limitations"]
    assert "Collision detection does not establish fault." in evidence["limitations"]


def test_non_collision_incidents_are_ignored():
    incidents = [
        make_incident(IncidentType.NEAR_COLLISION),
        make_incident(IncidentType.UNSAFE_FOLLOWING),
    ]

    assessments = ResponsibilityAssessor().analyze(incidents)

    assert assessments == []


def test_empty_incident_list_returns_empty_assessments():
    assessments = ResponsibilityAssessor().analyze([])

    assert assessments == []
