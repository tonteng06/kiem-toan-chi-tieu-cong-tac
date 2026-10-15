import pytest

from evaluation.agent_eval_contract import validate_agent_output


def valid_output() -> dict:
    return {
        "answer": "The claim should be escalated.",
        "decision": "ESCALATED",
        "evidence_refs": [
            "DOC003@v1.0",
            "DOC007@v1.0",
        ],
        "usage": {
            "calls": 1,
            "prompt_tokens": 420,
            "completion_tokens": 85,
            "max_prompt": 420,
        },
    }


def test_valid_output_is_accepted():
    data = valid_output()

    result = validate_agent_output(data)

    assert result == data


def test_no_answer_is_valid_decision():
    data = valid_output()
    data["decision"] = "NO_ANSWER"
    data["answer"] = "I cannot answer from the available policy evidence."
    data["evidence_refs"] = []

    result = validate_agent_output(data)

    assert result["decision"] == "NO_ANSWER"


def test_missing_required_field_is_rejected():
    data = valid_output()
    del data["decision"]

    with pytest.raises(ValueError, match="Missing Agent output"):
        validate_agent_output(data)


def test_invalid_decision_is_rejected():
    data = valid_output()
    data["decision"] = "MAYBE"

    with pytest.raises(ValueError, match="decision must be one of"):
        validate_agent_output(data)


def test_evidence_refs_must_be_a_list():
    data = valid_output()
    data["evidence_refs"] = "DOC003@v1.0"

    with pytest.raises(ValueError, match="evidence_refs must be a list"):
        validate_agent_output(data)


def test_empty_evidence_reference_is_rejected():
    data = valid_output()
    data["evidence_refs"] = [""]

    with pytest.raises(
        ValueError,
        match="every evidence reference",
    ):
        validate_agent_output(data)


def test_missing_usage_field_is_rejected():
    data = valid_output()
    del data["usage"]["completion_tokens"]

    with pytest.raises(ValueError, match="Missing usage field"):
        validate_agent_output(data)


@pytest.mark.parametrize(
    "key,value",
    [
        ("calls", -1),
        ("prompt_tokens", -1),
        ("completion_tokens", -1),
        ("max_prompt", -1),
        ("calls", True),
        ("prompt_tokens", 3.5),
    ],
)
def test_usage_values_must_be_non_negative_integers(
    key,
    value,
):
    data = valid_output()
    data["usage"][key] = value

    with pytest.raises(
        ValueError,
        match=f"usage.{key}",
    ):
        validate_agent_output(data)
