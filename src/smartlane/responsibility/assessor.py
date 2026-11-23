from __future__ import annotations

from smartlane.models import (
    Incident,
    IncidentType,
    ResponsibilityAssessment,
    ResponsibilityClass,
)


class ResponsibilityAssessor:
    """
    Conservative responsibility assessment.

    Current prototype does not have sufficient evidence to
    determine collision fault. Assessments remain indeterminate
    until reliable behavioural and interaction evidence exists.
    """

    def analyze(
        self,
        incidents: list[Incident],
    ) -> list[ResponsibilityAssessment]:

        assessments = []

        for incident in incidents:
            if incident.incident_type != IncidentType.COLLISION_CANDIDATE:
                continue

            assessments.append(
                ResponsibilityAssessment(
                    incident_id=incident.incident_id,
                    classification=ResponsibilityClass.INDETERMINATE,
                    confidence=0.0,
                    reasoning=(
                        "Collision candidate detected, but available "
                        "evidence is insufficient to determine which "
                        "road user contributed to the incident."
                    ),
                    evidence={
                        "incident_type": incident.incident_type.value,
                        "incident_confidence": incident.confidence,
                        "available_evidence": incident.evidence,
                        "missing_evidence": [
                            "Reliable POV braking and acceleration measurements",
                            "Reliable relative distance and closing-speed estimates",
                            "Verified vehicle trajectories before the incident",
                            "Sufficient evidence of each road user's actions",
                        ],
                        "limitations": [
                            "Collision detection does not establish fault.",
                            "Vehicle bounding-box expansion is an image-space proxy.",
                            "POV stationary state does not establish responsibility.",
                            "No legal fault determination is performed.",
                        ],
                    },
                )
            )

        return assessments