"""Deterministic claim checks against the policy corpus (TV2, Day 2).

`calculate_claim` is read-only: it never changes state. It returns totals,
rule violations and missing data, plus a recommended status the agent can
cite as evidence. Limits mirror Member 1's policy documents; every issue
carries an evidence reference such as "DOC003@v1.0".
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date

from src.models.claim import Claim, ClaimStatus

HOTEL_REF, MEAL_REF = "DOC003@v1.0", "DOC004@v1.0"
RECEIPT_REF, DEADLINE_REF, INTL_REF = "DOC006@v1.0", "DOC002@v2.0", "DOC008@v1.0"
TRANSPORT_REF = "DOC005@v1.0"

HOTEL_LIMITS = {  # VND per night, keys normalised (no accents, no spaces)
    "hochiminhcity": 2_000_000, "hochiminh": 2_000_000, "hanoi": 2_000_000, "danang": 1_500_000,
}
HOTEL_OTHER_DOMESTIC = 1_200_000
MEAL_LIMIT_DOMESTIC, MEAL_LIMIT_INTERNATIONAL = 500_000, 1_000_000  # VND per day
RECEIPT_THRESHOLD = 500_000  # receipt required from this amount (DOC006)
SUBMISSION_DAYS = 10  # DOC002 v2.0 supersedes DOC001 v1.0 (15 days)
ALCOHOL_WORDS = {"ruou", "bia", "alcohol", "beer", "wine"}

# When several outcomes apply, the first one in this list wins.
OUTCOME_PRIORITY = [ClaimStatus.REJECTED, ClaimStatus.NEED_MORE_INFO, ClaimStatus.ESCALATED]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c))


def _issue(code: str, message: str, outcome: ClaimStatus, evidence: str) -> dict:
    return {"code": code, "message": message, "outcome": outcome.value, "evidence": evidence}


def calculate_claim(claim: Claim) -> dict:
    # Dataclasses are mutable: validate again before making a recommendation.
    claim.__post_init__()
    totals = claim.total_by_category()
    total = sum(totals.values())
    violations: list[dict] = []
    missing: list[dict] = []

    for e in claim.expenses:  # non-reimbursable items
        if ALCOHOL_WORDS & set(re.findall(r"\w+", _norm(e.description))):
            violations.append(_issue(
                "NOT_REIMBURSABLE",
                f"Alcoholic beverages are not reimbursable: '{e.description}' ({e.amount:,} VND)",
                ClaimStatus.REJECTED, MEAL_REF))

    daily: dict[str, dict[date, int]] = {"hotel": defaultdict(int), "meal": defaultdict(int)}
    for expense in claim.expenses:
        if expense.category in daily:
            for allocation in expense.daily_amounts():
                daily[expense.category][allocation.expense_date] += allocation.amount

    hotel = totals.get("hotel", 0)
    if hotel:
        if claim.is_international:
            missing.append(_issue(
                "NO_HOTEL_POLICY",
                f"No hotel limit is defined for {claim.city}; a limit must not be invented",
                ClaimStatus.ESCALATED, INTL_REF))
        else:
            limit = HOTEL_LIMITS.get(_norm(claim.city).replace(" ", ""), HOTEL_OTHER_DOMESTIC)
            for night, amount in sorted(daily["hotel"].items()):
                if amount > limit:
                    violations.append(_issue(
                        "HOTEL_OVER_LIMIT",
                        f"Hotel {amount:,} VND on {night} exceeds the {limit:,} VND nightly limit for {claim.city}",
                        ClaimStatus.ESCALATED, HOTEL_REF))

    meal = totals.get("meal", 0)
    if meal:
        limit = MEAL_LIMIT_INTERNATIONAL if claim.is_international else MEAL_LIMIT_DOMESTIC
        for day, amount in sorted(daily["meal"].items()):
            if amount > limit:
                violations.append(_issue(
                    "MEAL_OVER_LIMIT",
                    f"Meals {amount:,} VND on {day} exceed the {limit:,} VND daily allowance",
                    ClaimStatus.ESCALATED, MEAL_REF))

    for expense in claim.expenses:
        if expense.category != "transport":
            continue
        if not expense.business_purpose.strip():
            missing.append(_issue(
                "MISSING_TRANSPORT_PURPOSE", "Record the business purpose of the transportation expense",
                ClaimStatus.NEED_MORE_INFO, TRANSPORT_REF))
        # Structured input is authoritative; also catch explicit legacy descriptions.
        description = _norm(expense.description)
        luxury = expense.is_luxury_upgrade or any(
            phrase in description for phrase in ("luxury vehicle upgrade", "luxury upgrade", "nang cap xe sang")
        )
        if luxury and not expense.prior_approval:
            violations.append(_issue(
                "UNAPPROVED_LUXURY_UPGRADE", "Luxury vehicle upgrades require prior approval for the upgrade",
                ClaimStatus.REJECTED, TRANSPORT_REF))

    for e in claim.expenses:  # receipts
        if e.amount >= RECEIPT_THRESHOLD and not e.has_receipt:
            missing.append(_issue(
                "MISSING_RECEIPT",
                f"Receipt required for {e.category} {e.amount:,} VND on {e.expense_date}",
                ClaimStatus.NEED_MORE_INFO, RECEIPT_REF))

    late_days = (claim.submitted_date - claim.end_date).days
    if late_days > SUBMISSION_DAYS:
        violations.append(_issue(
            "LATE_SUBMISSION",
            f"Submitted {late_days} days after returning; the limit is {SUBMISSION_DAYS} days",
            ClaimStatus.ESCALATED, DEADLINE_REF))

    if claim.is_international and not claim.prior_approval:
        violations.append(_issue(
            "NO_PRIOR_APPROVAL", "International travel requires prior manager approval",
            ClaimStatus.ESCALATED, INTL_REF))

    outcomes = {i["outcome"] for i in violations + missing}
    recommended = next((s for s in OUTCOME_PRIORITY if s.value in outcomes), ClaimStatus.APPROVED)

    return {
        "claim_id": claim.claim_id,
        "summary": (
            f"{claim.claim_id}: {claim.days} days in {claim.city}, total {total:,} VND; "
            f"{len(violations)} violation(s), {len(missing)} missing item(s) -> {recommended.value}"
        ),
        "total": total,
        "totals": totals,
        "violations": violations,
        "missing_data": missing,
        "recommended_status": recommended.value,
    }
