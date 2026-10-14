"""Typed, serializable contracts shared by the MCP tools and agent."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


RetrievalMode = Literal["dense", "hybrid"]
AgentDecision = Literal["APPROVE", "REJECT", "ESCALATE", "NO_ANSWER", "NEED_MORE_INFO"]
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
    date: str
    owner: str
    dense_score: float | None
    bm25_score: float | None


class SearchDocumentsOutput(TypedDict):
    results: list[SearchResultItem]


class EvidenceCitation(TypedDict):
    evidence_ref: str
    doc_id: str
    version: str
    chunk_id: str
    title: str


class EvidenceSearch(TypedDict):
    query: str
    mode: str
    top_k: int
    results: list[SearchResultItem]


class AuditPreviewOutput(TypedDict):
    claim_id: str
    question: str
    decision: AgentDecision
    reason: str
    required_evidence_refs: list[str]
    missing_evidence_refs: list[str]
    evidence: list[SearchResultItem]
    citations: list[EvidenceCitation]
    searches: list[EvidenceSearch]
    calculation: dict
    read_only: bool


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

