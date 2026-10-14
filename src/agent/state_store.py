"""JSON-backed claim state store (TV2, Day 2).

The only place that reads or writes claim state. Every status change goes
through `update_status`, which enforces the transition table in claim.py.
Failures raise StateStoreError; the tool layer (Day 3) turns them into
"Error: ..." strings.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.models.claim import Claim, ClaimStatus, can_transition

DEFAULT_PATH = Path(__file__).parents[2] / "data" / "claims" / "claims.json"
VN_TZ = timezone(timedelta(hours=7))


class StateStoreError(Exception):
    pass


class StateStore:
    def __init__(self, path: Path | str = DEFAULT_PATH) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, Claim]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {c.claim_id: c for c in map(Claim.from_dict, raw)}

    def _save(self, claims: dict[str, Claim]) -> None:
        data = [c.to_dict() for c in claims.values()]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)  # atomic: a crash never leaves a half-written file

    def all(self) -> list[Claim]:
        return list(self._load().values())

    def get(self, claim_id: str) -> Claim:
        claims = self._load()
        if claim_id not in claims:
            raise StateStoreError(f"Claim not found: {claim_id}")
        return claims[claim_id]

    def update_status(self, claim_id: str, new_status: ClaimStatus | str, reason: str) -> Claim:
        try:
            new_status = ClaimStatus(new_status)
        except ValueError:
            raise StateStoreError(f"Unknown status: {new_status}") from None
        if not reason.strip():
            raise StateStoreError("A reason is required for a status change")

        claims = self._load()
        if claim_id not in claims:
            raise StateStoreError(f"Claim not found: {claim_id}")
        claim = claims[claim_id]
        if not can_transition(claim.status, new_status):
            raise StateStoreError(
                f"Invalid transition for {claim_id}: {claim.status.value} -> {new_status.value}"
            )

        claim.status = new_status
        claim.decision_reason = reason.strip()
        claim.updated_at = datetime.now(VN_TZ).isoformat(timespec="seconds")
        self._save(claims)
        return claim