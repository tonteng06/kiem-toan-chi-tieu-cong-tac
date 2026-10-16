"""MCP policy/claim tools with evidence-checked writes and explicit read-back."""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from src.agent.tool_registry import ToolRegistry, build_registry
from src.agent.state_store import StateStore, DEFAULT_PATH
from src.mcp_server.contracts import PersistableDecision
from src.mcp_server.evidence import serialize_search_result
from src.mcp_server.registry_adapter import dispatch_read_tool

if TYPE_CHECKING:
    from src.models.document import SearchResult
    from src.rag.retriever import Retriever


ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "data" / "policies"

# The protocol owns stdout in stdio mode. Route application diagnostics to stderr.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

server = MCPServer("travel-expense-audit")


@lru_cache(maxsize=1)
def _get_store() -> StateStore:
    """Allow isolated demo state without changing the tracked claim fixture."""
    return StateStore(os.environ.get("AIPR_STATE_PATH", str(DEFAULT_PATH)))


@lru_cache(maxsize=1)
def _get_registry() -> ToolRegistry:
    return build_registry(store=_get_store())


def _call_registry(name: str, claim_id: str) -> dict:
    try:
        return dispatch_read_tool(_get_registry(), name, {"claim_id": claim_id})
    except Exception as exc:
        message = str(exc)
        if not message.startswith("Error:"):
            logger.exception("Registry call failed for %s", name)
            message = f"Error: registry tool {name} failed ({type(exc).__name__}: {exc})"
        raise ToolError(message) from exc


@lru_cache(maxsize=1)
def _get_retriever() -> Retriever:
    """Build the shared Retriever once, on the first search request."""
    from src.rag.chunker import chunk_documents
    from src.rag.loader import load_documents
    from src.rag.retriever import Retriever

    documents = load_documents(POLICY_DIR)
    if not documents:
        raise ToolError(f"Error: No policy documents found in {POLICY_DIR}")
    return Retriever(chunk_documents(documents))


def _serialize_search_result(result: SearchResult) -> dict[str, object]:
    return serialize_search_result(result)


@server.tool()
def search_policy(
    query: str,
    mode: Literal["dense", "hybrid"] = "hybrid",
    top_k: int = 3,
) -> dict[str, list[dict[str, object]]]:
    """Search policy documents and return ranked chunks with source provenance."""
    if not query.strip():
        raise ToolError("Error: query must not be empty")
    if top_k < 1:
        raise ToolError("Error: top_k must be a positive integer")

    try:
        # Keep this boundary aligned with the shared member 1 Retriever contract.
        results = _get_retriever().retrieve(query, mode=mode, top_k=top_k)
        payload = {"results": [_serialize_search_result(item) for item in results]}
    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Policy retrieval failed")
        raise ToolError(f"Error: Policy retrieval failed: {exc}") from exc
    return payload


@server.tool()
def get_claim_status(claim_id: str) -> dict[str, str]:
    """Read a claim's persisted status and decision metadata."""
    return _call_registry("get_claim_status", claim_id)


@server.tool()
def get_claim(claim_id: str) -> dict:
    """Read a full claim through the shared TV2 tool registry."""
    return _call_registry("get_claim", claim_id)


@server.tool()
def calculate_claim(claim_id: str) -> dict:
    """Calculate the recommendation through TV2's registered read-only tool."""
    return _call_registry("calculate_claim", claim_id)


@server.tool()
def submit_decision(
    claim_id: str, decision: PersistableDecision, reason: str, evidence_refs: list[str],
) -> dict:
    """Persist an evidence-backed recommendation. Caller MUST immediately read status back."""
    from src.agent.business_rules import calculate_claim as calculate
    from src.mcp_server.agent_bridge import required_policy_refs
    from src.rag.loader import load_documents

    try:
        if not reason.strip():
            raise ValueError("reason must not be empty")
        claim = _get_store().get(claim_id)
        calculation = calculate(claim)
        if decision != calculation["recommended_status"]:
            raise ValueError("decision does not match the calculated recommendation")
        required = required_policy_refs(claim, calculation)
        supplied = set(evidence_refs)
        known = {f"{doc.doc_id}@v{doc.version}" for doc in load_documents(POLICY_DIR)}
        if not required <= supplied or not supplied <= known:
            raise ValueError("missing required evidence or unknown policy/version reference")
        updated = _get_store().update_status(claim_id, decision, reason)
        return {"claim_id": claim_id, "decision": decision, "status": updated.status.value,
                "updated_at": updated.updated_at}
    except Exception as exc:
        raise ToolError(f"Error: submit_decision failed: {exc}") from exc


def main() -> None:
    """Run the MCP server over stdio with protocol-only stdout."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

