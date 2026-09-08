import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOCK_DIR = ROOT / "data" / "mock" / "scenario_01"


def load(name):
    return json.loads(
        (MOCK_DIR / f"{name}.json").read_text(encoding="utf-8")
    )


def test_cross_contract_consistency():
    behavior = load("behavior_event")
    interaction = load("interaction")
    incident = load("incident")
    responsibility = load("responsibility")
    trip_report = load("trip_report")
    vehicle_track = load("vehicle_track")
    ego_state = load("ego_state")
    lane_geometry = load("lane_geometry")
    driver_score = load("driver_score")

    # ---------------------------------------------------------
    # 1. Behavior event temporal validity
    # ---------------------------------------------------------
    assert behavior["start_frame"] <= behavior["end_frame"]
    assert behavior["start_time_seconds"] <= behavior["end_time_seconds"]

    # ---------------------------------------------------------
    # 2. Interaction temporal validity
    # ---------------------------------------------------------
    assert interaction["start_frame"] <= interaction["end_frame"]
    assert interaction["start_time_seconds"] <= interaction["end_time_seconds"]

    # ---------------------------------------------------------
    # 3. Incident temporal validity
    # ---------------------------------------------------------
    assert incident["start_frame"] <= incident["end_frame"]
    assert incident["start_time_seconds"] <= incident["end_time_seconds"]

    # ---------------------------------------------------------
    # 4. Ego vehicle consistency
    # ---------------------------------------------------------
    assert interaction["ego_vehicle_id"] == 0
    assert 0 in incident["involved_vehicle_ids"]
    assert behavior["subject"]["type"] == "ego"

    # ---------------------------------------------------------
    # 5. Lead vehicle consistency
    # ---------------------------------------------------------
    lead_vehicle_id = interaction["other_vehicle_id"]

    assert lead_vehicle_id in behavior["related_vehicle_ids"]
    assert lead_vehicle_id in incident["involved_vehicle_ids"]
    assert vehicle_track["track_id"] == lead_vehicle_id
    assert vehicle_track["is_ego"] is False

    # ---------------------------------------------------------
    # 6. Incident references behavior
    # ---------------------------------------------------------
    assert behavior["event_id"] in incident["related_behavior_event_ids"]

    # ---------------------------------------------------------
    # 7. Incident references interaction
    # ---------------------------------------------------------
    assert interaction["interaction_id"] in incident["related_interaction_ids"]

    # ---------------------------------------------------------
    # 8. Responsibility references incident
    # ---------------------------------------------------------
    assert responsibility["incident_id"] == incident["incident_id"]

    # ---------------------------------------------------------
    # 9. Trip report contains the same objects
    # ---------------------------------------------------------
    assert any(
        event["event_id"] == behavior["event_id"]
        for event in trip_report["behavior_events"]
    )

    assert any(
        item["incident_id"] == incident["incident_id"]
        for item in trip_report["incidents"]
    )

    assert any(
        item["incident_id"] == responsibility["incident_id"]
        for item in trip_report["responsibility_assessments"]
    )

    # ---------------------------------------------------------
    # 10. Trip report score matches standalone score
    # ---------------------------------------------------------
    assert trip_report["score"]["score"] == driver_score["score"]
    assert trip_report["score"]["rating"] == driver_score["rating"]

    score_fields = [
        "following_score",
        "braking_score",
        "acceleration_score",
        "lane_behavior_score",
        "interaction_score",
        "incident_score",
    ]

    for field in score_fields:
        assert trip_report["score"][field] == driver_score[field]

    # ---------------------------------------------------------
    # 11. Ego state is temporally aligned with the interaction
    # ---------------------------------------------------------
    assert (
        interaction["start_frame"]
        <= ego_state["frame_number"]
        <= interaction["end_frame"]
    )

    # ---------------------------------------------------------
    # 12. Ego state is temporally aligned with lane geometry
    # ---------------------------------------------------------
    assert ego_state["frame_number"] == lane_geometry["frame_number"]

    # ---------------------------------------------------------
    # 13. Vehicle observations are ordered
    # ---------------------------------------------------------
    observation_frames = [
        observation["frame_number"]
        for observation in vehicle_track["observations"]
    ]

    assert observation_frames == sorted(observation_frames)

    # ---------------------------------------------------------
    # 14. Vehicle observation timestamps are ordered
    # ---------------------------------------------------------
    observation_times = [
        observation["timestamp_seconds"]
        for observation in vehicle_track["observations"]
    ]

    assert observation_times == sorted(observation_times)

    # ---------------------------------------------------------
    # 15. All incident vehicles are represented consistently
    # ---------------------------------------------------------
    assert set(incident["involved_vehicle_ids"]) == {
        interaction["ego_vehicle_id"],
        interaction["other_vehicle_id"],
    }
