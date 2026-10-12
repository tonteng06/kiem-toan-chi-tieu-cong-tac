# MCP tool contracts draft

Status: day-one draft for group review. The server/client skeleton exists; the
tool handlers and claim state side effect are scheduled for later integration.
The skeleton targets the official MCP Python SDK 2.x API. `requirements.txt`
contains the union of this dependency and the RAG dependencies listed on the
member 1 branch so the team can use one shared installation file after merging.

## Shared conventions

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
`title`, `version`, `content`, `score`, and `mode`. The current RAG model nests
the metadata under `SearchResult.chunk`; the MCP adapter should flatten it only
at serialization time without dropping provenance.

## `get_claim_status`

Purpose: read the current state of a claim, including after a decision write.

Input: `{"claim_id": "..."}`.

Output: `claim_id`, `status`, `decision_reason`, and `updated_at`. A missing claim
must return an explicit tool error.

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

