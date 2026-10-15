from __future__ import annotations

from typing import TypedDict

from evaluation.agent_eval_contract import (
    AgentEvalOutput,
    validate_agent_output,
)


class CaseMetrics(TypedDict):
    decision_correct: bool
    correct_refusal: bool | None
    evidence_coverage: float | None


def decision_correct(
    expected_decision: str,
    actual_decision: str,
) -> bool:
    """
    Return True when the Agent decision exactly matches
    the expected decision.
    """
    return actual_decision == expected_decision


def correct_refusal(
    expected_decision: str,
    actual_decision: str,
) -> bool | None:
    """
    Evaluate refusal only for cases whose expected
    decision is NO_ANSWER.

    None means this case is not a refusal test case.
    """
    if expected_decision != "NO_ANSWER":
        return None

    return actual_decision == "NO_ANSWER"


def evidence_coverage(
    expected_refs: list[str],
    actual_refs: list[str],
) -> float | None:
    """
    Measure how much expected policy evidence appears
    in the Agent evidence references.

    Duplicate references do not increase the score.

    None means there is no expected evidence to score.
    """
    expected = set(expected_refs)

    if not expected:
        return None

    actual = set(actual_refs)

    matched = expected & actual

    return len(matched) / len(expected)


def evaluate_case(
    expected_decision: str,
    expected_refs: list[str],
    output: object,
) -> CaseMetrics:
    """
    Validate one Agent output and compute Agent-level metrics.

    This function does not evaluate LLM faithfulness.
    """
    validated: AgentEvalOutput = validate_agent_output(output)

    return {
        "decision_correct": decision_correct(
            expected_decision,
            validated["decision"],
        ),
        "correct_refusal": correct_refusal(
            expected_decision,
            validated["decision"],
        ),
        "evidence_coverage": evidence_coverage(
            expected_refs,
            validated["evidence_refs"],
        ),
    }
