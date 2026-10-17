"""Real stdio write/read-back demo on an isolated copy of sample claims.

Default: real retrieval + deterministic business reasoning (no LLM).
--transport-only skips retrieval and is integration evidence, never final Agent evaluation.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.state_store import DEFAULT_PATH
from src.mcp_server.adapters import McpToolbox
from src.mcp_server.agent_bridge import preview_audit, required_policy_refs
from src.models.claim import Claim


def observe(box, name, args):
    raw = box.call(name, args)
    if raw.startswith("Error:"):
        raise RuntimeError(raw)
    return json.loads(raw)


def run(claim_id: str, output: Path, *, transport_only: bool = False) -> dict:
    original = hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest()
    question = f"Audit travel expense claim {claim_id}, checking applicable policies."
    with tempfile.TemporaryDirectory(prefix="aipr-state-") as folder:
        state = Path(folder) / "claims.json"
        shutil.copyfile(DEFAULT_PATH, state)
        # Configure only the child server; never change the caller's environment.
        bootstrap = (
            "import os; os.environ['AIPR_STATE_PATH']=" + repr(str(state)) + "; "
            "from src.mcp_server.server import main; main()"
        )
        with McpToolbox(args=["-c", bootstrap], timeout=300) as box:
            before = observe(box, "get_claim_status", {"claim_id": claim_id})
            raw_claim = observe(box, "get_claim", {"claim_id": claim_id})
            claim = Claim.from_dict(raw_claim)
            calculation = observe(box, "calculate_claim", {"claim_id": claim_id})
            if transport_only:
                # Server checks policy versions/coverage. This mode tests transport and persistence only.
                decision = calculation["recommended_status"]
                reason = calculation["summary"]
                refs = sorted(required_policy_refs(claim, calculation))
            else:
                async def search(query, mode, top_k):
                    return observe(box, "search_policy", {"query": query, "mode": mode, "top_k": top_k})
                preview = asyncio.run(preview_audit(claim, question, search, calculation_result=calculation))
                decision, reason = preview["decision"], preview["reason"]
                refs = sorted({citation["evidence_ref"] for citation in preview["citations"]})
                if decision == "NO_ANSWER":
                    raise RuntimeError("Insufficient retrieved evidence; no write: " + reason)
            written = observe(box, "submit_decision", {
                "claim_id": claim_id, "decision": decision, "reason": reason, "evidence_refs": refs,
            })
            # The next call after write is the mandatory read-back, not a cached object.
            actual = observe(box, "get_claim_status", {"claim_id": claim_id})
            disk = next(c for c in json.loads(state.read_text()) if c["claim_id"] == claim_id)
            verified = (actual["claim_id"] == written["claim_id"] == claim_id
                        and actual["status"] == written["status"] == decision == disk["status"]
                        and actual["decision_reason"] == reason.strip()
                        and actual["updated_at"] == written["updated_at"] == disk["updated_at"]
                        and before["status"] != actual["status"])
            if not verified:
                raise RuntimeError("VERIFY FAILED")
            history = box.history
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_kind": "transport_integration" if transport_only else "retrieval_deterministic_integration",
            "final_agent_evaluation": False, "llm_used": False,
            "question": question, "claim_id": claim_id, "decision": decision,
            "steps": history, "usage": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "max_prompt": 0},
            "verification": "VERIFY SUCCESS", "before": before, "after": actual,
            "disk_verified": True, "isolated_state": True,
        }
    if hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest() != original:
        raise RuntimeError("Tracked claims changed unexpectedly")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{claim_id}: {decision}; VERIFY SUCCESS; {output}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", default="CLM-001")
    parser.add_argument("--output", type=Path, default=ROOT / "logs/demo.jsonl")
    parser.add_argument("--three", action="store_true", help="Generate run_01, run_02, run_03 in output's directory")
    parser.add_argument("--transport-only", action="store_true")
    args = parser.parse_args()
    if args.three:
        for index, claim_id in enumerate(("CLM-001", "CLM-002", "CLM-003"), 1):
            run(claim_id, args.output.parent / f"run_{index:02d}.jsonl", transport_only=args.transport_only)
    else:
        run(args.claim_id, args.output, transport_only=args.transport_only)


if __name__ == "__main__":
    main()
