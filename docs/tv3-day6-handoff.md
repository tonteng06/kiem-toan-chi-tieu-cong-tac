# TV3 integration handoff for 16 October

The revised schedule moves write/read-back to 15 October. The fetched main
(`efc683b`) and TV3 branch (`f33be6a`) did not yet expose a write tool, so this
change first closes that TV3 integration blocker. Main was merged without conflicts.

## TV2 connection

Use the existing synchronous `McpToolbox` with `run_agent(question, llm, toolbox)`.
Discovery now advertises `submit_decision` with the previously documented signature:
claim_id, decision, reason, evidence_refs. No owner modules were edited for this change.

The write tool rejects NO_ANSWER, missing/unknown policy refs, a decision inconsistent
with `calculate_claim`, and illegal StateStore transitions. This is a deterministic
safety boundary, not proof that an LLM reasoned faithfully about retrieved content.
TV2 must gate evidence before writing, invoke `get_claim_status` immediately after
successful submit, compare actual status/reason/timestamp, and fail explicitly on
mismatch. An arbitrary final model action must not be treated as verified persistence.

The fetched TV2 agent has a callable LLM port, but no real provider/retry integration
or mandatory write/read-back orchestration yet. Those remain TV2 work. This change
does not substitute a scripted model for real LLM runs or evaluation.

## TV1 evaluation

`make eval` delegates directly to the existing real retrieval evaluator. Existing
Agent evaluation contract/summary modules remain unchanged. Integration logs record
`final_agent_evaluation: false`; do not use them as real Agent benchmark answers.
The real retrieval evaluator was rerun successfully: Dense Hit@3/Recall@3 100%/100%,
Hybrid 100%/95.45% (11 answerable out of 15). Hybrid Q13 still misses DOC007 in top-3.
Final Decision Accuracy/Correct Refusal/Faithfulness and real token metrics still
need actual provider output supplied by TV2 and evaluation by TV1.

## Demo and logs

`make demo` / `make logs`: actual embeddings/retrieval, existing deterministic rules,
real MCP writes on a temporary claim copy, immediate read-back and JSON disk comparison.
`python scripts/demo_verified_audit.py --transport-only --three`: no embeddings, real
MCP/file side effects only. Run kind and zero LLM usage are explicit in every record.
The log file is written only after verification succeeds. No automatic retry of writes.

For a negative-path demo, pass an unknown claim ID: the command exits nonzero and no
successful log is written. Server-side regressions test empty evidence, unknown refs,
incorrect recommendation, terminal transitions and NO_ANSWER without disk mutation.

The server's JSON storage is safe for sequential use through one server instance;
it does not provide locking for multiple server processes sharing one state file.

## MCP defense preparation

Explain host/client/server ownership, tools/list discovery and cache refresh,
protocol-only stdout, JSON/Error observations, real file writes and why read-back
must be a separate call. Three small live-code exercises for TV3:

- Add a read tool and show that refresh discovers its schema without changing client dispatch.
- Add one write input constraint and demonstrate Error output without changing the state file.
- Extend verification with a new returned field and demonstrate an explicit mismatch failure.
