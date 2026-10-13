import shutil
from pathlib import Path

import pytest

from src.agent.state_store import StateStore, StateStoreError
from src.models.claim import ClaimStatus

SAMPLE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "claims.json"
    shutil.copy(SAMPLE, path)  # never touch the real sample data
    return StateStore(path)


def test_get_and_all(store):
    assert store.get("CLM-001").status == ClaimStatus.SUBMITTED
    assert len(store.all()) == 7


def test_missing_claim_raises(store):
    with pytest.raises(StateStoreError, match="not found"):
        store.get("CLM-999")
    with pytest.raises(StateStoreError, match="not found"):
        store.update_status("CLM-999", "APPROVED", "x")


def test_update_persists_across_reload(store):
    store.update_status("CLM-001", "APPROVED", "Within all limits")
    claim = StateStore(store.path).get("CLM-001")  # fresh instance reads the file
    assert claim.status == ClaimStatus.APPROVED
    assert claim.decision_reason == "Within all limits"
    assert claim.updated_at


def test_final_status_cannot_change(store):
    with pytest.raises(StateStoreError, match="Invalid transition"):
        store.update_status("CLM-005", "REJECTED", "try again")
    assert store.get("CLM-005").status == ClaimStatus.APPROVED


def test_bad_input_is_rejected(store):
    with pytest.raises(StateStoreError, match="Unknown status"):
        store.update_status("CLM-001", "MAYBE", "x")
    with pytest.raises(StateStoreError, match="reason"):
        store.update_status("CLM-001", "APPROVED", "   ")
    assert store.get("CLM-001").status == ClaimStatus.SUBMITTED