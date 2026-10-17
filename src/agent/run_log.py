"""Per-question run record (TV2, Day 6): what Member 3's JSONL logs and Member 1's evaluation need.

One JSON line per question: timestamp, question, decision, stop reason, the verified write, usage
(calls, prompt_tokens, completion_tokens, max_prompt) and every step with tool args and results.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))


def run_record(question: str, result: dict, question_id: str | None = None) -> dict:
    return {
        "timestamp": datetime.now(VN_TZ).isoformat(timespec="seconds"),
        "question_id": question_id,
        "question": question,
        "decision": result["decision"],
        "answer": result["answer"],
        "evidence_refs": result["evidence_refs"],
        "stopped_reason": result["stopped_reason"],
        "write": result.get("write"),
        "usage": result["usage"],
        "steps": result["trace"],
    }


def append_run_log(path: Path | str, question: str, result: dict, question_id: str | None = None) -> dict:
    record = run_record(question, result, question_id)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record