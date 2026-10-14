# MCP tool contracts and read-only Agent handoff

Status: `search_documents` and `get_claim_status` are implemented on the
`member3-mcp` integration branch. The 14 October read-only bridge connects these
responses to the existing deterministic reasoner. `submit_decision` is scheduled
for 15 October. The server/client use the MCP Python SDK 2.x API.

## Shared conventions

- Claim inputs and persisted expense fields follow `docs/claim_format.md`.
  Multi-day costs require explicit allocations; boolean strings are invalid.

- Use JSON-compatible input and output values with type hints and the `TypedDict`
  definitions in `src/mcp/contracts.py`.
- Return tool failures as clear errors; do not silently return empty evidence or
  a successful-looking result when a dependency fails.
- `search_documents` preserves provenance from `SearchResult.chunk`: `doc_id`,
  `title`, `version`, and `chunk_id` must travel with the content.
- MCP stdio is the server's protocol channel. Diagnostics belong on stderr,
  never stdout.
- The client calls `tools/list` at runtime and calls tools by discovered name.

## `search_documents`

Purpose: retrieve evidence relevant to a query.

Input:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `query` | string | yes | Search query from the agent |
| `mode` | `dense` or `hybrid` | no | Defaults to `hybrid` |
| `top_k` | integer | no | Defaults to `3`; must be positive |

Output: `{"results": [...]}`. Each result includes `chunk_id`, `doc_id`,
`title`, `version`, `date`, `owner`, `content`, `score`, `mode`, `dense_score`,
and `bm25_score`. The MCP adapter flattens `SearchResult.chunk` at
serialization time, preserving the source metadata and retrieval scores.

## `get_claim_status`

Purpose: read the current state of a claim, including after a decision write.

Input: `{"claim_id": "..."}`.

Output: `claim_id`, `status`, `decision_reason`, and `updated_at`. A missing claim
must return an explicit tool error.

## Read-only Agent integration (14 October)

`src/mcp/evidence.py` owns serialization and validation at both ends of the
boundary. It preserves all `SearchResultItem` fields, validates finite scores,
and rejects missing provenance or conflicting data. Empty retrieval is allowed;
it is never interpreted as sufficient evidence for a decision.

`src/mcp/client.py:search_payload` accepts SDK 2.x structured content or exactly
one JSON text block. Tool errors, malformed JSON and invalid metadata raise a
clear `ValueError`; they do not silently become an empty success response.

Member 2 can call:

```python
from src.mcp.agent_bridge import preview_audit_via_mcp

preview = await preview_audit_via_mcp(
    client, claim, user_question, mode="hybrid", top_k=3
)
```

The bridge calls the discovered `search_documents` tool and uses the existing
`calculate_claim` function. It does not implement or replace the future LLM loop.
`user_question` is a retrieval hint for auditing the structured `claim`, not an
arbitrary general-knowledge question. Do not use this facade as a general QA API.

The output is `AuditPreviewOutput`: final `decision`, `reason`, complete evidence,
document/version/chunk citations, required/missing references, each search's
arguments/results, calculation details and `read_only: true`. The calculation
is an intermediate candidate: consumers must use the evidence-gated `decision`.
No write tool or `StateStore.update_status` is called.

Source requirements follow the current rule set: deadline/receipts, category
policies, international policy where relevant, every reported issue source, and
DOC007 for over-limit exceptions. A targeted follow-up may retrieve missing
sources. The default is at most 6 searches (configurable from 1 to 10), and each
missing source is targeted at most once. Retrieval weights and Top-K defaults
are unchanged. Scores are ranking values, not refusal confidence thresholds.

If a required document/version remains unavailable, final `decision` is
`NO_ANSWER`; the calculation's candidate recommendation must not authorize a
write. If a source's metadata/content changes between searches, fail explicitly.
Keep the `required_policy_refs` handoff synchronized when Member 2 adds rules.
Source/version coverage is a necessary check, not a semantic faithfulness score.
The current reasoner uses deterministic constants matching the bundled policies;
policy changes require the business-logic owner to update and test those rules.

`NEED_MORE_INFO` remains an explicit workflow outcome when policy evidence is
present but claim information (such as receipts) is missing. It is distinct from
missing policy evidence (`NO_ANSWER`). This follows the existing shared state
model; the full Agent owner still controls the eventual action boundary.

## `submit_decision`

Purpose: persist an allowed agent decision to the claim state store. This tool
will be implemented with a real state change and followed immediately by
`get_claim_status` to verify it.

Input: `claim_id`, `decision`, `reason`, and `evidence_refs` (document IDs with
versions, for example `DOC003@v1.2`).

The current `ClaimStatus` model supports `APPROVED`, `REJECTED`, `ESCALATED`,
and `NEED_MORE_INFO`; it has no persisted `NO_ANSWER` status. The draft allows
the first three write decisions and the explicit workflow transition
`NEED_MORE_INFO`. `NO_ANSWER` should not call this write tool. The distinction
between an agent outcome and a persisted claim transition is:

| Agent decision | Persisted claim status |
| --- | --- |
| `APPROVE` | `APPROVED` |
| `REJECT` | `REJECTED` |
| `ESCALATE` | `ESCALATED` |
| `NEED_MORE_INFO` | `NEED_MORE_INFO` (only when business logic explicitly chooses this transition) |
| `NO_ANSWER` | No write; wait for more evidence or clarification |

Output: `claim_id`, the accepted `decision`, resulting `status`, and
`updated_at`. Reject writes for missing claims, invalid transitions, or
unsupported decisions. After a successful write, the caller must read the claim
again and compare the actual status with the expected status.

## Decisions to confirm with the group

- Confirm whether missing evidence should remain `NO_ANSWER` or become the
  persisted `NEED_MORE_INFO` status. They are distinct in the current draft;
  confirm whether the agent should explicitly map between them.
- Confirm the exact shape of `evidence_refs` with the agent owner.
- Confirm the state store format and concurrency expectations before
  implementing `submit_decision`.
- Member 2's branch notes `calculate_claim` and `get_claim` as proposed tools.
  Confirm whether those belong in the MCP server or remain internal Agent/
  business-logic functions; the day-one plan only requires the three tools
  above.

## Runtime notes

- Run the server with `python -m src.mcp.server`; stdio is reserved for MCP
  protocol messages, and application logging is configured for stderr.
- The retriever is initialized lazily from `data/policies/` on the first search.
- Claim reads use `StateStore` and return an explicit MCP tool error for an
  unknown claim.

