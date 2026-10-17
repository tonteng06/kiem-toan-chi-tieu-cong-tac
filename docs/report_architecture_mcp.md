# Architecture and MCP contribution for report assembly

The application separates policy retrieval (TV1), the Agent/business rules/state
store (TV2), and MCP integration/reproducible execution (TV3). The host discovers
tools dynamically with tools/list, converts their input schemas into the Agent's
schema format, and invokes tools/call through a stdio client. McpToolbox provides
the synchronous schemas()/call() interface required by the hand-written Agent loop.
A dedicated worker thread owns the asynchronous client connection and its cleanup.
Discovery is cached per session and explicitly refreshed when tools change.

The server exposes search_policy, get_claim, calculate_claim, get_claim_status and
submit_decision. Policy responses retain document ID/version, chunk ID/content,
retrieval mode and scores. Document-level evidence references use DOC003@v1.0.
Structured tool output becomes JSON text; failures become Error: observations.
Untruncated arguments, raw results and observations remain available in history.
The stdio protocol owns stdout; diagnostics are routed to stderr.

A write first validates its reason, evidence coverage and known policy versions,
checks the recommendation calculated by existing business rules, and delegates the
status transition to TV2's StateStore. The store writes a temporary JSON file and
atomically replaces its state file. NO_ANSWER is never persisted. The client then
calls get_claim_status immediately and compares claim ID, status, reason and update
time. The integration demo additionally checks the saved JSON file. Successful
submit alone is not treated as verification.

Reproducibility is provided through Makefile setup/test/smoke/demo/logs/eval targets,
README setup instructions, and an environment-variable example without credentials.
Demos use temporary state copies so repeated runs do not alter tracked sample claims.
JSONL logs contain timestamps, tool arguments/results, steps, usage and verification.
Transport-only and deterministic-retrieval integration runs are labelled explicitly;
they are not real LLM evaluation data. Final Agent metrics and measured token usage
must come from TV2 provider runs evaluated by TV1. The existing real Dense/Hybrid
retrieval evaluator is invoked directly by make eval.

The final TV2 Agent/provider branch was merged locally on 17 October. The added
demo_agent_mcp runner supplies the runtime-discovered MCP schemas to that Agent,
requires every submitted evidence reference to have been retrieved with text,
and checks the isolated JSON state after the Agent's mandatory status read-back.

Limitations: the current file store has no multi-process locking. Real provider
traces and final Agent quality/usage measurements remain pending because no key
is configured in the review session; fresh stdio acceptance is also blocked by
the review host's Windows loopback restriction. No claim about final Agent
performance follows from passing handler tests or earlier deterministic runs.
