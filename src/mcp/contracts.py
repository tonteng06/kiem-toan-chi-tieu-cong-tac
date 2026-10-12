"""Typed, serializable contracts shared by the MCP tools and agent."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


RetrievalMode = Literal["dense", "hybrid"]
AgentDecision = Literal["APPROVE", "REJECT", "ESCALATE", "NO_ANSWER"]
PersistableDecision = Literal[
    "APPROVE", "REJECT", "ESCALATE", "NEED_MORE_INFO"
]


class SearchDocumentsInput(TypedDict):
    query: str
    mode: NotRequired[RetrievalMode]
    top_k: NotRequired[int]


class SearchResultItem(TypedDict):
    chunk_id: str
    doc_id: str
    title: str
    version: str
    content: str
    score: float
    mode: str


class SearchDocumentsOutput(TypedDict):
    results: list[SearchResultItem]


class GetClaimStatusInput(TypedDict):
    claim_id: str


class ClaimStatusOutput(TypedDict):
    claim_id: str
    status: str
    decision_reason: str
    updated_at: str


class SubmitDecisionInput(TypedDict):
    claim_id: str
    decision: PersistableDecision
    reason: str
    evidence_refs: list[str]


class SubmitDecisionOutput(TypedDict):
    claim_id: str
    decision: PersistableDecision
    status: str
    updated_at: str

