from __future__ import annotations
 
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
 
 
class ClaimStatus(str, Enum):
    SUBMITTED = "SUBMITTED"            # initial state, waiting for a decision
    APPROVED = "APPROVED"              # final
    REJECTED = "REJECTED"              # final
    ESCALATED = "ESCALATED"            # sent to a human reviewer
    NEED_MORE_INFO = "NEED_MORE_INFO"  # missing receipt / policy evidence
 
 
# Allowed transitions. APPROVED / REJECTED are final: the agent cannot re-decide them.
TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.SUBMITTED: {
        ClaimStatus.APPROVED, ClaimStatus.REJECTED,
        ClaimStatus.ESCALATED, ClaimStatus.NEED_MORE_INFO,
    },
    ClaimStatus.NEED_MORE_INFO: {ClaimStatus.SUBMITTED},
    ClaimStatus.ESCALATED: {ClaimStatus.APPROVED, ClaimStatus.REJECTED},
    ClaimStatus.APPROVED: set(),
    ClaimStatus.REJECTED: set(),
}
 
CATEGORIES = {"hotel", "meal", "transport", "other"}
 
 
def can_transition(src: ClaimStatus, dst: ClaimStatus) -> bool:
    return dst in TRANSITIONS[src]
 
 
@dataclass
class Expense:
    category: str          # one of CATEGORIES
    amount: int            # VND
    expense_date: date
    description: str = ""
    has_receipt: bool = False
 
    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'")
        if self.amount <= 0:
            raise ValueError("amount must be > 0")
 
 
@dataclass
class Claim:
    claim_id: str
    employee: str
    city: str
    country: str
    start_date: date
    end_date: date
    submitted_date: date   # policy v2.0: submit within 10 days after returning
    purpose: str
    expenses: list[Expense] = field(default_factory=list)
    prior_approval: bool = False   # international trips need prior manager approval (DOC008)
    status: ClaimStatus = ClaimStatus.SUBMITTED
    decision_reason: str = ""
    updated_at: str = ""   # ISO timestamp, set by state_store on write
 
    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        if self.submitted_date < self.end_date:
            raise ValueError("submitted_date is before end_date")
 
    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days
 
    @property
    def days(self) -> int:
        return self.nights + 1
 
    @property
    def is_international(self) -> bool:
        return self.country != "VN"
 
    def total_by_category(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for e in self.expenses:
            totals[e.category] = totals.get(e.category, 0) + e.amount
        return totals
 
    @classmethod
    def from_dict(cls, d: dict) -> Claim:
        return cls(
            claim_id=d["claim_id"],
            employee=d["employee"],
            city=d["city"],
            country=d.get("country", "VN"),
            start_date=date.fromisoformat(d["start_date"]),
            end_date=date.fromisoformat(d["end_date"]),
            submitted_date=date.fromisoformat(d["submitted_date"]),
            purpose=d.get("purpose", ""),
            expenses=[
                Expense(
                    category=e["category"],
                    amount=int(e["amount"]),
                    expense_date=date.fromisoformat(e["expense_date"]),
                    description=e.get("description", ""),
                    has_receipt=bool(e.get("has_receipt", False)),
                )
                for e in d.get("expenses", [])
            ],
            prior_approval=bool(d.get("prior_approval", False)),
            status=ClaimStatus(d.get("status", "SUBMITTED")),
            decision_reason=d.get("decision_reason", ""),
            updated_at=d.get("updated_at", ""),
        )
 
    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat()
        d["end_date"] = self.end_date.isoformat()
        d["submitted_date"] = self.submitted_date.isoformat()
        d["status"] = self.status.value
        for raw, e in zip(d["expenses"], self.expenses):
            raw["expense_date"] = e.expense_date.isoformat()
        return d