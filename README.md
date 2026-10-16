# Travel Expense Audit Agent

AIPR project: policy retrieval, deterministic expense checks, JSON claim state,
and MCP tools for travel expense auditing.

## Current scope

- RAG: document loading, chunking, dense search, BM25 and hybrid search.
- Business rules: daily/nightly limits, receipts, alcohol, submission deadline,
  international approval and transportation requirements.
- State store: allowed transitions, atomic file replacement and read-back.
- MCP: `search_policy`, `get_claim_status`, `get_claim`, `calculate_claim` are
  implemented. Claim tools delegate to TV2's registry and dispatcher.
- Read-only integration: MCP evidence feeds the existing deterministic claim
  reasoner, retaining document/version/chunk citations and checking source coverage.
- `submit_decision` (Day 5), the full Agent loop and write/read-back verification
  are pending.

## Setup on Windows (PowerShell)

Run from the repository root. Use Python 3.12 and an isolated environment so the
MSYS2 Python on PATH is not used accidentally. With uv installed:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
```

`requirements.txt` contains runtime dependencies; `requirements-dev.txt` also
installs pytest. Installation requires package-index access. The first real RAG
search downloads `sentence-transformers/all-MiniLM-L6-v2` unless cached.

## Run checks

Full suite, including the new unittest-compatible regressions:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Business/model regression checks using only the Python standard library:

```powershell
python -m unittest discover -s tests -p test_regressions.py -v
```

Use an explicit Python executable if `python` resolves to the wrong interpreter.
The state-persistence test operates on a temporary copy of the sample claims.

## MCP and retrieval

```powershell
.\.venv\Scripts\python.exe scripts\smoke_mcp_tools.py
.\.venv\Scripts\python.exe -m src.mcp_server.server
```

The smoke uses an in-process MCP client and deterministic embedding vectors. It
checks discovery/calls but does not verify subprocess stdio or real model quality.
The server command starts the real stdio endpoint; stdout is reserved for MCP.

```powershell
.\.venv\Scripts\python.exe -m evaluation.evaluate_retrieval
.\.venv\Scripts\python.exe -m evaluation.day2_reasoning_analysis
```

These evaluation commands use the real model and overwrite their corresponding
CSV reports. Stored baseline scores are historical results, not proof of a fresh
successful run. See `docs/tool_contracts.md` for MCP contracts.

## Claim data contract

See `docs/claim_format.md` before adding inputs or integrating Agent tools.
`data/claims/claims.json` contains seven synthetic examples. Their explicit daily
allocations are fixture data; the runtime never invents an equal split for a real
invoice. Sample totals and expected recommendations remain unchanged.

## Member 3 checkpoint for 14 October

The default example is one hotel night in Da Nang for 1,800,000 VND against the
1,500,000 VND limit. Expected evidence-backed decision: `ESCALATED`, including
DOC003 (hotel limit) and DOC007 (exception review), plus receipt/deadline checks.

```powershell
.\.venv\Scripts\python.exe scripts\demo_readonly_audit.py
.\.venv\Scripts\python.exe scripts\demo_readonly_audit.py --transport inprocess
.\.venv\Scripts\python.exe scripts\demo_readonly_audit.py --claim-id CLM-002
```

Both transports use real embeddings; neither silently substitutes vectors. The
stdio mode starts the server process from the repository root. The output
contains search arguments/results, complete evidence, reasoning and the final
decision. The demo verifies that the sample claim file is unchanged. Required
policy evidence that cannot be retrieved yields `NO_ANSWER`, not an unsupported
approval. Read `docs/tool_contracts.md` for the Agent handoff and limitations.

Focused tests (SDK tests require installed runtime dependencies):

```powershell
python -m unittest discover -s tests -p test_mcp_evidence.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_mcp_sdk.py -v
```

## Verification checkpoint

The merge-preparation review passed 75 pytest tests and 71 subtests using the
project Python 3.12 environment. `scripts/smoke_stdio.py` completed with `stdio OK`:
real subprocess discovery, CLM-001 read and CLM-999 error. The existing in-process
search smoke passed with deterministic embeddings and retained source metadata.

The real-embedding demo timed out after 45 seconds in this review, so its full
retrieval/reasoning result is not claimed as verified. See
`progress/2026-10-14-tv3.md` for exact commands, limitations and merge readiness.

## Day 4 registry integration

Main was merged after both TV2 and TV1. The integrated suite now passes 146 tests
and 71 subtests. Real subprocess claim-tool checks pass without a model:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_registry.py
```

Expected last line: `registry stdio OK; claim state unchanged`. This checks
discovery, full claim reads, registered calculations for all four outcomes and
safe error observations. It does not evaluate embedding quality.

The existing demo's `--claim-id` option now obtains both claim data and reasoning
through the registered MCP tools. It still needs the real embedding model for
policy retrieval. TV2 can integrate `await dispatch_mcp(...)` into the Agent loop;
see `docs/tool_contracts.md` for the handoff.

The newer plan also provides a synchronous `McpToolbox` for TV2's synchronous
Agent loop. See `docs/mcp_toolbox_handoff.md` for the `schemas()` / `call()` port,
schema conversion, cached discovery and clean connection shutdown.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_adapter.py
```

This saves complete real-stdio evidence to `evaluation/day4_adapter_smoke.json`
and finishes with `adapter stdio OK`. The expanded suite passes 177 tests and
71 subtests, including dynamic tool addition and raw server stdout inspection.

## TV3 integration and reproducible commands (16 October)

Python 3.11+ is required. From the repository root:

```bash
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
make test
make smoke
make demo
make logs
make eval
```

GNU Make is optional: run the Python command shown in each Makefile target directly
on Windows, for example `python scripts/demo_verified_audit.py --three`.
Use `make PYTHON=.venv/bin/python test` if the virtual environment is not activated.
For Linux CPU-only deployments, installing CPU PyTorch before requirements avoids
unnecessary CUDA packages: `python -m pip install torch --index-url https://download.pytorch.org/whl/cpu`.

`make demo` runs actual policy retrieval, the existing deterministic business rules,
`submit_decision`, and an immediate `get_claim_status` over a real MCP stdio subprocess.
It checks the read-back status, reason, timestamp and the actual JSON file. Missing
retrieved policy evidence stops the flow before writing. The demo makes an isolated
copy of sample claims; the tracked fixture remains unchanged and reruns are safe.
The first retrieval downloads `sentence-transformers/all-MiniLM-L6-v2`; later runs
reuse the Hugging Face cache. Downloads/network availability are cold-start prerequisites.

`make logs` generates `logs/run_01.jsonl` through `run_03.jsonl` for APPROVED,
ESCALATED and NEED_MORE_INFO. Each JSONL record contains UTC timestamp, question,
full tool arguments/results, steps, actual usage, before/after state and verification.
`--transport-only` provides a model-free transport/persistence check; such logs are
explicitly marked `transport_integration` and do not prove RAG or final Agent quality.
Both modes use deterministic reasoning, with zero LLM calls/tokens. They must not be
reported as real LLM Agent evaluation or used to invent final performance metrics.

`make eval` executes TV1's real Dense/Hybrid retrieval evaluation against
`tests/testset.jsonl`, overwriting `evaluation/results.csv` and `summary.csv` with
measured output. It does not produce Agent Decision Accuracy/Faithfulness. Those
metrics require TV2's real provider and actual Agent outputs via TV1's evaluation contract.
A model/download failure is a failed evaluation, never a cached-success substitute.

The MCP server now discovers five tools including `submit_decision`. A write requires
claim ID, persistable decision, non-empty reason and document/version evidence refs.
The server checks the existing rule recommendation, policy references and allowed
state transition before saving through TV2's StateStore. NO_ANSWER is never persisted.
The caller must immediately call `get_claim_status` and compare the returned fields.
`.env.example` documents optional environment variables; export them before starting
the server (the application does not automatically load `.env`).
