import json
from pathlib import Path

import pytest

from src.agent.business_rules import calculate_claim
from src.models.claim import Claim

CLAIMS_FILE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"

EXPECTED = {
    "CLM-001": "APPROVED",
    "CLM-002": "ESCALATED",
    "CLM-003": "NEED_MORE_INFO",
    "CLM-004": "ESCALATED",
    "CLM-005": "APPROVED",  # within limits; the state store blocks re-deciding it
    "CLM-006": "REJECTED",
    "CLM-007": "ESCALATED",
}


def load(claim_id: str) -> Claim:
    raw = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))
    return next(Claim.from_dict(d) for d in raw if d["claim_id"] == claim_id)


@pytest.mark.parametrize("claim_id, expected", EXPECTED.items())
def test_recommended_status_matches_policy(claim_id, expected):
    assert calculate_claim(load(claim_id))["recommended_status"] == expected


def test_totals():
    result = calculate_claim(load("CLM-001"))
    assert result["total"] == 4_050_000
    assert result["totals"] == {"hotel": 2_700_000, "meal": 900_000, "transport": 450_000}


def test_issue_codes_and_evidence():
    codes = lambda cid, key: {i["code"] for i in calculate_claim(load(cid))[key]}
    assert codes("CLM-002", "violations") == {"HOTEL_OVER_LIMIT"}
    assert codes("CLM-003", "missing_data") == {"MISSING_RECEIPT"}
    assert codes("CLM-004", "missing_data") == {"NO_HOTEL_POLICY"}  # must not reuse domestic limits
    assert codes("CLM-006", "violations") == {"NOT_REIMBURSABLE"}
    assert codes("CLM-007", "violations") == {"LATE_SUBMISSION"}
    assert calculate_claim(load("CLM-002"))["violations"][0]["evidence"] == "DOC003@v1.0"


def test_calculation_does_not_change_the_claim():
    claim = load("CLM-002")
    before = claim.to_dict()
    calculate_claim(claim)
    assert claim.to_dict() == before