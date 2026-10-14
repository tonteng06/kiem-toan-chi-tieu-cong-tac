"""Tool registry (TV2, Day 3): the one lookup table the dispatcher uses.

Tools are plain functions registered by name. Model output is never evaluated:
the model can only pick a name that exists in this table.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.agent import business_rules
from src.agent.state_store import StateStore

JSON_TYPES = {str: "string", int: "integer", bool: "boolean"}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    params: dict[str, type]  # argument name -> expected type; every argument is required
    func: Callable[..., Any]
    writes: bool = False  # True for tools with a side effect (submit_decision, Day 5)

    def schema(self) -> dict:
        """Tool description in the shape LLM function calling expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {k: {"type": JSON_TYPES[t]} for k, t in self.params.items()},
                "required": list(self.params),
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]


def build_registry(store: StateStore | None = None) -> ToolRegistry:
    """Registry with the read tools. submit_decision (write) is added on Day 5."""
    store = store or StateStore()

    def get_claim(claim_id: str) -> dict:
        return store.get(claim_id).to_dict()

    def get_claim_status(claim_id: str) -> dict:
        c = store.get(claim_id)
        return {
            "claim_id": c.claim_id,
            "status": c.status.value,
            "decision_reason": c.decision_reason,
            "updated_at": c.updated_at,
        }

    def calculate_claim(claim_id: str) -> dict:
        return business_rules.calculate_claim(store.get(claim_id))

    registry = ToolRegistry()
    for tool in (
        Tool("get_claim", "Return the full data of a claim.", {"claim_id": str}, get_claim),
        Tool("get_claim_status", "Return the current persisted status of a claim.",
             {"claim_id": str}, get_claim_status),
        Tool("calculate_claim",
             "Compute totals and check a claim against policy limits. Read-only: never changes status.",
             {"claim_id": str}, calculate_claim),
    ):
        registry.register(tool)
    return registry