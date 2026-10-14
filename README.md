# Travel Expense Audit Agent

AIPR project: policy retrieval, deterministic expense checks, JSON claim state,
and MCP tools for travel expense auditing.

## Current scope

- RAG: document loading, chunking, dense search, BM25 and hybrid search.
- Business rules: daily/nightly limits, receipts, alcohol, submission deadline,
  international approval and transportation requirements.
- State store: allowed transitions, atomic file replacement and read-back.
- MCP: `search_documents` and `get_claim_status` are implemented.
- `submit_decision`, the full Agent loop and end-to-end verification are pending.

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
.\.venv\Scripts\python.exe -m src.mcp.server
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

## Verification checkpoint

The 14 October preflight passed 32 standard-library regression tests. The full
pytest suite, MCP stdio round-trip and real embedding load remain unverified in
the restricted work environment. See `progress/2026-10-14-preflight.md` for the
exact scope and limitations.
