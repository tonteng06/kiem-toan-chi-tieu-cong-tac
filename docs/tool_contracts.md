# MCP tool contracts and read-only Agent handoff

Status: `search_policy` and `get_claim_status` are implemented on the
`member3-mcp` integration branch. The 14 October read-only bridge connects these
responses to the existing deterministic reasoner. `submit_decision` is scheduled
for Day 5. The Day 4 registry adapters expose four read tools: `search_policy`,
`get_claim`, `calculate_claim`, `get_claim_status`. The server/client use MCP SDK 2.x.

## Shared conventions

- Claim inputs and persisted expense fields follow `docs/claim_format.md`.
  Multi-day costs require explicit allocations; boolean strings are invalid.

- Use JSON-compatible input and output values with type hints and the `TypedDict`
  definitions in `src/mcp_server/contracts.py`.
- Return tool failures as errors whose message starts with `Error:`; do not silently return empty evidence or
  a successful-looking result when a dependency fails.
- `search_policy` preserves provenance from `SearchResult.chunk`: `doc_id`,
  `title`, `version`, and `chunk_id` must travel with the content.
- MCP stdio is the server's protocol channel. Diagnostics belong on stderr,
  never stdout.
- The client calls `tools/list` at runtime and calls tools by discovered name.

## `search_policy`

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

`src/mcp_server/evidence.py` owns serialization and validation at both ends of the
boundary. It preserves all `SearchResultItem` fields, validates finite scores,
and rejects missing provenance or conflicting data. Empty retrieval is allowed;
it is never interpreted as sufficient evidence for a decision.

`src/mcp_server/client.py:search_payload` accepts SDK 2.x structured content or exactly
one JSON text block. Tool errors, malformed JSON and invalid metadata raise a
clear `ValueError`; they do not silently become an empty success response.

Member 2 can call:

```python
from src.mcp_server.agent_bridge import preview_audit_via_mcp

preview = await preview_audit_via_mcp(
    client, claim, user_question, mode="hybrid", top_k=3
)
```

The bridge calls the discovered `search_policy` tool and uses the existing
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

## Day 4 registry adapter (15 October)

The new synchronous Agent port is `adapters.McpToolbox`: `schemas()` and
`call(name, args) -> str`, backed by one SDK connection in a worker thread.
It discovers tools once, supports explicit `refresh()`, converts schemas to TV2's
format and retains complete raw results in `history`. `LocalToolbox` wraps TV2's
unchanged local registry with the same port. See `docs/mcp_toolbox_handoff.md`
for lifetime, timeout, normalization and owner-confirmation details. The async
helpers below remain supported; discovery is now cached per client.

The three claim tools are registered in TV2's `build_registry`. The MCP server
uses `registry_adapter.dispatch_read_tool` -> TV2 `dispatch` -> the original
registered function. Validation and business rules remain owned by TV2. The
read adapter rejects any registry entry marked `writes=True` before invoking it.

`get_claim(claim_id)` returns the full serialized claim. `calculate_claim(claim_id)`
returns the deterministic totals, issues and `recommended_status` from TV2.
`get_claim_status(claim_id)` preserves its earlier response shape. None writes
state. Registry errors become MCP ToolError responses and retain `Error:` at the
client observation boundary.

The asynchronous Agent loop can consume the same JSON/Error observation format
as the synchronous dispatcher:

```python
from src.mcp_server.client import dispatch_mcp, discover_tools

tools = await discover_tools(client)  # actual MCP input_schema for each tool
observation = await dispatch_mcp(client, "calculate_claim", {"claim_id": "CLM-002"})
```

Arguments may be a dict or JSON string, using TV2's existing `parse_args`.
Ordinary transport, schema and tool failures become `Error: ...` observations;
cancellation propagates. No tool call is retried automatically. Use `await` in
the Agent loop: registering async MCP functions directly as synchronous TV2
Tool.func callbacks would not await them and is unsupported.

For a read-only grounded audit of a stored claim:

```python
from src.mcp_server.agent_bridge import preview_registered_claim_via_mcp

preview = await preview_registered_claim_via_mcp(
    client, "CLM-002", "Audit the Da Nang hotel claim", mode="hybrid", top_k=3
)
```

This calls `get_claim` and `calculate_claim` via MCP and the actual shared
registry, then retrieves policy evidence via `search_policy`. It validates the
calculation's claim identity, totals, status and issue provenance before the
existing evidence gate chooses a final decision. A mismatched/corrupt calculation
raises an error, rather than producing an approval. Missing policy sources still
produce `NO_ANSWER`. The full LLM loop remains TV2's integration responsibility.

`demo_readonly_audit.py --claim-id CLM-002` uses this registered-claim path.
The default in-memory example continues using the earlier local-claim facade.
`smoke_registry.py` verifies the real stdio/registry path without embedding
weights, and verifies the persisted claim file's hash is unchanged.

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
| `APPROVED` | `APPROVED` |
| `REJECTED` | `REJECTED` |
| `ESCALATED` | `ESCALATED` |
| `NEED_MORE_INFO` | `NEED_MORE_INFO` (only when business logic explicitly chooses this transition) |
| `NO_ANSWER` | No claim write; only respond to the user |

Output: `claim_id`, the accepted `decision`, resulting `status`, and
`updated_at`. Reject writes for missing claims, invalid transitions, or
unsupported decisions. After a successful write, the caller must read the claim
again and compare the actual status with the expected status.

## Agreed merge handoff

- Shared names: `search_policy`, `calculate_claim`, `get_claim_status`, `get_claim`,
  `submit_decision`. The current MCP server exposes the four read tools;
  the write action and write/read-back verification remain Day 5 work.
- Persistable decisions are exactly `APPROVED`, `REJECTED`, `ESCALATED`,
  `NEED_MORE_INFO`. `NO_ANSWER` is an Agent response and is never persisted.
- Evidence references are strings such as `DOC003@v1.0`.
- Server ToolError messages and client-normalized MCP errors start with `Error:`.
  The client preserves `is_error=True` while normalizing SDK wrapper messages.
- Confirm concurrency expectations with the state-store owner before write tools.
- Merge order is TV2, TV1, then TV3. Preserve merge commits, never force push.

## Runtime notes

- Run the server with `python -m src.mcp_server.server`; stdio is reserved for MCP
  protocol messages, and application logging is configured for stderr.
- The retriever is initialized lazily from `data/policies/` on the first search.
- Claim reads use `StateStore` and return an explicit MCP tool error for an
  unknown claim.

