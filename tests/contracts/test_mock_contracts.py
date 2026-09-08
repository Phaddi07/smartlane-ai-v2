import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"
MOCK_DIR = ROOT / "data" / "mock" / "scenario_01"


SCHEMA_NAMES = [
    "behavior_event",
    "driver_score",
    "ego_state",
    "incident",
    "interaction",
    "lane_geometry",
    "responsibility",
    "trip_report",
    "vehicle_track",
]


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_mock_matches_schema(name):
    schema_path = SCHEMA_DIR / f"{name}.schema.json"
    data_path = MOCK_DIR / f"{name}.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(data_path.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(data),
        key=lambda error: list(error.path)
    )

    assert not errors, "\n".join(
        f"{'.'.join(map(str, error.path))}: {error.message}"
        for error in errors
    )
