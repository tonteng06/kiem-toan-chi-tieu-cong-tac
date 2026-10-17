from __future__ import annotations

import json
from pathlib import Path

from evaluation.agent_eval_summary import summarize_evaluation
from src.agent.business_rules import calculate_claim
from src.models.claim import Claim

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "agent_run_01.jsonl"
CLAIMS_PATH = ROOT / "data" / "claims" / "claims.json"
OUT_PATH = ROOT / "evaluation" / "real_agent_summary.json"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    raw_claims = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    claims = {
        item["claim_id"]: Claim.from_dict(item)
        for item in raw_claims
    }

    records = load_jsonl(LOG_PATH)

    seen: set[str] = set()
    cases = []
    verified_writes = 0

    for record in records:
        claim_id = record["question_id"]

        if claim_id in seen:
            raise ValueError(f"Duplicate claim in evaluation log: {claim_id}")
        seen.add(claim_id)

        if record.get("stopped_reason") != "final":
            raise ValueError(
                f"{claim_id} is not a successful final Agent output"
            )

        if record.get("usage", {}).get("calls", 0) <= 0:
            raise ValueError(
                f"{claim_id} has no real LLM calls"
            )

        calculation = calculate_claim(claims[claim_id])

        issues = (
            calculation["violations"]
            + calculation["missing_data"]
        )

        expected_refs = sorted({
            issue["evidence"]
            for issue in issues
        })

        output = {
            "answer": record["answer"],
            "decision": record["decision"],
            "evidence_refs": record["evidence_refs"],
            "usage": record["usage"],
        }

        cases.append({
            "case_id": claim_id,
            "expected_decision": calculation["recommended_status"],
            "expected_refs": expected_refs,
            "output": output,
        })

        write = record.get("write") or {}
        if write.get("verify") == "VERIFY SUCCESS":
            verified_writes += 1

    summary = summarize_evaluation(cases)

    result = {
        "source_log": "logs/agent_run_01.jsonl",
        **summary,
        "verified_writes": verified_writes,
    }

    OUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("===== REAL CLAIM AGENT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
