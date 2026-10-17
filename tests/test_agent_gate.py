"""End-to-end agent scenarios on the real registry, rules and state store (scripted model).

The model is scripted so the tests are deterministic; everything else (business rules, evidence
gate, submit_decision, read-back verify, state file) is the real code.
"""
import json
import shutil
from pathlib import Path

import pytest

from evaluation.agent_eval_contract import validate_agent_output
from src.agent.agent import ModelReply, RegistryToolbox, run_agent
from src.agent.run_log import append_run_log, run_record
from src.agent.state_store import StateStore
from src.agent.tool_registry import build_registry
from src.models.document import Chunk, SearchResult

SAMPLE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"


class FakeRetriever:
    """Returns one chunk per policy reference it was given, e.g. ["DOC003@v1.0"]."""

    def __init__(self, refs=()):
        self.refs = list(refs)

    def retrieve(self, query, mode="hybrid", top_k=3):
        out = []
        for ref in self.refs[:top_k]:
            doc, version = ref.split("@v")
            out.append(SearchResult(Chunk(f"{doc}-c0", doc, f"Title {doc}", version, "2026-01-01", "Finance",
                                          f"text of {doc}"), 0.9, mode))
        return out


class ScriptedLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def __call__(self, messages, schemas):
        return ModelReply(self.replies.pop(0), prompt_tokens=100, completion_tokens=20)


def tool(name, **args):
    return json.dumps({"action": "tool", "name": name, "args": args})


def final(decision, refs=()):
    return json.dumps({"action": "final", "decision": decision, "answer": f"{decision} because of the rules.",
                       "evidence_refs": list(refs)})


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "claims.json"
    shutil.copy(SAMPLE, path)
    return StateStore(path)


def run(store, replies, refs=(), toolbox=None):
    tb = toolbox or RegistryToolbox(build_registry(store, FakeRetriever(refs)))
    return run_agent("Audit the claim", ScriptedLLM(replies), tb)


def status(store, claim_id):
    return store.get(claim_id).status.value


def audit(claim_id, decision, search="hotel policy"):
    """The model's normal path: read, calculate, search, write, then answer."""
    return [
        tool("get_claim", claim_id=claim_id), tool("calculate_claim", claim_id=claim_id),
        tool("search_policy", query=search),
        tool("submit_decision", claim_id=claim_id, decision=decision, reason=f"{decision} per policy"),
        final(decision),
    ]


@pytest.mark.parametrize("claim_id, decision, refs", [
    ("CLM-001", "APPROVED", ["DOC003@v1.0"]),      # no issue: needs some policy text, any
    ("CLM-002", "ESCALATED", ["DOC003@v1.0"]),     # hotel over the Da Nang limit
    ("CLM-006", "REJECTED", ["DOC004@v1.0"]),      # alcohol is not reimbursable
    ("CLM-003", "NEED_MORE_INFO", ["DOC006@v1.0"]),  # missing receipt
])
def test_decision_is_written_and_verified(store, claim_id, decision, refs):
    out = run(store, audit(claim_id, decision), refs)
    assert out["decision"] == decision and out["stopped_reason"] == "final"
    assert out["write"] == {"claim_id": claim_id, "decision": decision, "verify": "VERIFY SUCCESS"}
    assert status(store, claim_id) == decision  # the state file really changed
    submit = next(t for t in out["trace"] if t.get("tool") == "submit_decision")
    assert submit["verify"]["expected_status"] == decision == submit["verify"]["actual_status"]
    validate_agent_output(out)


def test_no_policy_evidence_blocks_the_write_and_ends_in_no_answer(store):
    replies = audit("CLM-002", "ESCALATED")[:-1] + [final("NO_ANSWER")]
    out = run(store, replies, refs=[])  # the corpus returns nothing
    blocked = next(t for t in out["trace"] if t.get("tool") == "submit_decision")
    assert blocked["blocked_by_gate"] and "no policy evidence" in blocked["observation"]
    assert out["decision"] == "NO_ANSWER" and out["write"] is None
    assert status(store, "CLM-002") == "SUBMITTED"
    validate_agent_output(out)


def test_wrong_policy_does_not_count_as_evidence(store):
    out = run(store, audit("CLM-002", "ESCALATED")[:-1] + [final("NO_ANSWER")], refs=["DOC001@v1.0"])
    assert next(t for t in out["trace"] if t.get("tool") == "submit_decision")["blocked_by_gate"]
    assert status(store, "CLM-002") == "SUBMITTED"


def test_cannot_approve_a_claim_the_rules_flag(store):
    out = run(store, audit("CLM-002", "APPROVED")[:-1] + [final("NO_ANSWER")], refs=["DOC003@v1.0"])
    blocked = next(t for t in out["trace"] if t.get("tool") == "submit_decision")
    assert "conflicts with the business rules" in blocked["observation"]
    assert status(store, "CLM-002") == "SUBMITTED"


def test_write_before_calculate_is_blocked(store):
    replies = [tool("submit_decision", claim_id="CLM-001", decision="APPROVED", reason="x"), final("NO_ANSWER")]
    out = run(store, replies, refs=["DOC003@v1.0"])
    assert "run calculate_claim" in out["trace"][0]["observation"]
    assert status(store, "CLM-001") == "SUBMITTED"


def test_no_answer_is_never_persisted(store):
    replies = [tool("calculate_claim", claim_id="CLM-002"),
               tool("submit_decision", claim_id="CLM-002", decision="NO_ANSWER", reason="x"), final("NO_ANSWER")]
    out = run(store, replies, refs=["DOC003@v1.0"])
    assert "never written" in out["trace"][1]["observation"]
    assert status(store, "CLM-002") == "SUBMITTED" and out["write"] is None


def test_final_decision_without_a_verified_write_is_rejected(store):
    replies = [tool("calculate_claim", claim_id="CLM-001"), final("APPROVED"), final("NO_ANSWER")]
    out = run(store, replies)
    assert out["trace"][1]["observation"].startswith("Error: final APPROVED rejected")
    assert out["decision"] == "NO_ANSWER" and status(store, "CLM-001") == "SUBMITTED"


def test_final_must_repeat_the_decision_that_was_written(store):
    replies = audit("CLM-002", "ESCALATED")[:-1] + [final("REJECTED"), final("ESCALATED")]
    out = run(store, replies, refs=["DOC003@v1.0"])
    assert out["trace"][-2]["observation"].startswith("Error: final REJECTED rejected")
    assert out["decision"] == "ESCALATED"


def test_final_claim_cannot_be_decided_again(store):
    out = run(store, audit("CLM-005", "APPROVED")[:-1] + [final("NO_ANSWER")], refs=["DOC003@v1.0"])
    submit = next(t for t in out["trace"] if t.get("tool") == "submit_decision")
    assert submit["is_error"] and "Invalid transition" in submit["observation"]  # already APPROVED
    assert out["write"] is None and out["decision"] == "NO_ANSWER"


class LyingToolbox(RegistryToolbox):
    """Simulates a broken write: the read-back says the status did not change."""

    def call(self, name, args=None):
        if name == "get_claim_status":
            return json.dumps({"claim_id": args["claim_id"], "status": "SUBMITTED"})
        return super().call(name, args)


def test_verify_failed_is_reported_and_ends_the_run(store):
    tb = LyingToolbox(build_registry(store, FakeRetriever(["DOC003@v1.0"])))
    out = run(store, audit("CLM-002", "ESCALATED"), toolbox=tb)
    assert out["stopped_reason"] == "verify_failed" and out["decision"] == "NO_ANSWER"
    assert out["write"]["verify"] == "VERIFY FAILED"
    validate_agent_output(out)


def test_run_record_has_what_the_logs_need(store, tmp_path):
    out = run(store, audit("CLM-002", "ESCALATED"), ["DOC003@v1.0"])
    rec = run_record("Audit CLM-002", out, "Q1")
    for key in ("timestamp", "question", "decision", "usage", "steps", "write", "stopped_reason"):
        assert key in rec
    assert set(rec["usage"]) == {"calls", "prompt_tokens", "completion_tokens", "max_prompt"}
    assert rec["usage"]["calls"] == 5 and rec["usage"]["prompt_tokens"] == 500
    log = tmp_path / "logs" / "run.jsonl"
    append_run_log(log, "Audit CLM-002", out, "Q1")
    append_run_log(log, "Audit CLM-002", out, "Q2")
    assert [json.loads(line)["question_id"] for line in log.read_text(encoding="utf-8").splitlines()] == ["Q1", "Q2"]


def test_demo_script_runs_claims_on_a_copy_and_logs(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("demo_agent", Path(__file__).parents[1] / "scripts" / "demo_agent.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    tracked_before = SAMPLE.read_bytes()
    log = tmp_path / "logs" / "agent_run.jsonl"
    results = demo.run_claims(["CLM-002"], ScriptedLLM(audit("CLM-002", "ESCALATED")), FakeRetriever(["DOC003@v1.0"]), log)
    assert results[0]["write"]["verify"] == "VERIFY SUCCESS"
    assert json.loads(log.read_text(encoding="utf-8"))["question_id"] == "CLM-002"
    assert SAMPLE.read_bytes() == tracked_before  # the tracked sample data was not touched