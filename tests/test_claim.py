import json
from datetime import date
from pathlib import Path

import pytest

from src.models.claim import Claim, ClaimStatus, Expense, can_transition

CLAIMS_FILE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"


def load_claims() -> dict[str, Claim]:
    raw = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))
    return {c.claim_id: c for c in map(Claim.from_dict, raw)}


def test_all_sample_claims_load_and_roundtrip():
    claims = load_claims()
    assert len(claims) == 7
    for c in claims.values():
        assert Claim.from_dict(json.loads(json.dumps(c.to_dict()))) == c


def test_derived_fields():
    claims = load_claims()
    assert claims["CLM-001"].days == 4 and claims["CLM-001"].nights == 3
    assert claims["CLM-004"].is_international
    assert not claims["CLM-002"].is_international
    assert (claims["CLM-007"].submitted_date - claims["CLM-007"].end_date).days == 12


def test_final_statuses_cannot_change():
    for final in (ClaimStatus.APPROVED, ClaimStatus.REJECTED):
        for dst in ClaimStatus:
            assert not can_transition(final, dst)
    assert can_transition(ClaimStatus.SUBMITTED, ClaimStatus.ESCALATED)
    assert can_transition(ClaimStatus.ESCALATED, ClaimStatus.APPROVED)


def test_invalid_data_is_rejected():
    with pytest.raises(ValueError):
        Expense("gift", 100000, date(2026, 9, 1))
    with pytest.raises(ValueError):
        Expense("hotel", 0, date(2026, 9, 1))
    bad = {**json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))[0], "end_date": "2026-09-01"}
    with pytest.raises(ValueError):
        Claim.from_dict(bad)