"""Lossless, validated evidence at the Retriever -> MCP -> Agent boundary."""
from __future__ import annotations

import math
from collections.abc import Mapping

from src.mcp.contracts import SearchDocumentsOutput, SearchResultItem
from src.models.document import SearchResult


TEXT_FIELDS = ("chunk_id", "doc_id", "title", "version", "date", "owner", "content", "mode")


def source_ref(item: SearchResultItem) -> str:
    """Match the business-rule citation format without changing source metadata."""
    return f"{item['doc_id']}@v{item['version'].removeprefix('v')}"


def parse_search_payload(payload: object) -> SearchDocumentsOutput:
    """Fail explicitly on malformed evidence; never silently drop provenance."""
    if not isinstance(payload, Mapping) or not isinstance(payload.get("results"), list):
        raise ValueError("search_documents must return an object with a results list")
    results = []
    identities = {}
    for item in payload["results"]:
        if not isinstance(item, Mapping):
            raise ValueError("each search result must be an object")
        for key in TEXT_FIELDS:
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"search result requires non-empty {key}")
        if item["mode"] not in {"dense", "hybrid"}:
            raise ValueError("search result mode must be dense or hybrid")
        record = {key: item[key] for key in TEXT_FIELDS}
        for key in ("score", "dense_score", "bm25_score"):
            if key not in item:
                raise ValueError(f"search result is missing {key}")
            value = item[key]
            if key != "score" and value is None:
                record[key] = None
            elif type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{key} must be a finite number")
            else:
                record[key] = float(value)
        identity = (record["doc_id"], record["version"], record["chunk_id"])
        if identity in identities and identities[identity] != record:
            raise ValueError("conflicting data for the same evidence chunk")
        identities[identity] = record
        results.append(record)
    return {"results": results}


def serialize_search_result(result: SearchResult) -> SearchResultItem:
    chunk = result.chunk
    record = {key: getattr(chunk, key) for key in TEXT_FIELDS if key != "mode"}
    record.update(
        score=float(result.score), mode=result.mode,
        dense_score=float(result.dense_score) if result.dense_score is not None else None,
        bm25_score=float(result.bm25_score) if result.bm25_score is not None else None,
    )
    return parse_search_payload({"results": [record]})["results"][0]
