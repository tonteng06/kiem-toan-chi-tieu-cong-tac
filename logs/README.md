# Run evidence

run_01.jsonl, run_02.jsonl and run_03.jsonl are actual policy-retrieval/MCP subprocess
runs, not mocked outputs. They load the real MiniLM embedding model, retrieve
policy chunks, apply TV2's deterministic business rules, write JSON state and
immediately read get_claim_status back, with a second disk check. Each uses an
isolated copy of the sample claims. Outcomes: APPROVED, ESCALATED, NEED_MORE_INFO.

Each record includes timestamps, question, complete tool arguments/raw results,
steps, usage, before/after state and VERIFY SUCCESS. The run_kind is
retrieval_deterministic_integration, llm_used is false, and LLM usage is zero.
These runs prove RAG/MCP/file integration; they do not establish final LLM Agent
Decision Accuracy, Correct Refusal or Faithfulness.

Recreate with `make logs` or `python scripts/demo_verified_audit.py --three`.
After the model is cached, `HF_HUB_OFFLINE=1 make logs` avoids network access.
The committed run_01..03 were generated with this cached real model command.
A missing-evidence/download failure stops before writing and does not create a
successful replacement log. demo.jsonl is the online cold-start retrieval demo.

transport_smoke.jsonl is a separate, model-free transport/persistence check from
`make smoke`, explicitly marked transport_integration. To reproduce that scope:
`python scripts/demo_verified_audit.py --transport-only`.

Actual LLM Agent logs still require TV2's provider. Never relabel these runs or
invent token usage/final performance metrics from deterministic integration.
