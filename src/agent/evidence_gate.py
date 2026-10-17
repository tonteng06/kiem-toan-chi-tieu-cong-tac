"""Evidence gate (TV2, Day 5/6): decides whether the agent may call the write tool.

The gate watches the tool results the agent has actually seen. It lets `submit_decision` through
only when the decision is backed by evidence; otherwise it returns an "Error: ..." string that the
agent sees as an observation. The write never happens in that case.

Rules for submit_decision(claim_id, decision, reason):
  1. NO_ANSWER is never persisted (it is an agent response, not a claim status).
  2. calculate_claim must have been run for this claim in this run.
  3. The decision must equal the rule engine's recommended status (the agent may not approve a
     claim with violations, and may not invent a stricter outcome either).
  4. Every policy reference cited by the calculation (e.g. DOC003@v1.0) must have been seen in a
     search_policy result. Without it there is no policy evidence -> the agent must answer
     NO_ANSWER. A claim with no issues still needs at least one policy search that returned text.
"""
from __future__ import annotations

import json
from typing import Any

ERROR_PREFIX = "Error: "
WRITE_TOOLS = {"submit_decision"}
PERSISTABLE = {"APPROVED", "REJECTED", "ESCALATED", "NEED_MORE_INFO"}


class EvidenceGate:
    def __init__(self) -> None:
        self.calculations: dict[str, dict] = {}  # claim_id -> parsed calculate_claim result
        self.seen_refs: set[str] = set()  # evidence_ref values returned by search_policy
        self.searches_with_results = 0

    # -- observing -------------------------------------------------------------------
    def observe(self, name: str, args: dict, observation: str) -> None:
        """Record a tool result. Errors and unparsable output are ignored (they are no evidence)."""
        if observation.startswith(ERROR_PREFIX):
            return
        try:
            data = json.loads(observation)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        if name == "calculate_claim" and isinstance(data.get("claim_id"), str):
            self.calculations[data["claim_id"]] = data
        elif name == "search_policy":
            results = [r for r in data.get("results", []) if isinstance(r, dict)]
            for r in results:
                if isinstance(r.get("evidence_ref"), str):
                    self.seen_refs.add(r["evidence_ref"])
            if results:
                self.searches_with_results += 1

    @property
    def claims_touched(self) -> bool:
        return bool(self.calculations)

    # -- checking --------------------------------------------------------------------
    def check_write(self, name: str, args: dict[str, Any]) -> str | None:
        """None when the write may go ahead, otherwise an 'Error: ...' observation."""
        if name not in WRITE_TOOLS:
            return None
        claim_id, decision = args.get("claim_id"), args.get("decision")
        if decision == "NO_ANSWER":
            return f"{ERROR_PREFIX}NO_ANSWER is never written to a claim; give it as the final answer instead"
        if decision not in PERSISTABLE:
            return f"{ERROR_PREFIX}decision must be one of {sorted(PERSISTABLE)}, got {decision!r}"
        calc = self.calculations.get(claim_id) if isinstance(claim_id, str) else None
        if calc is None:
            return f"{ERROR_PREFIX}write blocked: run calculate_claim for {claim_id!r} first"
        recommended = calc.get("recommended_status")
        if decision != recommended:
            return (f"{ERROR_PREFIX}write blocked: {decision} conflicts with the business rules "
                    f"(calculate_claim recommends {recommended})")
        required = sorted({i["evidence"] for i in calc.get("violations", []) + calc.get("missing_data", [])
                           if isinstance(i, dict) and "evidence" in i})
        missing = [r for r in required if r not in self.seen_refs]
        if missing:
            return (f"{ERROR_PREFIX}write blocked: no policy evidence yet for {missing}. "
                    "Call search_policy for them, or answer NO_ANSWER if the corpus has nothing")
        if not required and self.searches_with_results == 0:
            return f"{ERROR_PREFIX}write blocked: no policy evidence yet. Call search_policy first"
        return None