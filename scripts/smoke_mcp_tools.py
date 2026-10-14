"""Exercise MCP tools/list and tools/call without downloading embedding weights."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Allow local smoke runs against an ignored .vendor install on Windows.
for extra_path in (ROOT / ".vendor", ROOT / ".vendor" / "win32" / "lib", ROOT / ".vendor" / "win32"):
    if extra_path.exists():
        sys.path.insert(0, str(extra_path))

import numpy as np
from mcp import Client

# The smoke verifies tool wiring and hybrid ranking, not model quality/weights.
sys.modules["sentence_transformers"] = types.SimpleNamespace(
    SentenceTransformer=object
)

import src.rag.retriever as retriever_module
import src.mcp_server.server as mcp_server
from src.mcp_server.client import call_tool, discover_tools


class DeterministicEmbeddingModel:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    1.0 + lowered.count("hotel"),
                    1.0 + lowered.count("receipt"),
                    1.0 + lowered.count("taxi"),
                ]
            )
        vectors = np.asarray(rows, dtype=float)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


async def main() -> None:
    retriever_module.EmbeddingModel = DeterministicEmbeddingModel
    mcp_server._get_retriever.cache_clear()

    async with Client(mcp_server.server) as client:
        tools = await discover_tools(client)
        names = [tool.name for tool in tools]
        if not {"search_policy", "get_claim_status"} <= set(names):
            raise AssertionError(f"Unexpected tools/list result: {names}")

        search = await call_tool(
            client,
            "search_policy",
            {"query": "Da Nang hotel limit", "mode": "hybrid", "top_k": 3},
        )
        if search.is_error:
            raise AssertionError(search.content)
        results = search.structured_content["results"]
        if len(results) != 3:
            raise AssertionError(f"Expected 3 search results, got {len(results)}")
        if not all(
            {"doc_id", "version", "chunk_id", "score", "mode"} <= item.keys()
            for item in results
        ):
            raise AssertionError("Search results are missing provenance fields")

        claim = await call_tool(client, "get_claim_status", {"claim_id": "CLM-001"})
        if claim.is_error or claim.structured_content["claim_id"] != "CLM-001":
            raise AssertionError(claim.content)

        print(
            {
                "tools": names,
                "search_count": len(results),
                "first_source": {
                    key: results[0][key]
                    for key in ("doc_id", "version", "chunk_id")
                },
                "claim_status": claim.structured_content["status"],
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
