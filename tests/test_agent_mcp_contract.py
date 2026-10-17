"""Agent/MCP handler contract regressions. Scripted LLM/retrieval, no stdio claim.

The real handler, Agent gate, rules and file store are exercised together.
These tests are not retrieval or real LLM performance measurements.
"""
import json
import shutil
from pathlib import Path

import pytest

from src.agent.agent import ModelReply, run_agent
from src.agent.state_store import StateStore
from src.mcp_server import server as endpoint
from src.mcp_server.agent_bridge import required_policy_refs
from src.agent.business_rules import calculate_claim

SAMPLE = Path(__file__).parents[1] / "data/claims/claims.json"


def test_mcp_runner_blocks_unseen_write_citations_without_calling_write():
    from scripts.demo_agent_mcp import GroundedMcpToolbox

    class Wire:
        calls = []
        def call(self, name, args):
            self.calls.append(name)
            return json.dumps({"results": [{"evidence_ref": "DOC003@v1.0", "content": "Hotel limit"}]})

    wire = Wire()
    box = GroundedMcpToolbox(wire)
    assert box.call("submit_decision", {"evidence_refs": ["DOC003@v1.0"]}).startswith("Error:")
    assert wire.calls == []
    box.call("search_policy", {"query": "hotel limit"})
    assert box.call("submit_decision", {"evidence_refs": ["DOC003@v1.0", "DOC006@v1.0"]}).startswith("Error:")
    assert wire.calls == ["search_policy"]
    box.call("submit_decision", {"evidence_refs": ["DOC003@v1.0"]})
    assert wire.calls[-1] == "submit_decision"


@pytest.mark.parametrize("claim_id,decision", [
    ("CLM-001", "APPROVED"), ("CLM-002", "ESCALATED"),
    ("CLM-003", "NEED_MORE_INFO"), ("CLM-006", "REJECTED"),
])
def test_agent_writes_real_mcp_contract_and_immediately_reads_back(tmp_path, monkeypatch, claim_id, decision):
    path = tmp_path / "claims.json"
    shutil.copyfile(SAMPLE, path)
    store = StateStore(path)
    monkeypatch.setattr(endpoint, "_get_store", lambda: store)
    refs = sorted(required_policy_refs(store.get(claim_id), calculate_claim(store.get(claim_id))))
    calls = []

    class HandlerToolbox:
        def schemas(self):
            # Actual server definitions, not a second hand-maintained schema list.
            return [{"name": t.name, "input_schema": t.parameters}
                    for t in endpoint.server._tool_manager.list_tools()]

        def call(self, name, args=None):
            calls.append(name)
            if name == "calculate_claim":
                payload = calculate_claim(store.get(args["claim_id"]))
            elif name == "search_policy":
                payload = {"results": [{"evidence_ref": ref, "content": "Scripted policy fixture"} for ref in refs]}
            elif name == "submit_decision":
                payload = endpoint.submit_decision(**args)
            elif name == "get_claim_status":
                current = store.get(args["claim_id"])
                payload = {"claim_id": current.claim_id, "status": current.status.value}
            return json.dumps(payload)

    replies = iter([
        {"action": "tool", "name": "calculate_claim", "args": {"claim_id": claim_id}},
        {"action": "tool", "name": "search_policy", "args": {"query": "policies"}},
        {"action": "tool", "name": "submit_decision", "args": {
            "claim_id": claim_id, "decision": decision, "reason": "Regression: checked policy refs",
            "evidence_refs": refs}},
        {"action": "final", "decision": decision, "answer": "Verified", "evidence_refs": refs},
    ])
    output = run_agent("Audit " + claim_id, lambda m, s: ModelReply(json.dumps(next(replies))), HandlerToolbox())
    assert output["decision"] == decision
    assert output["write"]["verify"] == "VERIFY SUCCESS"
    assert calls[-2:] == ["submit_decision", "get_claim_status"]
    assert StateStore(path).get(claim_id).status.value == decision
