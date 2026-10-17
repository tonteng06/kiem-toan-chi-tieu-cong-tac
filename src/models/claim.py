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


def _require_bool(value: object, name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean (true or false)")


def _require_amount(value: object) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError("amount must be a positive integer in VND")


@dataclass
class ExpenseAllocation:
    """Actual amount for one meal day or hotel night; never a trip average."""

    expense_date: date
    amount: int

    def __post_init__(self) -> None:
        if type(self.expense_date) is not date:
            raise ValueError("allocation expense_date must be a date")
        _require_amount(self.amount)
 
 
def can_transition(src: ClaimStatus, dst: ClaimStatus) -> bool:
    return dst in TRANSITIONS[src]
 
 
@dataclass
class Expense:
    category: str          # one of CATEGORIES
    amount: int            # VND
    expense_date: date
    description: str = ""
    has_receipt: bool = False
    allocations: list[ExpenseAllocation] = field(default_factory=list)
    business_purpose: str = ""
    is_luxury_upgrade: bool = False
    prior_approval: bool = False  # approval for this upgrade, not the whole trip
 
    def __post_init__(self) -> None:
        if not isinstance(self.category, str) or self.category not in CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'")
        _require_amount(self.amount)
        if type(self.expense_date) is not date:
            raise ValueError("expense_date must be a date")
        for name in ("has_receipt", "is_luxury_upgrade", "prior_approval"):
            _require_bool(getattr(self, name), name)
        for name in ("description", "business_purpose"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")
        if not isinstance(self.allocations, list):
            raise ValueError("allocations must be a list")
        if self.allocations:
            if self.category not in {"hotel", "meal"}:
                raise ValueError("allocations are only supported for hotel and meal expenses")
            for allocation in self.allocations:
                if not isinstance(allocation, ExpenseAllocation):
                    raise ValueError("allocations must contain ExpenseAllocation values")
                allocation.__post_init__()
            dates = [a.expense_date for a in self.allocations]
            if len(set(dates)) != len(dates):
                raise ValueError("allocation dates must be unique within an expense")
            if sum(a.amount for a in self.allocations) != self.amount:
                raise ValueError("allocation amounts must sum to the expense amount")

    def daily_amounts(self) -> list[ExpenseAllocation]:
        """Without a breakdown, the entire amount belongs to expense_date."""
        return self.allocations or [ExpenseAllocation(self.expense_date, self.amount)]
 
 
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
        for name in ("claim_id", "employee", "city", "country"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if len(self.country.strip()) != 2 or not self.country.strip().isascii() or not self.country.strip().isalpha():
            raise ValueError("country must be a two-letter country code")
        for name in ("start_date", "end_date", "submitted_date"):
            if type(getattr(self, name)) is not date:
                raise ValueError(f"{name} must be a date")
        for name in ("purpose", "decision_reason", "updated_at"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")
        _require_bool(self.prior_approval, "prior_approval")
        if not isinstance(self.status, ClaimStatus):
            raise ValueError("status must be a ClaimStatus")
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        if self.submitted_date < self.end_date:
            raise ValueError("submitted_date is before end_date")
        if not isinstance(self.expenses, list) or not self.expenses:
            raise ValueError("a claim must contain at least one expense")
        for expense in self.expenses:
            if not isinstance(expense, Expense):
                raise ValueError("expenses must contain Expense values")
            expense.__post_init__()
            if not self.start_date <= expense.expense_date <= self.end_date:
                raise ValueError("expense_date must fall within the trip")
            for allocation in expense.daily_amounts():
                if not self.start_date <= allocation.expense_date <= self.end_date:
                    raise ValueError("allocation date must fall within the trip")
                if expense.category == "hotel" and allocation.expense_date >= self.end_date:
                    raise ValueError("hotel night must be before the trip end_date")
 
    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days
 
    @property
    def days(self) -> int:
        return self.nights + 1
 
    @property
    def is_international(self) -> bool:
        return self.country.strip().upper() != "VN"
 
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
                    amount=e["amount"],
                    expense_date=date.fromisoformat(e["expense_date"]),
                    description=e.get("description", ""),
                    has_receipt=e.get("has_receipt", False),
                    allocations=[
                        ExpenseAllocation(date.fromisoformat(a["expense_date"]), a["amount"])
                        for a in e.get("allocations", [])
                    ],
                    business_purpose=e.get("business_purpose", ""),
                    is_luxury_upgrade=e.get("is_luxury_upgrade", False),
                    prior_approval=e.get("prior_approval", False),
                )
                for e in d.get("expenses", [])
            ],
            prior_approval=d.get("prior_approval", False),
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
            for allocation, value in zip(raw["allocations"], e.allocations):
                allocation["expense_date"] = value.expense_date.isoformat()
        return d
