import json
import shutil
from pathlib import Path

import pytest

from src.agent.dispatcher import dispatch, is_error
from src.agent.state_store import StateStore
from src.agent.tool_registry import Tool, build_registry

SAMPLE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"


@pytest.fixture
def registry(tmp_path):
    path = tmp_path / "claims.json"
    shutil.copy(SAMPLE, path)  # never touch the real sample data
    return build_registry(StateStore(path))


def test_read_tools_return_json(registry):
    status = json.loads(dispatch(registry, "get_claim_status", {"claim_id": "CLM-001"}))
    assert status["status"] == "SUBMITTED"
    calc = json.loads(dispatch(registry, "calculate_claim", {"claim_id": "CLM-002"}))
    assert calc["recommended_status"] == "ESCALATED"
    claim = json.loads(dispatch(registry, "get_claim", {"claim_id": "CLM-003"}))
    assert claim["claim_id"] == "CLM-003"


def test_args_can_be_a_json_string(registry):
    out = dispatch(registry, "get_claim_status", '{"claim_id": "CLM-001"}')
    assert not is_error(out)


def test_calculate_does_not_change_state(registry):
    dispatch(registry, "calculate_claim", {"claim_id": "CLM-006"})
    out = json.loads(dispatch(registry, "get_claim_status", {"claim_id": "CLM-006"}))
    assert out["status"] == "SUBMITTED"


@pytest.mark.parametrize("name", ["delete_all", "", None, ["get_claim"], "__import__('os')"])
def test_unknown_tool_is_an_error_not_a_crash(registry, name):
    out = dispatch(registry, name, {})
    assert is_error(out)
    assert "Available tools" in out


@pytest.mark.parametrize("raw, fragment", [
    ("{not json", "not valid JSON"),
    ("[1, 2]", "JSON object"),
    ({}, "missing"),
    ({"claim_id": "CLM-001", "extra": 1}, "unknown argument"),
    ({"claim_id": 123}, "must be str"),
    ({"claim_id": True}, "must be str"),
])
def test_bad_arguments_return_error(registry, raw, fragment):
    out = dispatch(registry, "get_claim_status", raw)
    assert is_error(out)
    assert fragment in out


def test_missing_claim_returns_error(registry):
    out = dispatch(registry, "get_claim_status", {"claim_id": "CLM-999"})
    assert out == "Error: Claim not found: CLM-999"


def test_injection_text_is_just_data(registry):
    out = dispatch(registry, "get_claim", {"claim_id": "__import__('os').system('echo hi')"})
    assert is_error(out)
    assert "not found" in out


def test_tool_bug_does_not_crash_the_run(registry):
    def boom(claim_id: str) -> dict:
        raise RuntimeError("disk on fire")

    registry.register(Tool("boom", "Always fails.", {"claim_id": str}, boom))
    out = dispatch(registry, "boom", {"claim_id": "CLM-001"})
    assert out.startswith("Error: ") and "RuntimeError" in out
    assert not is_error(dispatch(registry, "get_claim", {"claim_id": "CLM-001"}))  # still works


def test_schemas_describe_every_tool(registry):
    schemas = {s["name"]: s for s in registry.schemas()}
    assert set(schemas) == {"get_claim", "get_claim_status", "calculate_claim", "submit_decision"}
    assert schemas["calculate_claim"]["input_schema"]["required"] == ["claim_id"]