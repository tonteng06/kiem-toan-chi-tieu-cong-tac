import pytest

from evaluation.agent_eval_summary import summarize_evaluation


def make_output(
    decision: str,
    refs: list[str],
    prompt_tokens: int,
    completion_tokens: int,
    calls: int = 1,
    max_prompt: int | None = None,
) -> dict:
    if max_prompt is None:
        max_prompt = prompt_tokens

    return {
        "answer": "Test answer",
        "decision": decision,
        "evidence_refs": refs,
        "usage": {
            "calls": calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "max_prompt": max_prompt,
        },
    }


def test_summary_all_correct():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "ESCALATED",
            "expected_refs": [
                "DOC003@v1.0",
                "DOC007@v1.0",
            ],
            "output": make_output(
                "ESCALATED",
                [
                    "DOC003@v1.0",
                    "DOC007@v1.0",
                ],
                400,
                100,
            ),
        },
        {
            "case_id": "B",
            "expected_decision": "NO_ANSWER",
            "expected_refs": [],
            "output": make_output(
                "NO_ANSWER",
                [],
                300,
                50,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    assert summary["total_cases"] == 2
    assert summary["correct_decisions"] == 2
    assert summary["decision_accuracy"] == 1.0

    assert summary["refusal_cases"] == 1
    assert summary["correct_refusals"] == 1
    assert summary["correct_refusal_rate"] == 1.0

    assert summary["evidence_cases"] == 1
    assert summary["average_evidence_coverage"] == 1.0

    assert summary["total_llm_calls"] == 2
    assert summary["total_prompt_tokens"] == 700
    assert summary["total_completion_tokens"] == 150
    assert summary["total_tokens"] == 850
    assert summary["average_tokens_per_case"] == 425.0
    assert summary["max_prompt_tokens"] == 400


def test_summary_with_wrong_decision_and_refusal():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "ESCALATED",
            "expected_refs": ["DOC003@v1.0"],
            "output": make_output(
                "APPROVED",
                ["DOC003@v1.0"],
                100,
                20,
            ),
        },
        {
            "case_id": "B",
            "expected_decision": "NO_ANSWER",
            "expected_refs": [],
            "output": make_output(
                "APPROVED",
                [],
                100,
                20,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    assert summary["correct_decisions"] == 0
    assert summary["decision_accuracy"] == 0.0

    assert summary["refusal_cases"] == 1
    assert summary["correct_refusals"] == 0
    assert summary["correct_refusal_rate"] == 0.0


def test_average_evidence_coverage():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "ESCALATED",
            "expected_refs": [
                "DOC003@v1.0",
                "DOC007@v1.0",
            ],
            "output": make_output(
                "ESCALATED",
                ["DOC003@v1.0"],
                100,
                20,
            ),
        },
        {
            "case_id": "B",
            "expected_decision": "REJECTED",
            "expected_refs": [
                "DOC004@v1.0",
            ],
            "output": make_output(
                "REJECTED",
                ["DOC004@v1.0"],
                100,
                20,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    # Case A coverage = 0.5
    # Case B coverage = 1.0
    # Average = 0.75
    assert summary["average_evidence_coverage"] == 0.75


def test_no_refusal_cases_returns_none():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "APPROVED",
            "expected_refs": [],
            "output": make_output(
                "APPROVED",
                [],
                100,
                20,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    assert summary["refusal_cases"] == 0
    assert summary["correct_refusal_rate"] is None


def test_no_evidence_cases_returns_none():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "NO_ANSWER",
            "expected_refs": [],
            "output": make_output(
                "NO_ANSWER",
                [],
                100,
                20,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    assert summary["evidence_cases"] == 0
    assert summary["average_evidence_coverage"] is None


def test_multiple_llm_calls_are_summed():
    cases = [
        {
            "case_id": "A",
            "expected_decision": "APPROVED",
            "expected_refs": [],
            "output": make_output(
                "APPROVED",
                [],
                500,
                80,
                calls=3,
                max_prompt=250,
            ),
        },
    ]

    summary = summarize_evaluation(cases)

    assert summary["total_llm_calls"] == 3
    assert summary["total_prompt_tokens"] == 500
    assert summary["total_completion_tokens"] == 80
    assert summary["total_tokens"] == 580
    assert summary["average_tokens_per_case"] == 580.0
    assert summary["max_prompt_tokens"] == 250


def test_empty_case_list_is_rejected():
    with pytest.raises(
        ValueError,
        match="At least one evaluation case",
    ):
        summarize_evaluation([])
