from __future__ import annotations

from typing import TypedDict


VALID_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "ESCALATED",
    "NEED_MORE_INFO",
    "NO_ANSWER",
}


class UsageStats(TypedDict):
    calls: int
    prompt_tokens: int
    completion_tokens: int
    max_prompt: int


class AgentEvalOutput(TypedDict):
    answer: str
    decision: str
    evidence_refs: list[str]
    usage: UsageStats


def validate_agent_output(data: object) -> AgentEvalOutput:
    """
    Validate the minimum Agent output required by Member 1 evaluation.

    This validates only the evaluation interface.
    It does not judge whether the Agent answer is correct.
    """
    if not isinstance(data, dict):
        raise ValueError("Agent output must be a dictionary")

    required_fields = {
        "answer",
        "decision",
        "evidence_refs",
        "usage",
    }

    missing = required_fields - set(data)

    if missing:
        raise ValueError(
            f"Missing Agent output field(s): {sorted(missing)}"
        )

    answer = data["answer"]
    decision = data["decision"]
    evidence_refs = data["evidence_refs"]
    usage = data["usage"]

    if not isinstance(answer, str):
        raise ValueError("answer must be a string")

    if (
        not isinstance(decision, str)
        or decision not in VALID_DECISIONS
    ):
        raise ValueError(
            f"decision must be one of {sorted(VALID_DECISIONS)}"
        )

    if not isinstance(evidence_refs, list):
        raise ValueError("evidence_refs must be a list")

    for ref in evidence_refs:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(
                "every evidence reference must be a non-empty string"
            )

    if not isinstance(usage, dict):
        raise ValueError("usage must be a dictionary")

    required_usage = {
        "calls",
        "prompt_tokens",
        "completion_tokens",
        "max_prompt",
    }

    missing_usage = required_usage - set(usage)

    if missing_usage:
        raise ValueError(
            f"Missing usage field(s): {sorted(missing_usage)}"
        )

    for key in required_usage:
        value = usage[key]

        if type(value) is not int or value < 0:
            raise ValueError(
                f"usage.{key} must be a non-negative integer"
            )

    return data
