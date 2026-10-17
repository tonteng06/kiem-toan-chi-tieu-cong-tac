# Final-day review — 17 October 2026

**Submission readiness: incomplete.** TV3 integration changes are committed locally,
but real Agent evidence, the report and unrestricted-machine acceptance are still required.
Machine-readable evidence: `evaluation/day7_validation.json`.

## Changes and ownership

- Local merge 31b27df incorporates TV2's final Agent branch (5696422 / ba46362), resolving the missing manual Agent API. TV2 code was integrated from its branch, not rewritten.
- TV3 implementation 1d8ca46 adds the real Agent/MCP runner and five boundary regressions, plus updated README/Makefile/environment example.
- MCP retains `submit_decision(claim_id, decision, reason, evidence_refs)`. The local registry uses three arguments; these interfaces must not be conflated. Runtime discovery supplies the real MCP schema to the model.
- The runner requires every write citation to have been actually retrieved with text, in addition to TV2's evidence gate and the server's policy/rule/state validation. It never manufactures missing citations.

## Measured checklist

| Requirement | Finding |
| --- | --- |
| Python 3.11+ | Review interpreter 3.12.14 |
| Dense + Hybrid | Real cached-model rerun passed on 15 questions |
| Testset >=12, no_answer >=4 | 15 / 4 |
| Retrieval metrics | Dense Hit@3/Recall@3 100%/100%; Hybrid 100%/95.45%, on 11 answerable questions |
| Failure analysis | Q13 retained: Hybrid lacks DOC007, recall 0.5 |
| Regression | 236 passed + 71 subtests; 21 loopback-dependent checks excluded only in the command |
| Agent -> MCP write contract | Four handler-level integration regressions pass; scripted LLM/retrieval |
| Fresh stdio discovery/write/verify | Blocked in this host; not certified |
| Existing >=3 real JSONL runs | Three 16 October retrieval/deterministic/MCP runs validated; all zero LLM tokens |
| Real LLM Agent run/usage | Not run: no provider configuration |
| Final Agent metrics / faithfulness | Pending actual outputs; no values invented |
| Cold-start copy/venv | Copy and fresh venv succeeded; requirements install did not |
| Dependency resolution | Host index cannot resolve mcp>=2,<3; installed working SDK is 2.3.0 |
| README / Makefile / .env.example / ai-usage | Updated; real Agent command included |
| report.docx | Missing in this repository |
| Secret checks | No tracked .env or common token-pattern matches; limited scan only |
| Claim fixture / evaluation CSV integrity | Unchanged after review and real evaluation rerun |
| .git / contributions | Present; local history retains all three members and prior Codex-assisted commits |
| Remote/main status | Fetch blocked; no push/PR/main merge performed |

## Environment failures, distinguished from project results

Full pytest first exposed the obsolete Agent implementation; merging TV2 resolved
that code blocker. The next adapter test timed out. A separate five-second probe
running only `asyncio.run(asyncio.sleep(0))` hung in Windows
`socket._fallback_socketpair -> accept`. This isolates an event-loop/loopback
restriction independent of the application. Do not weaken tests or alter production
socket behavior to turn this into a passing result.

Git clone attempts also failed inside Git's MSYS runtime (`NtCreateDirectoryObject`,
access denied), so tracked files were copied instead. A fresh standard venv was
created; pip could not find a compatible MCP distribution in the index accessible
from this host. This does not establish whether the same package is available in
the submission machine's configured index. Confirm it before claiming cold-start.

## Acceptance commands on the submission machine

From the repo root with a clean Python 3.12 venv activated, install requirements,
then run each command in order and inspect its exit code:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/smoke_stdio.py
python scripts/smoke_registry.py
python scripts/demo_verified_audit.py
python scripts/demo_verified_audit.py --three
python -m evaluation.evaluate_retrieval
```

With GNU Make, equivalent targets are `make setup`, `make test`, `make smoke`,
`make demo`, `make logs`, `make eval`. A single initial setup/demo command is
`make setup && make demo` in a shell supporting `&&`.

Configure the provider key locally as an exported environment variable (do not
paste it into project files or logs), then create separate real Agent/MCP logs:

```powershell
python scripts/demo_agent_mcp.py CLM-001 --log logs/agent_run_01.jsonl
python scripts/demo_agent_mcp.py CLM-002 --log logs/agent_run_02.jsonl
python scripts/demo_agent_mcp.py CLM-003 --log logs/agent_run_03.jsonl
```

These commands must actually succeed with VERIFY SUCCESS and disk_verified=true.
The runner exits nonzero for a failed/unverified claim and never falls back to a
mock model. Keep failure logs as failures. TV1 must separately evaluate actual
Agent responses for all required cases, including Q09–Q12 no_answer; these three
claim demos alone do not measure refusal or faithfulness.

## Before submission

1. Resolve dependency installation and get a full pytest/stdio acceptance pass on the submission machine.
2. Run the real provider; hand actual Agent outputs/usage to TV1 for final evaluation and faithfulness review.
3. Assemble report.docx (8–9 pages), including Architecture/MCP text, a real trace, measured results, limitations and all members' contribution hashes. Cross-check against saved CSV/JSONL outputs.
4. Fetch current remote refs; review and merge stable PRs using merge commits, push main, check git status, and submit with `.git`. No force push or fabricated attribution.

TV3 defense focus: explain dynamic discovery, schema normalization, stdio stdout
discipline, actual JSON side effects, evidence gating and the mandatory separate
read-back. Be able to change a tool contract and its validation/test directly.


## Post-review acceptance — 18 October 2026

This section supersedes the incomplete status above while preserving the
17 October review as historical evidence.

- Remote `main` was successfully fetched and merged on the submission Mac.
- Full regression on merged `main`: **257 passed, 71 subtests passed**.
- MCP stdio discovery passed with all five tools.
- Registry smoke passed, including expected error observations.
- Deterministic MCP write/read-back demo finished with `VERIFY SUCCESS` and
  `disk_verified=true`.
- Retrieval rerun: Dense Hit@3/Recall@3 = 100%/100%; Hybrid = 100%/95.45%.
- Claim grounding: Dense and Hybrid = **6/6 issues grounded, 100% Grounding@3**.
- Real claim-Agent evaluation from `logs/agent_run_01.jsonl`:
  Decision Accuracy = **100% (4/4)**, Evidence Coverage = **100%**
  on 3 evidence-scored cases, and 4/4 writes verified.
- Real Correct Refusal evaluation from `logs/agent_run_04.jsonl`:
  **100% (4/4)** for Q09-Q12.
- Manual material-faithfulness review: 4/4 claim conclusions supported;
  CLM-006 contains one minor lexical translation issue that does not affect
  the decision.
- `make eval` now reproduces retrieval, grounding, claim-Agent metrics and
  Correct Refusal summaries.
- Secret scan found no tracked Groq key after `.env.example` was cleaned.
- `report.docx` remains the final submission artifact to assemble after these
  measured results are frozen.
