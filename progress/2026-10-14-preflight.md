# Preflight fixes - 2026-10-14

Scope: repair confirmed model/business-rule bugs before the planned 14 October
Agent/MCP tasks. These changes are local working-tree changes, not a new commit.

## Changes

- Reject string/numeric booleans, non-integer amounts, empty claims, blank
  identifiers and expense dates outside the trip.
- Add explicit daily/nightly expense allocations with validation of dates,
  positive amounts and matching invoice totals. Check combined spend on each
  date instead of averaging over the trip.
- Enforce transportation business-purpose recording and upgrade-specific prior
  approval under DOC005. Preserve the separation from international trip approval.
- Revalidate mutable claims before calculation. Preserve new fields across JSON
  round-trips and state updates.
- Enrich the seven synthetic sample claims with allocations and transportation
  purposes, retaining their original totals and expected recommendations.
- Add `tests/test_regressions.py`, `requirements-dev.txt`, setup instructions and
  the input contract in `docs/claim_format.md`.

## Verification

Run with CPython 3.12.14:

```text
python -m unittest discover -s tests -p test_regressions.py -v
Ran 32 tests
OK
```

Tests cover malformed inputs, same-day invoice aggregation, daily/nightly
boundaries, unequal allocations, transportation rules, the seven sample outcomes,
JSON round-trips, calculation immutability and persisted read-back on a temp copy.

Full pytest was not run: pytest is unavailable, and the attempted installation
failed because the host could not resolve the package index. Standard-library
regressions are not represented as a passing full pytest run.

MCP stdio and the real embedding model remain unverified. The preflight runtime
probe `asyncio.run(asyncio.sleep(0))` timed out after 15 seconds. No retrieval
quality metric has been rerun or changed in this checkpoint.

## Remaining work for the planned task

- Implement the agreed Agent tool dispatch and `submit_decision` boundary.
- Verify decision write/read-back through MCP with a working async runtime.
- Run the full pytest suite and a real-model retrieval evaluation in the normal
  project environment. Preserve the documented Q13 hybrid miss until retrieval
  changes are intentionally implemented and evaluated.
- Confirm concurrency expectations before exposing state writes to multiple
  simultaneous callers; atomic replacement alone is not a concurrency lock.
