import json
from pathlib import Path

root = Path("data/mock/scenario_01")
root.mkdir(parents=True, exist_ok=True)

behavior_event = {
    "event_id": "BE-001",
    "behavior_type": "braking",
    "subject": {
        "type": "ego",
        "id": None
    },
    "start_frame": 210,
    "end_frame": 225,
    "start_time_seconds": 10.12,
    "end_time_seconds": 10.84,
    "magnitude": -4.8,
    "confidence": 0.94,
    "related_vehicle_ids": [24],
    "evidence": {
        "reason": "Ego vehicle decelerated rapidly while following vehicle 24.",
        "peak_deceleration_mps2": -4.8,
        "min_time_headway_seconds": 0.91
    }
}

driver_score = {
    "score": 850,
    "following_score": 82,
    "braking_score": 74,
    "acceleration_score": 100,
    "lane_behavior_score": 100,
    "interaction_score": 86,
    "incident_score": 82,
    "rating": "GOOD",
    "penalties": [
        {
            "type": "hard_braking",
            "severity": "medium",
            "points": 30
        },
        {
            "type": "unsafe_following",
            "severity": "medium",
            "points": 30
        },
        {
            "type": "near_collision",
            "severity": "high",
            "points": 90
        }
    ],
    "evidence": [
        {
            "type": "starting_score",
            "value": 1000
        },
        {
            "type": "validated_behavior_events",
            "value": 1
        },
        {
            "type": "validated_incidents",
            "value": 1
        }
    ]
}

ego_state = {
    "frame_number": 220,
    "timestamp_seconds": 10.60,
    "speed_mps": 11.8,
    "acceleration_mps2": -4.8,
    "heading_degrees": 2.1,
    "lane_id": 2,
    "motion_state": "decelerating",
    "confidence": 0.96,
    "evidence": {
        "source": "vehicle_tracking",
        "reason": "Rapid deceleration during interaction with lead vehicle 24."
    }
}

interaction = {
    "interaction_id": "INT-001",
    "ego_vehicle_id": 0,
    "other_vehicle_id": 24,
    "start_frame": 180,
    "end_frame": 235,
    "start_time_seconds": 8.67,
    "end_time_seconds": 11.33,
    "min_distance_m": 2.4,
    "min_normalized_distance": 0.18,
    "relative_speed_mps": 5.2,
    "closing_rate_mps": 5.2,
    "time_headway_seconds": 0.91,
    "interaction_type": "closing_then_separating",
    "confidence": 0.93,
    "related_behavior_event_ids": ["BE-001"],
    "evidence": {
        "lead_vehicle_id": 24,
        "progression": "closing_then_separating"
    }
}

incident = {
    "incident_id": "INC-001",
    "start_frame": 205,
    "end_frame": 228,
    "start_time_seconds": 9.88,
    "end_time_seconds": 10.99,
    "involved_vehicle_ids": [0, 24],
    "incident_type": "near_collision",
    "severity": "high",
    "confidence": 0.91,
    "related_behavior_event_ids": ["BE-001"],
    "related_interaction_ids": ["INT-001"],
    "evidence": {
        "minimum_distance_m": 2.4,
        "minimum_time_headway_seconds": 0.91,
        "ego_hard_braking": True
    }
}

responsibility = {
    "incident_id": "INC-001",
    "classification": "pov_primary",
    "confidence": 0.84,
    "reasoning": "The ego vehicle approached the lead vehicle too quickly and required hard braking to avoid a collision.",
    "evidence": {
        "ego_closing_rate_mps": 5.2,
        "ego_hard_braking": True,
        "lead_vehicle_abrupt_action": False
    }
}

lane_geometry = {
    "frame_number": 220,
    "timestamp_seconds": 10.60,
    "lane_count": 3,
    "ego_lane_id": 2,
    "lane_boundaries": [
        {
            "boundary_id": 1,
            "points": [
                {"x": 0.12, "y": 0.95},
                {"x": 0.35, "y": 0.45}
            ],
            "confidence": 0.91
        },
        {
            "boundary_id": 2,
            "points": [
                {"x": 0.35, "y": 0.95},
                {"x": 0.50, "y": 0.45}
            ],
            "confidence": 0.92
        },
        {
            "boundary_id": 3,
            "points": [
                {"x": 0.67, "y": 0.95},
                {"x": 0.55, "y": 0.45}
            ],
            "confidence": 0.90
        },
        {
            "boundary_id": 4,
            "points": [
                {"x": 0.91, "y": 0.95},
                {"x": 0.70, "y": 0.45}
            ],
            "confidence": 0.88
        }
    ],
    "confidence": 0.89,
    "evidence": {
        "source": "road_geometry",
        "stable_lane_assignment": True
    }
}

vehicle_track = {
    "track_id": 24,
    "vehicle_type": "car",
    "is_ego": False,
    "first_frame": 1,
    "last_frame": 448,
    "observations": [
        {
            "frame_number": 180,
            "timestamp_seconds": 8.67,
            "bbox": {
                "x1": 820,
                "y1": 390,
                "x2": 1040,
                "y2": 610
            },
            "confidence": 0.94,
            "vehicle_type": "car"
        },
        {
            "frame_number": 205,
            "timestamp_seconds": 9.88,
            "bbox": {
                "x1": 835,
                "y1": 400,
                "x2": 1055,
                "y2": 620
            },
            "confidence": 0.95,
            "vehicle_type": "car"
        },
        {
            "frame_number": 220,
            "timestamp_seconds": 10.60,
            "bbox": {
                "x1": 850,
                "y1": 405,
                "x2": 1070,
                "y2": 625
            },
            "confidence": 0.96,
            "vehicle_type": "car"
        },
        {
            "frame_number": 235,
            "timestamp_seconds": 11.33,
            "bbox": {
                "x1": 875,
                "y1": 415,
                "x2": 1095,
                "y2": 635
            },
            "confidence": 0.95,
            "vehicle_type": "car"
        }
    ]
}

trip_report = {
    "report_id": "RPT-001",
    "video_id": "test_drive",
    "processing_mode": "batch",
    "duration_seconds": 21.63,
    "score": {"score": 850, "following_score": 82, "braking_score": 74, "acceleration_score": 100, "lane_behavior_score": 100, "interaction_score": 86, "incident_score": 82, "rating": "GOOD"},
    "behavior_events": [behavior_event],
    "incidents": [incident],
    "responsibility_assessments": [responsibility],
    "summary": "The drive was generally safe, but one high-risk following interaction resulted in hard braking and a near-collision.",
    "generated_at": "2026-09-08T14:00:00Z"
}

objects = {
    "behavior_event": behavior_event,
    "driver_score": driver_score,
    "ego_state": ego_state,
    "incident": incident,
    "interaction": interaction,
    "lane_geometry": lane_geometry,
    "responsibility": responsibility,
    "trip_report": trip_report,
    "vehicle_track": vehicle_track
}

for name, obj in objects.items():
    path = root / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

print(f"Created {len(objects)} mock contract objects.")

