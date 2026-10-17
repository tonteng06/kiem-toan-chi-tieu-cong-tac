# Progress 2026-10-12

## Member 1 - Data / RAG / Evaluation

Done:
- Added 8 policy documents, metadata, loader, chunker, dense retrieval, BM25,
  hybrid retrieval, and a unified `Retriever` interface.
- Expanded the testset to 15 questions, including 4 no-answer cases and Q13-Q15
  reasoning cases; ran dense and hybrid retrieval evaluation.
- Dense: Hit@3 100%, Recall@3 100%. Hybrid: Hit@3 100%, Recall@3 95.45%.
- Recorded the Q13 hybrid miss for DOC007 in the failure analysis.

Source branch: `member1-rag-eval`.

## Member 2 - Agent / Business Logic

Done:
- Added typed `Claim` and `Expense` models, claim statuses and allowed state
  transitions, plus 7 sample claims.
- Added claim-model tests on `feature/agent-tools`.
- Identified tool-boundary questions for `calculate_claim`, `get_claim`,
  `get_claim_status`, and `submit_decision`.

Source branch: `feature/agent-tools`.

## Member 3 - MCP / Integration

Done:
- Added MCP server and stdio client skeletons on `member3-mcp`.
- Added dynamic `tools/list` discovery and name-based tool calls.
- Drafted typed request/response contracts and `docs/tool_contracts.md`.
- Combined MCP and RAG dependencies in `requirements.txt` for later branch
  integration.

Test:
- Not run during this implementation pass.

Problem:
- Confirm whether `NO_ANSWER` maps to the claim status `NEED_MORE_INFO`, and
  whether `calculate_claim` and `get_claim` should be MCP tools or internal
  Agent/business-logic functions.

Next:
- Implement `search_policy` and `get_claim_status` after the group confirms
  the contracts; add `submit_decision` with real persistence and read-back
  verification at the planned checkpoint.

Commit:
- `4970` Add MCP server and client skeleton (present on `origin/member3-mcp`).

## Integration status

- RAG <-> Agent: not integrated.
- Agent <-> MCP: skeleton and contract draft only.
- Write <-> verify: pending implementation.
- Evaluation: member 1's retrieval baseline is recorded on their branch.
- Blocker: confirm tool ownership and the `NO_ANSWER` / `NEED_MORE_INFO`
  mapping.


## Day 4 update - 2026-10-15

- Main containing TV1 and TV2 was merged as bd9cee8; tests and real stdio pass.
- The server exposes four read tools and delegates claim calls to TV2's registry.
- adapters.McpToolbox supplies the synchronous schemas()/call() port; an owned
  worker thread runs one MCP session, discovers once and refreshes explicitly.
- Full schema/result adapters and untruncated history are implemented. Existing
  async helpers also cache discovery per client.
- Handoff for TV2: docs/mcp_toolbox_handoff.md. The owner has not yet confirmed
  wiring this port into the full Agent loop; no such confirmation is invented.
- Written TV2 confirmation/date for earlier edits to its files remains pending.
- TV1's new canonical RetrievedChunk/evidence_ref module is not on the merged
  main snapshot yet. Update the serialization boundary to import it when ready;
  do not define a duplicate canonical chunk reference in TV3.
- Day 5 remains: integrate Agent action gating, submit_decision and read-back
  verification. Real embedding/LLM quality and end-to-end writes are not claimed
  by the passing adapter smoke.
- The new plan requires the above owner confirmations before marking merge/PR
  readiness complete. No new PR or remote merge is claimed here.

## TV3 16 October revised schedule

Main efc683b was merged locally into member3-mcp without conflicts (078d03e).
The missing write tool is now implemented using the existing StateStore/rules;
read-back is a separate immediate MCP call and the demo checks the file as well.
See docs/tv3-day6-handoff.md and progress/2026-10-16-tv3.md for scope and verification.
The three committed logs now contain real MiniLM retrieval + deterministic rules +
MCP/file integration, with zero LLM calls; they are not final LLM Agent evaluation.
Actual make eval passed: Dense Hit@3/Recall@3 100%/100%; Hybrid 100%/95.45%.
Full test checkpoint: 218 passed, 71 subtests passed. Real provider/Agent evaluation
and written owner acceptance remain pending; existing historical notes above are
checkpoints, not claims that these newer requirements are complete.

## Final-day update — 2026-10-17

The final TV2 branch (5696422) was merged locally as 31b27df. TV3 implementation
1d8ca46 connects its real provider/manual loop to dynamically discovered MCP
tools, preserving the evidence_refs write contract. A boundary gate checks that
all submitted refs were actually retrieved with text. Five new handler/boundary
regressions pass. No owner-confirmation date is inferred or invented.

Measured selection: 236 tests + 71 subtests passed, 21 host-loopback-dependent
checks excluded. Actual retrieval eval again measured Dense 100%/100% and Hybrid
100%/95.45% Hit@3/Recall@3. Full suite, fresh stdio, cold-start installation and
real provider runs are not certified in this host. report.docx and final Agent
quality/usage metrics remain absent. See docs/final-review-2026-10-17.md and
evaluation/day7_validation.json. This update supersedes earlier pending-code
statements but does not replace missing acceptance evidence.
