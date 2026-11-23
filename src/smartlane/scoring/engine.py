
from __future__ import annotations

from smartlane.models import (
    BehaviorSeverity,
    BehaviorValidationStatus,
    DriverRating,
    DriverScore,
    ScoreEvidence,
    ScorePenalty,
)


class ScoringEngine:
    BASE_SCORE = 1000

    PENALTY_POINTS = {
        BehaviorSeverity.MINOR: 20,
        BehaviorSeverity.MODERATE: 50,
        BehaviorSeverity.SEVERE: 100,
    }

    CATEGORY_MAP = {
        "following": "following_score",
        "braking": "braking_score",
        "acceleration": "acceleration_score",
        "lane_change": "lane_behavior_score",
        "cut_in": "interaction_score",
        "merge": "interaction_score",
        "sudden_movement": "interaction_score",
    }

    def calculate(
        self,
        behavior_events,
        incidents=None,
        validated_behaviors=None,
    ) -> DriverScore:
        incidents = incidents or []
        validated_behaviors = validated_behaviors or []

        evidence = []
        penalties = []
        seen_event_ids = set()

        category_deductions = {
            "following_score": 0,
            "braking_score": 0,
            "acceleration_score": 0,
            "lane_behavior_score": 0,
            "interaction_score": 0,
            "incident_score": 0,
        }

        events_by_id = {
            event.event_id: event
            for event in behavior_events
        }

        for event in behavior_events:
            evidence.append(
                ScoreEvidence(
                    type=event.behavior_type.value,
                    value={
                        "event_id": event.event_id,
                        "confidence": event.confidence,
                        "start_time_seconds": event.start_time_seconds,
                        "end_time_seconds": event.end_time_seconds,
                        "classification": "observed_candidate",
                        "scoring_status": "not_penalized",
                    },
                )
            )

        for validated in validated_behaviors:
            event_id = validated.event_id

            if event_id in seen_event_ids:
                continue

            seen_event_ids.add(event_id)

            event = events_by_id.get(event_id)

            if event is None:
                continue

            confirmed = (
                validated.validation_status
                == BehaviorValidationStatus.CONFIRMED_MISTAKE
            )

            severity = validated.severity
            points = (
                self.PENALTY_POINTS.get(severity, 0)
                if confirmed else 0
            )

            if points > 0:
                penalties.append(
                    ScorePenalty(
                        type=event.behavior_type.value,
                        severity=severity.value,
                        points=points,
                    )
                )

                category = self.CATEGORY_MAP.get(
                    event.behavior_type.value
                )

                if category:
                    category_deductions[category] += points

            evidence.append(
                ScoreEvidence(
                    type="behavior_validation",
                    value={
                        "event_id": event_id,
                        "validation_status": validated.validation_status.value,
                        "severity": severity.value if severity else None,
                        "penalty_points": points,
                        "reasoning": validated.reasoning,
                        "scoring_status": (
                            "penalized" if points else "not_penalized"
                        ),
                    },
                )
            )

        for incident in incidents:
            evidence.append(
                ScoreEvidence(
                    type="incident_observation",
                    value={
                        "incident_id": incident.incident_id,
                        "confidence": incident.confidence,
                        "classification": incident.incident_type.value,
                        "scoring_status": "not_penalized",
                        "reason": (
                            "Incident responsibility and driving "
                            "contribution have not been established."
                        ),
                    },
                )
            )

        evaluated_categories = sum(
            deduction > 0
            for deduction in category_deductions.values()
        )

        total_categories = len(category_deductions)
        evidence_coverage = evaluated_categories / total_categories

        if not penalties:
            evidence.append(
                ScoreEvidence(
                    type="scoring_status",
                    value={
                        "classification": "not_evaluated",
                        "evaluated_categories": 0,
                        "total_categories": total_categories,
                        "evidence_coverage": 0.0,
                        "score_interpretation": (
                            "No confirmed mistakes with applicable "
                            "penalties. Driving score not evaluated."
                        ),
                    },
                )
            )

            return DriverScore(
                score=None,
                rating=None,
                evidence_coverage=0.0,
                scoring_status="not_evaluated",
                penalties=[],
                evidence=evidence,
            )

        total_deduction = sum(
            penalty.points for penalty in penalties
        )

        score = max(0, self.BASE_SCORE - total_deduction)

        if score >= 900:
            rating = DriverRating.EXCELLENT
        elif score >= 750:
            rating = DriverRating.GOOD
        elif score >= 600:
            rating = DriverRating.MODERATE
        elif score >= 400:
            rating = DriverRating.POOR
        else:
            rating = DriverRating.CRITICAL

        category_scores = {
            name: (
                max(0, self.BASE_SCORE - deduction)
                if deduction > 0 else None
            )
            for name, deduction in category_deductions.items()
        }

        evidence.append(
            ScoreEvidence(
                type="scoring_status",
                value={
                    "classification": "evaluated",
                    "evaluated_categories": evaluated_categories,
                    "total_categories": total_categories,
                    "evidence_coverage": evidence_coverage,
                    "total_penalty_points": total_deduction,
                    "score_interpretation": (
                        "Preliminary score based on confirmed "
                        "behavior validations only."
                    ),
                },
            )
        )

        return DriverScore(
            score=score,
            following_score=category_scores["following_score"],
            braking_score=category_scores["braking_score"],
            acceleration_score=category_scores["acceleration_score"],
            lane_behavior_score=category_scores["lane_behavior_score"],
            interaction_score=category_scores["interaction_score"],
            incident_score=None,
            rating=rating,
            evidence_coverage=evidence_coverage,
            scoring_status="evaluated",
            penalties=penalties,
            evidence=evidence,
        )
