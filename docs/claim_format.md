# Claim input contract

## Validation

- `claim_id`, `employee`, `city`, `country`: non-empty strings. Country is a
  two-letter code; domestic detection accepts case/whitespace variants of `VN`.
- Dates use ISO `YYYY-MM-DD`. End date cannot precede start date; submission
  cannot precede return. Every expense date must fall within the trip.
- At least one expense is required. Amounts are positive integer VND values.
  Numeric strings, fractions and booleans are rejected rather than coerced.
- `has_receipt`, claim/expense `prior_approval`, and `is_luxury_upgrade` must be
  JSON booleans (`true`/`false`). Strings such as `"false"` and numbers are invalid.
- `calculate_claim` validates again because callers can mutate dataclass fields.
  Invalid inputs raise `ValueError`; they must not be converted into an approval.

## Meal days and hotel nights

Each expense still represents one original invoice/expense. Its `amount` is
used for the receipt threshold; splitting allocations cannot bypass that check.

Without `allocations`, all money belongs to `expense_date`. For an invoice that
covers several days/nights, supply the actual breakdown:

```json
{
  "category": "meal",
  "amount": 900000,
  "expense_date": "2026-09-09",
  "description": "Meals over two days",
  "has_receipt": true,
  "allocations": [
    {"expense_date": "2026-09-08", "amount": 400000},
    {"expense_date": "2026-09-09", "amount": 500000}
  ]
}
```

Allocation dates must be unique within an invoice, within the trip, and their
positive integer amounts must add up exactly to the invoice amount. Allocations
are supported only for hotel and meal categories. A hotel allocation date is the
night's start date, so it must precede the trip end date (checkout).

The calculator sums all invoices/allocations on the same day or night and checks
each total against its policy limit. A cheap day cannot offset an expensive day.
It never divides an invoice by trip duration or infers amounts from descriptions.
Callers must provide a breakdown for a multi-day invoice; otherwise the full
amount is conservatively checked on its expense date and may be escalated.

The seven synthetic sample claims now contain explicit allocations chosen for
those scenarios. Their original totals, persisted statuses and expected
recommendations are preserved. These fixture allocations are not an inference
method to use with real claims.

## Transportation (DOC005)

- Record `business_purpose` on each transportation expense. A missing or blank
  value yields `MISSING_TRANSPORT_PURPOSE` / `NEED_MORE_INFO`. A general trip
  purpose is not automatically copied to new transportation inputs.
- Set `is_luxury_upgrade: true` for a luxury vehicle upgrade. Such an expense
  requires its own `prior_approval: true`; claim-level international travel
  approval does not authorize an upgrade.
- Without that approval, `UNAPPROVED_LUXURY_UPGRADE` recommends `REJECTED`.
- Explicit legacy phrases (`luxury vehicle upgrade`, `luxury upgrade`,
  `nang cap xe sang`, ignoring Vietnamese accents) also trigger the upgrade rule.
  This compatibility check is not a general natural-language classifier; new
  integrations should populate the structured flag.

State serialization preserves allocations and all transportation fields.
The existing outcome priority and claim transition table remain unchanged.
