import pytest

from evaluation.agent_metrics import (
    correct_refusal,
    decision_correct,
    evidence_coverage,
    evaluate_case,
)


def make_output(
    decision: str,
    evidence_refs: list[str],
) -> dict:
    return {
        "answer": "Example answer",
        "decision": decision,
        "evidence_refs": evidence_refs,
        "usage": {
            "calls": 1,
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "max_prompt": 100,
        },
    }


def test_decision_correct():
    assert decision_correct("ESCALATED", "ESCALATED")
    assert not decision_correct("ESCALATED", "APPROVED")


def test_correct_refusal_for_no_answer_case():
    assert correct_refusal(
        "NO_ANSWER",
        "NO_ANSWER",
    ) is True

    assert correct_refusal(
        "NO_ANSWER",
        "APPROVED",
    ) is False


def test_correct_refusal_not_applicable():
    assert correct_refusal(
        "ESCALATED",
        "ESCALATED",
    ) is None


def test_full_evidence_coverage():
    score = evidence_coverage(
        [
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
        [
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
    )

    assert score == 1.0


def test_partial_evidence_coverage():
    score = evidence_coverage(
        [
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
        [
            "DOC003@v1.0",
        ],
    )

    assert score == 0.5


def test_extra_evidence_does_not_hurt_coverage():
    score = evidence_coverage(
        ["DOC003@v1.0"],
        [
            "DOC003@v1.0",
            "DOC004@v1.0",
        ],
    )

    assert score == 1.0


def test_duplicate_evidence_does_not_increase_score():
    score = evidence_coverage(
        [
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
        [
            "DOC003@v1.0",
            "DOC003@v1.0",
        ],
    )

    assert score == 0.5


def test_no_expected_evidence_returns_none():
    assert evidence_coverage([], []) is None


def test_evaluate_case_correct_decision_partial_evidence():
    result = evaluate_case(
        expected_decision="ESCALATED",
        expected_refs=[
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
        output=make_output(
            "ESCALATED",
            ["DOC003@v1.0"],
        ),
    )

    assert result == {
        "decision_correct": True,
        "correct_refusal": None,
        "evidence_coverage": 0.5,
    }


def test_evaluate_case_correct_refusal():
    result = evaluate_case(
        expected_decision="NO_ANSWER",
        expected_refs=[],
        output=make_output(
            "NO_ANSWER",
            [],
        ),
    )

    assert result == {
        "decision_correct": True,
        "correct_refusal": True,
        "evidence_coverage": None,
    }


def test_evaluate_case_wrong_refusal():
    result = evaluate_case(
        expected_decision="NO_ANSWER",
        expected_refs=[],
        output=make_output(
            "APPROVED",
            [],
        ),
    )

    assert result["decision_correct"] is False
    assert result["correct_refusal"] is False


def test_invalid_agent_output_is_rejected():
    output = make_output(
        "ESCALATED",
        ["DOC003@v1.0"],
    )

    del output["usage"]

    with pytest.raises(
        ValueError,
        match="Missing Agent output",
    ):
        evaluate_case(
            expected_decision="ESCALATED",
            expected_refs=["DOC003@v1.0"],
            output=output,
        )
