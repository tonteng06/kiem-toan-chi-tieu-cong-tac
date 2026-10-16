"""Tool registry (TV2, Day 3): the one lookup table the dispatcher uses.

Tools are plain functions registered by name. Model output is never evaluated:
the model can only pick a name that exists in this table.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.agent import business_rules
from src.agent.state_store import StateStore

JSON_TYPES = {str: "string", int: "integer", bool: "boolean"}
POLICY_MODES = ("dense", "hybrid")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    params: dict[str, type]  # argument name -> expected type; required unless in `defaults`
    func: Callable[..., Any]
    writes: bool = False  # True for tools with a side effect (submit_decision, Day 5)
    defaults: dict[str, Any] = field(default_factory=dict)  # optional arguments and their defaults

    def schema(self) -> dict:
        """Tool description in the shape LLM function calling expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    k: {"type": JSON_TYPES[t], **({"default": self.defaults[k]} if k in self.defaults else {})}
                    for k, t in self.params.items()
                },
                "required": [k for k in self.params if k not in self.defaults],
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


def build_registry(store: StateStore | None = None, retriever: Any | None = None) -> ToolRegistry:
    """Registry with the read tools. submit_decision (write) is added on Day 5.

    `retriever` is Member 1's `Retriever` (anything with `.retrieve(query, mode, top_k)`).
    Without it, `search_policy` is simply not registered.
    """
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

    def search_policy(query: str, mode: str = "hybrid", top_k: int = 3) -> dict:
        """Policy retrieval with provenance. An empty result list is NOT evidence."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if mode not in POLICY_MODES:
            raise ValueError(f"mode must be one of {list(POLICY_MODES)}, got {mode!r}")
        if top_k < 1:
            raise ValueError("top_k must be a positive integer")
        results = []
        for r in retriever.retrieve(query, mode=mode, top_k=top_k):
            c = r.chunk
            results.append({
                "chunk_id": c.chunk_id, "doc_id": c.doc_id, "title": c.title,
                "version": c.version, "date": c.date, "owner": c.owner,
                "evidence_ref": f"{c.doc_id}@v{c.version}",
                "content": c.content, "score": r.score, "mode": r.mode,
                "dense_score": r.dense_score, "bm25_score": r.bm25_score,
            })
        return {"results": results}

    registry = ToolRegistry()
    if retriever is not None:
        registry.register(Tool(
            "search_policy",
            "Search the travel-expense policy corpus. Returns chunks with doc_id, version and "
            "evidence_ref (e.g. DOC003@v1.0). No results means no evidence: do not guess.",
            {"query": str, "mode": str, "top_k": int}, search_policy, defaults={"mode": "hybrid", "top_k": 3},
        ))
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