"""MCP tools for policy search and claim status reads."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from src.agent.state_store import StateStore, StateStoreError

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
def _get_retriever() -> Retriever:
    """Build the shared Retriever once, on the first search request."""
    from src.rag.chunker import chunk_documents
    from src.rag.loader import load_documents
    from src.rag.retriever import Retriever

    documents = load_documents(POLICY_DIR)
    if not documents:
        raise ToolError(f"No policy documents found in {POLICY_DIR}")
    return Retriever(chunk_documents(documents))


def _serialize_search_result(result: SearchResult) -> dict[str, object]:
    chunk = result.chunk
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "title": chunk.title,
        "version": chunk.version,
        "date": chunk.date,
        "owner": chunk.owner,
        "content": chunk.content,
        "score": float(result.score),
        "mode": result.mode,
        "dense_score": (
            float(result.dense_score) if result.dense_score is not None else None
        ),
        "bm25_score": (
            float(result.bm25_score) if result.bm25_score is not None else None
        ),
    }


@server.tool()
def search_documents(
    query: str,
    mode: Literal["dense", "hybrid"] = "hybrid",
    top_k: int = 3,
) -> dict[str, list[dict[str, object]]]:
    """Search policy documents and return ranked chunks with source provenance."""
    if not query.strip():
        raise ToolError("query must not be empty")
    if top_k < 1:
        raise ToolError("top_k must be a positive integer")

    try:
        # Keep this boundary aligned with the shared member 1 Retriever contract.
        results = _get_retriever().retrieve(query, mode=mode, top_k=top_k)
    except ToolError:
        raise
    except Exception as exc:
        logger.exception("Policy retrieval failed")
        raise ToolError(f"Policy retrieval failed: {exc}") from exc
    return {"results": [_serialize_search_result(item) for item in results]}


@server.tool()
def get_claim_status(claim_id: str) -> dict[str, str]:
    """Read a claim's persisted status and decision metadata."""
    if not claim_id.strip():
        raise ToolError("claim_id must not be empty")
    try:
        claim = StateStore().get(claim_id)
    except StateStoreError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Claim status read failed for %s", claim_id)
        raise ToolError(f"Unable to read claim status: {exc}") from exc

    return {
        "claim_id": claim.claim_id,
        "status": claim.status.value,
        "decision_reason": claim.decision_reason,
        "updated_at": claim.updated_at,
    }


def main() -> None:
    """Run the MCP server over stdio with protocol-only stdout."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

