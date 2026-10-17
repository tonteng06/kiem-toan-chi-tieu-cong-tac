# Travel Expense Audit Agent

AIPR T2: policy retrieval -> expense calculation -> evidence gate -> decision ->
persist JSON state -> immediate read-back verification. Python 3.11+ is required.

## Setup and one-command demo

Create and activate an isolated environment from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/demo_verified_audit.py
```

With uv, use `uv venv --python 3.12 .venv` and
`uv pip install --python .venv\Scripts\python.exe -r requirements.txt`.
Avoid the MSYS2 interpreter if it appears first on Windows PATH.

On Linux/macOS, use `python3 -m venv .venv` and `. .venv/bin/activate`.
With GNU Make installed and the environment activated, the required single line is:

```bash
make setup && make demo
```

The first retrieval downloads `sentence-transformers/all-MiniLM-L6-v2`. Internet
access is required unless it is cached. For an existing cache, export
`HF_HUB_OFFLINE=1`. Network/model failures are failures, never cached-success output.

`make demo` is a real RAG/MCP/file integration demo with deterministic business
reasoning and **zero LLM calls**. It is not final LLM Agent performance evidence.
The demo uses a temporary state copy, preserving `data/claims/claims.json`.

## Commands

GNU Make is optional on Windows; run the corresponding Python command directly.

| Make target | Python command | Scope |
| --- | --- | --- |
| `make test` | `python -m pytest -q` | Full regression suite |
| `make smoke` | See Makefile: three smoke commands | Discovery, reads, isolated write/read-back |
| `make demo` | `python scripts/demo_verified_audit.py` | Real retrieval + deterministic audit + MCP verify |
| `make logs` | `python scripts/demo_verified_audit.py --three` | Recreate three real integration logs |
| `make eval` | `python -m evaluation.evaluate_retrieval` | Real Dense/Hybrid evaluation |
| `make agent-demo` | `python scripts/demo_agent_mcp.py` | Real provider + manual Agent + MCP; requires API key |

## Real LLM Agent over MCP

Export `GROQ_API_KEY` in the terminal before running the real Agent. See
`.env.example` for optional model, endpoint, timeout and retry configuration.
The application does not automatically load `.env`. Do not commit credentials.

```powershell
python scripts/demo_agent_mcp.py CLM-001 CLM-002 CLM-003 --log logs/agent_mcp.jsonl
```

This runner uses TV2's `run_agent` and real provider through TV3's `McpToolbox`.
Tool schemas come from runtime discovery. It preserves the MCP contract
`submit_decision(claim_id, decision, reason, evidence_refs)`; the local registry's
three-argument write tool is a separate interface. No evidence is invented to
bridge the difference: the model must retrieve and supply the required refs.
The loop automatically reads `get_claim_status` after a successful write; the
runner also checks the isolated saved state. Missing key, provider failure or
unverified claim produces a nonzero exit code. There is no mock-model fallback.
The runner allows at most 16 model steps by default (configurable up to 32);
the Agent module's default remains 8.

`scripts/demo_agent.py` is TV2's alternative **local-registry** runner. It does
not demonstrate MCP transport. Both runners use isolated claim copies.

## Evidence and evaluation

Five MCP tools: `search_policy`, `get_claim`, `calculate_claim`,
`submit_decision`, `get_claim_status`. The stdio server reserves stdout for MCP
and sends diagnostics to stderr. Start it with `python -m src.mcp_server.server`.
Details: `docs/tool_contracts.md`, `docs/mcp_toolbox_handoff.md` and
`docs/claim_format.md`.

`make eval` rewrites `evaluation/results.csv` and `summary.csv` using the actual
embedding model and `tests/testset.jsonl`: 15 questions, including 4 no-answer
questions. Retrieval metrics use the 11 answerable questions. The 17 October
rerun measured Dense Hit@3/Recall@3 = 100%/100% and Hybrid = 100%/95.45%.
Hybrid Q13 misses DOC007 in Top-3; see `evaluation/failure_analysis.txt`.
Retrieval ranking alone cannot prove correct refusal or LLM faithfulness.

`logs/run_01.jsonl` through `run_03.jsonl` are genuine 16 October retrieval/MCP
integration runs with zero LLM usage. Keep their dates and labels intact.
`--transport-only` checks transport/persistence without embeddings. Neither
kind is final Agent evaluation. TV1's evaluation contract/metrics must consume
actual provider outputs for Decision Accuracy, Correct Refusal, Evidence Coverage
and usage; faithfulness also requires judging generated answers against evidence.
Do not fabricate these results if the provider has not run.

## Final-day status

TV2's final Agent branch was merged into TV3 locally on 17 October, restoring the
Agent API and adding provider retry/timeout, evidence gating and mandatory verify.
See `progress/2026-10-17-tv3.md` and `docs/final-review-2026-10-17.md` for measured
checks and remaining submission blockers. The current review host blocks Windows
loopback sockets used by asyncio, so a full stdio regression must be rerun in a
normal terminal. No full-suite or fresh stdio pass is claimed for that host.

Before submitting: obtain real Agent logs/metrics, assemble `report.docx` (8–9
pages), run full pytest and demo on the submission machine, review/merge branches
using merge commits, and include `.git` in the final repository. JSON state is
intended for one writer; independent servers must not share the same state file.
