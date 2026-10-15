from __future__ import annotations

from typing import TypedDict

from evaluation.agent_eval_contract import validate_agent_output
from evaluation.agent_metrics import evaluate_case


class EvaluationCase(TypedDict):
    case_id: str
    expected_decision: str
    expected_refs: list[str]
    output: object


class EvaluationSummary(TypedDict):
    total_cases: int
    correct_decisions: int
    decision_accuracy: float
    refusal_cases: int
    correct_refusals: int
    correct_refusal_rate: float | None
    evidence_cases: int
    average_evidence_coverage: float | None
    total_llm_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    average_tokens_per_case: float
    max_prompt_tokens: int


def summarize_evaluation(
    cases: list[EvaluationCase],
) -> EvaluationSummary:
    """
    Aggregate Agent-level evaluation metrics across many cases.

    This function expects real Agent outputs when used for final
    project evaluation. Synthetic cases may be used only in unit tests.
    """
    if not cases:
        raise ValueError("At least one evaluation case is required")

    correct_decisions = 0

    refusal_cases = 0
    correct_refusals = 0

    evidence_scores: list[float] = []

    total_llm_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    max_prompt_tokens = 0

    for case in cases:
        output = validate_agent_output(case["output"])

        metrics = evaluate_case(
            expected_decision=case["expected_decision"],
            expected_refs=case["expected_refs"],
            output=output,
        )

        if metrics["decision_correct"]:
            correct_decisions += 1

        refusal_result = metrics["correct_refusal"]

        if refusal_result is not None:
            refusal_cases += 1

            if refusal_result:
                correct_refusals += 1

        coverage = metrics["evidence_coverage"]

        if coverage is not None:
            evidence_scores.append(coverage)

        usage = output["usage"]

        total_llm_calls += usage["calls"]
        total_prompt_tokens += usage["prompt_tokens"]
        total_completion_tokens += usage["completion_tokens"]

        max_prompt_tokens = max(
            max_prompt_tokens,
            usage["max_prompt"],
        )

    total_cases = len(cases)

    total_tokens = (
        total_prompt_tokens
        + total_completion_tokens
    )

    decision_accuracy = (
        correct_decisions / total_cases
    )

    correct_refusal_rate = (
        correct_refusals / refusal_cases
        if refusal_cases
        else None
    )

    average_evidence_coverage = (
        sum(evidence_scores) / len(evidence_scores)
        if evidence_scores
        else None
    )

    average_tokens_per_case = (
        total_tokens / total_cases
    )

    return {
        "total_cases": total_cases,
        "correct_decisions": correct_decisions,
        "decision_accuracy": decision_accuracy,
        "refusal_cases": refusal_cases,
        "correct_refusals": correct_refusals,
        "correct_refusal_rate": correct_refusal_rate,
        "evidence_cases": len(evidence_scores),
        "average_evidence_coverage": (
            average_evidence_coverage
        ),
        "total_llm_calls": total_llm_calls,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": (
            total_completion_tokens
        ),
        "total_tokens": total_tokens,
        "average_tokens_per_case": (
            average_tokens_per_case
        ),
        "max_prompt_tokens": max_prompt_tokens,
    }
