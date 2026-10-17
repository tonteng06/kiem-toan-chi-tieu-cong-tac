import pytest
from src.agent.agent import audit_claim_and_verify, call_llm

mock_db = {}

def mock_submit_decision(claim_id: str, decision: str, reason: str, evidence: list):
    mock_db[claim_id] = decision
    return {"status": "success", "claim_id": claim_id, "persisted_decision": decision}

def mock_get_claim_status(claim_id: str) -> str:
    return mock_db.get(claim_id, "PENDING")

def mock_get_claim(claim_id: str):
    return {"claim_id": claim_id, "amount": 1500000}

def mock_search_policy(query: str):
    return "DOC003@v1.0: Hotel limit is 2,000,000 VND/night."

def test_approved_and_verify_success():
    res = audit_claim_and_verify(
        claim_id="CLM001",
        query="Are the hotel expenses valid?",
        get_claim_fn=mock_get_claim,
        search_policy_fn=mock_search_policy,
        submit_decision_fn=mock_submit_decision,
        get_claim_status_fn=mock_get_claim_status
    )
    assert res["decision"] == "APPROVED"
    assert res["actual_status"] == "APPROVED"
    assert res["verify_result"] == "VERIFY SUCCESS"

def test_rejected_and_verify_success():
    res = audit_claim_and_verify(
        claim_id="CLM002",
        query="Entertainment expense exceeds the limit",
        get_claim_fn=mock_get_claim,
        search_policy_fn=mock_search_policy,
        submit_decision_fn=mock_submit_decision,
        get_claim_status_fn=mock_get_claim_status
    )
    assert res["decision"] == "REJECTED"
    assert res["verify_result"] == "VERIFY SUCCESS"

def test_need_more_info_skips_write():
    res = audit_claim_and_verify(
        claim_id="CLM003",
        query="Claim is missing the financial receipt",
        get_claim_fn=mock_get_claim,
        search_policy_fn=mock_search_policy,
        submit_decision_fn=mock_submit_decision,
        get_claim_status_fn=mock_get_claim_status
    )
    assert res["decision"] == "NEED_MORE_INFO"
    assert res["verify_result"] == "SKIPPED_NO_WRITE"
    assert "CLM003" not in mock_db

def test_no_answer_skips_write():
    res = audit_claim_and_verify(
        claim_id="CLM004",
        query="Policy not mentioned for this item",
        get_claim_fn=mock_get_claim,
        search_policy_fn=mock_search_policy,
        submit_decision_fn=mock_submit_decision,
        get_claim_status_fn=mock_get_claim_status
    )
    assert res["decision"] == "NO_ANSWER"
    assert res["verify_result"] == "SKIPPED_NO_WRITE"
    assert "CLM004" not in mock_db

def test_usage_format_matches_contract():
    reply = call_llm([{"role": "user", "content": "Check CLM001"}])
    assert "calls" in reply.usage
    assert "prompt_tokens" in reply.usage
    assert "completion_tokens" in reply.usage
    assert "max_prompt" in reply.usage