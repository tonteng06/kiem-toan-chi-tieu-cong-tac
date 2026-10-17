from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTSET_PATH = ROOT / "tests" / "testset.jsonl"
LOG_PATH = ROOT / "logs" / "agent_run_04.jsonl"
OUT_PATH = ROOT / "evaluation" / "no_answer_summary.json"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    testset = load_jsonl(TESTSET_PATH)
    records = load_jsonl(LOG_PATH)

    expected_ids = [
        row["id"]
        for row in testset
        if row.get("no_answer")
    ]

    by_id: dict[str, dict] = {}

    for record in records:
        qid = record["question_id"]

        if qid in by_id:
            raise ValueError(f"Duplicate refusal record: {qid}")

        by_id[qid] = record

    details = []
    correct = 0

    total_calls = 0
    prompt_tokens = 0
    completion_tokens = 0
    max_prompt = 0

    for qid in expected_ids:
        if qid not in by_id:
            raise ValueError(f"Missing refusal case: {qid}")

        record = by_id[qid]
        usage = record["usage"]

        valid = (
            record["decision"] == "NO_ANSWER"
            and record["stopped_reason"] == "final"
            and usage["calls"] > 0
        )

        correct += int(valid)

        total_calls += usage["calls"]
        prompt_tokens += usage["prompt_tokens"]
        completion_tokens += usage["completion_tokens"]
        max_prompt = max(max_prompt, usage["max_prompt"])

        details.append({
            "question_id": qid,
            "decision": record["decision"],
            "stopped_reason": record["stopped_reason"],
            "llm_calls": usage["calls"],
            "evidence_refs": record["evidence_refs"],
            "valid_refusal": valid,
        })

    total = len(expected_ids)

    result = {
        "source_log": "logs/agent_run_04.jsonl",
        "total_cases": total,
        "correct_refusals": correct,
        "correct_refusal_rate": correct / total if total else None,
        "total_llm_calls": total_calls,
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "max_prompt_tokens": max_prompt,
        "cases": details,
    }

    OUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("===== REAL CORRECT REFUSAL =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
