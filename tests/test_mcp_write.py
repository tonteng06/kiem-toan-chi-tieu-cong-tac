"""Write boundary and actual stdio persistence/read-back regression tests."""
import json
import shutil
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from src.agent.state_store import StateStore, DEFAULT_PATH
from src.agent.business_rules import calculate_claim
from src.mcp_server.agent_bridge import required_policy_refs
from src.mcp_server.server import submit_decision


def arguments(store, claim_id="CLM-001"):
    claim = store.get(claim_id)
    calc = calculate_claim(claim)
    return dict(claim_id=claim_id, decision=calc["recommended_status"], reason=calc["summary"],
                evidence_refs=sorted(required_policy_refs(claim, calc)))


@pytest.fixture
def store(tmp_path):
    target = tmp_path / "claims.json"
    shutil.copyfile(DEFAULT_PATH, target)
    return StateStore(target)


def test_real_file_persistence_and_terminal_transition(store):
    args = arguments(store)
    with patch("src.mcp_server.server._get_store", return_value=store):
        reply = submit_decision(**args)
        assert StateStore(store.path).get(args["claim_id"]).status.value == reply["status"] == "APPROVED"
        with pytest.raises(ToolError, match="Invalid transition"):
            submit_decision(**args)


@pytest.mark.parametrize("change", [
    {"reason": " "}, {"decision": "NO_ANSWER"}, {"decision": "REJECTED"},
    {"evidence_refs": []}, {"evidence_refs": ["DOC999@v1.0"]}, {"claim_id": "CLM-999"},
])
def test_invalid_write_never_changes_disk(store, change):
    args = arguments(store)
    args.update(change)
    before = store.path.read_bytes()
    with patch("src.mcp_server.server._get_store", return_value=store):
        with pytest.raises(ToolError, match="Error:"):
            submit_decision(**args)
    assert store.path.read_bytes() == before


def test_actual_stdio_write_is_followed_by_readback(tmp_path):
    from scripts.demo_verified_audit import run
    output = tmp_path / "run.jsonl"
    result = run("CLM-001", output, transport_only=True)
    assert result["verification"] == "VERIFY SUCCESS"
    names = [step["tool"] for step in result["steps"]]
    index = names.index("submit_decision")
    assert names[index + 1] == "get_claim_status"
    assert json.loads(output.read_text())["disk_verified"]


def test_client_forwards_only_runtime_configuration(monkeypatch):
    from contextlib import asynccontextmanager
    import asyncio
    from src.mcp_server.client import connect
    captured = []
    monkeypatch.setenv("AIPR_STATE_PATH", "/tmp/example.json")
    monkeypatch.setenv("HF_HOME", "/tmp/cache")
    monkeypatch.setenv("SSL_CERT_FILE", "/tmp/ca.pem")
    monkeypatch.setenv("SECRET_EXAMPLE_KEY", "must-not-forward")

    @asynccontextmanager
    async def fake_client(parameters):
        captured.append(parameters)
        yield object()

    async def exercise():
        with patch("src.mcp_server.client.Client", fake_client):
            async with connect("python", ["-m", "src.mcp_server.server"]):
                pass

    asyncio.run(exercise())
    assert captured[0].env["AIPR_STATE_PATH"] == "/tmp/example.json"
    assert captured[0].env["HF_HOME"] == "/tmp/cache"
    assert captured[0].env["SSL_CERT_FILE"] == "/tmp/ca.pem"
    assert "SECRET_EXAMPLE_KEY" not in captured[0].env
