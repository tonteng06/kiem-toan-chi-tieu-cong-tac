"""Regression checks runnable with unittest alone or with the full pytest suite."""
import copy
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.agent.business_rules import calculate_claim
from src.agent.state_store import StateStore, StateStoreError
from src.models.claim import Claim, ClaimStatus, Expense


SAMPLE = Path(__file__).parents[1] / "data" / "claims" / "claims.json"


def sample():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def expense(category="meal", amount=300_000, **overrides):
    return {"category": category, "amount": amount, "expense_date": "2026-09-08",
            "description": "Business expense", "has_receipt": True, **overrides}


def claim_with(*expenses, **overrides):
    raw = sample()[0]
    raw.update(overrides)
    raw["expenses"] = list(expenses)
    return Claim.from_dict(raw)


class InputValidationTests(unittest.TestCase):
    def test_receipt_requires_real_boolean(self):
        for bad in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, "boolean"):
                claim_with(expense(has_receipt=bad))

    def test_prior_approval_requires_real_boolean(self):
        for bad in ("false", "true", 0, 1, None):
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, "boolean"):
                claim_with(expense(), prior_approval=bad)

    def test_transport_flags_require_real_booleans(self):
        for field in ("prior_approval", "is_luxury_upgrade"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "boolean"):
                claim_with(expense("transport", **{field: "false"}))

    def test_actual_false_keeps_receipt_missing(self):
        result = calculate_claim(claim_with(expense(amount=500_000, has_receipt=False)))
        self.assertEqual(result["recommended_status"], "NEED_MORE_INFO")
        self.assertEqual(result["missing_data"][0]["code"], "MISSING_RECEIPT")

    def test_amount_must_be_positive_integer(self):
        for bad in (True, False, "300000", 300000.5, 0, -1, None):
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, "positive integer"):
                claim_with(expense(amount=bad))

    def test_direct_constructor_also_validates(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            Expense("meal", 100, date(2026, 9, 8), has_receipt="false")

    def test_empty_claim_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            claim_with()

    def test_expense_outside_trip_rejected(self):
        for day in ("2026-09-07", "2026-09-12"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "within the trip"):
                claim_with(expense(expense_date=day))

    def test_blank_identifiers_rejected(self):
        for field in ("claim_id", "employee", "city", "country"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "non-empty"):
                claim_with(expense(), **{field: " "})

    def test_invalid_allocation_sum_rejected(self):
        with self.assertRaisesRegex(ValueError, "sum"):
            claim_with(expense(allocations=[{"expense_date": "2026-09-08", "amount": 1}]))

    def test_duplicate_allocation_dates_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            claim_with(expense(allocations=[{"expense_date": "2026-09-08", "amount": 150_000}] * 2))

    def test_allocation_outside_trip_rejected(self):
        with self.assertRaisesRegex(ValueError, "within the trip"):
            claim_with(expense(allocations=[{"expense_date": "2026-09-12", "amount": 300_000}]))

    def test_hotel_checkout_night_rejected(self):
        with self.assertRaisesRegex(ValueError, "hotel night"):
            claim_with(expense("hotel", expense_date="2026-09-11"))

    def test_hotel_on_same_day_trip_rejected(self):
        with self.assertRaisesRegex(ValueError, "hotel night"):
            claim_with(expense("hotel"), end_date="2026-09-08")

    def test_mutated_claim_revalidated(self):
        claim = claim_with(expense())
        claim.expenses[0].has_receipt = "false"
        with self.assertRaisesRegex(ValueError, "boolean"):
            calculate_claim(claim)


class DailyLimitTests(unittest.TestCase):
    def test_single_meal_not_diluted_over_trip(self):
        result = calculate_claim(claim_with(expense(amount=900_000)))
        self.assertEqual(result["recommended_status"], "ESCALATED")
        self.assertEqual(result["violations"][0]["code"], "MEAL_OVER_LIMIT")

    def test_multiple_receipts_same_day_combined(self):
        result = calculate_claim(claim_with(expense(), expense()))
        self.assertEqual(result["recommended_status"], "ESCALATED")

    def test_limit_boundary_and_different_days(self):
        result = calculate_claim(claim_with(expense(amount=500_000), expense(amount=500_000, expense_date="2026-09-09")))
        self.assertEqual(result["recommended_status"], "APPROVED")

    def test_explicit_daily_breakdown_can_pass(self):
        claim = claim_with(expense(amount=900_000, allocations=[
            {"expense_date": "2026-09-08", "amount": 400_000},
            {"expense_date": "2026-09-09", "amount": 500_000}]))
        self.assertEqual(calculate_claim(claim)["recommended_status"], "APPROVED")

    def test_uneven_breakdown_cannot_hide_over_limit_day(self):
        claim = claim_with(expense(amount=900_000, allocations=[
            {"expense_date": "2026-09-08", "amount": 600_000},
            {"expense_date": "2026-09-09", "amount": 300_000}]))
        self.assertEqual(calculate_claim(claim)["recommended_status"], "ESCALATED")

    def test_hotel_one_expensive_night_not_diluted(self):
        claim = claim_with(expense("hotel", 2_100_000))
        result = calculate_claim(claim)
        self.assertEqual(result["recommended_status"], "ESCALATED")
        self.assertEqual(result["violations"][0]["code"], "HOTEL_OVER_LIMIT")

    def test_overlapping_hotel_allocations_are_summed(self):
        claim = claim_with(expense("hotel", 1_100_000), expense("hotel", 1_100_000))
        self.assertEqual(calculate_claim(claim)["recommended_status"], "ESCALATED")

    def test_vietnamese_city_and_country_normalization(self):
        claim = claim_with(expense("hotel", 1_400_000), city="\u0110\u00e0 N\u1eb5ng", country=" vn ")
        self.assertEqual(calculate_claim(claim)["recommended_status"], "APPROVED")

    def test_international_meal_boundary(self):
        for amount, status in ((1_000_000, "APPROVED"), (1_000_001, "ESCALATED")):
            with self.subTest(amount=amount):
                claim = claim_with(expense(amount=amount), country="SG", prior_approval=True)
                self.assertEqual(calculate_claim(claim)["recommended_status"], status)


class TransportTests(unittest.TestCase):
    def test_missing_business_purpose_requests_information(self):
        result = calculate_claim(claim_with(expense("transport")))
        self.assertEqual(result["recommended_status"], "NEED_MORE_INFO")
        self.assertEqual(result["missing_data"][0]["evidence"], "DOC005@v1.0")

    def test_unapproved_luxury_upgrade_rejected(self):
        claim = claim_with(expense("transport", is_luxury_upgrade=True, business_purpose="Client meeting"))
        result = calculate_claim(claim)
        self.assertEqual(result["recommended_status"], "REJECTED")
        self.assertEqual(result["violations"][0]["code"], "UNAPPROVED_LUXURY_UPGRADE")

    def test_legacy_luxury_description_also_checked(self):
        claim = claim_with(expense("transport", description="Luxury vehicle upgrade", business_purpose="Client meeting"))
        self.assertEqual(calculate_claim(claim)["recommended_status"], "REJECTED")

    def test_trip_approval_does_not_approve_upgrade(self):
        claim = claim_with(expense("transport", is_luxury_upgrade=True, business_purpose="Client meeting"), prior_approval=True)
        self.assertEqual(calculate_claim(claim)["recommended_status"], "REJECTED")

    def test_approved_upgrade_can_pass(self):
        claim = claim_with(expense("transport", is_luxury_upgrade=True, prior_approval=True, business_purpose="Client meeting"))
        self.assertEqual(calculate_claim(claim)["recommended_status"], "APPROVED")


class IntegrationRegressionTests(unittest.TestCase):
    def test_sample_outcomes_and_totals_unchanged(self):
        expected = ["APPROVED", "ESCALATED", "NEED_MORE_INFO", "ESCALATED", "APPROVED", "REJECTED", "ESCALATED"]
        claims = sample()
        self.assertEqual(len(claims), len(expected))
        for raw, status in zip(claims, expected):
            with self.subTest(claim=raw["claim_id"]):
                claim = Claim.from_dict(raw)
                before = copy.deepcopy(claim.to_dict())
                result = calculate_claim(claim)
                self.assertEqual(result["recommended_status"], status)
                self.assertEqual(result["total"], sum(e["amount"] for e in raw["expenses"]))
                self.assertEqual(claim.to_dict(), before)
                self.assertEqual(Claim.from_dict(json.loads(json.dumps(before))), claim)

    def test_extended_fields_survive_state_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "claims.json"
            shutil.copyfile(SAMPLE, path)
            store = StateStore(path)
            expenses = store.get("CLM-001").to_dict()["expenses"]
            store.update_status("CLM-001", "APPROVED", "Within limits")
            reloaded = StateStore(path).get("CLM-001")
            self.assertEqual(reloaded.status, ClaimStatus.APPROVED)
            self.assertEqual(reloaded.to_dict()["expenses"], expenses)
            with self.assertRaises(StateStoreError):
                store.update_status("CLM-001", "REJECTED", "Cannot re-decide")

    def test_deadline_boundary(self):
        for submitted, expected in (("2026-09-21", "APPROVED"), ("2026-09-22", "ESCALATED")):
            with self.subTest(submitted=submitted):
                claim = claim_with(expense(), submitted_date=submitted)
                self.assertEqual(calculate_claim(claim)["recommended_status"], expected)


if __name__ == "__main__":
    unittest.main()
