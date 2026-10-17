# Day 4 MCP toolbox handoff to TV2

The Agent can use a synchronous `schemas()` / `call(name, args)` port without
running an event loop itself. The MCP connection lives in one worker thread;
the SDK connection context is entered and closed in the same owning task.

```python
from src.mcp_server.adapters import McpToolbox

with McpToolbox() as tools:
    observation = tools.call("get_claim_status", {"claim_id": "CLM-001"})
```

Use `tools.schemas()` as the LLM's tool definitions. Each entry has exactly
`name`, `description`, `input_schema`, matching TV2's `Tool.schema()` port.
After the model selects a tool, pass its name and argument dict/JSON string to
`tools.call`. The observation is JSON text on success or starts with `Error: `.
If retaining TV2's local tools, wrap the registry with `LocalToolbox(registry)`;
it exposes the same two methods and delegates to the existing dispatcher.

## Discovery and schema behavior

- Connection startup lists tools once. `schemas()` and repeated `call()` do not
  list again. `refresh()` explicitly updates the cache after server tool changes.
- Names are discovered, not hard-coded. The current server advertises
  `search_policy`, `get_claim_status`, `get_claim`, `calculate_claim`.
- `query` is required for search; `mode` and `top_k` remain optional with their
  existing `hybrid` / `3` defaults. All original constraints are retained.
- Schema titles are removed, local `$ref` definitions are inlined before `$defs`
  is removed. Property names and default values are preserved. Recursive,
  unresolved or external references fail explicitly during discovery.
- `mcp_tool_to_openai_schema` offers the optional function/parameters wrapper.
- The legacy async helpers also cache per client; call
  `await discover_tools(client, refresh=True)` to explicitly rediscover.

## Calls, errors and lifetime

`McpToolbox.call` validates arguments against the discovered JSON schema, catches
ordinary validation/transport/tool/timeout errors, and returns an `Error: `
observation. Calls run in order and are not retried. `normalize_result` prefers
structured content and preserves Unicode. For text-only responses, blocks are
joined; valid JSON is re-encoded, plain text becomes a JSON string, and malformed
JSON-looking text is reported as an error.

`history` retains full arguments, the complete SDK result (protocol aliases),
and the observation for later JSONL logging. There is no text truncation.
Errors before a server response have `raw_result: null`. History is in memory;
the smoke script saves it explicitly as reproducible evidence.

Use `with McpToolbox(...)` so cleanup runs on normal return and caller errors.
The connection closes before the worker finishes. A stopped server is an error
observation; it does not trigger an implicit reconnect or retry. Startup/discovery
failure and explicit `refresh()` failure raise to their caller; tool `call()`
failures are observations. The default timeout is 30 seconds and is configurable.

## Reproduce from the repository root

With the project environment installed and activated, all paths are relative:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/smoke_adapter.py
python scripts/smoke_stdio.py
```

On Windows without activation, replace `python` with
`.\.venv\Scripts\python.exe`. No developer-specific absolute path is needed.
If the host's default temporary directory is restricted, set `TMPDIR` to an
existing writable temp directory and supply a fresh `--basetemp` to pytest.

Observed: 177 pytest tests and 71 subtests passed; adapter smoke completed with
`adapter stdio OK`. Full smoke evidence is `evaluation/day4_adapter_smoke.json`.
The suite includes real server discovery after adding a new tool, raw stdout
JSON-RPC inspection, an actual subprocess crash and clean worker shutdown.

## Items requiring owner confirmation

- The synchronous facade matches TV2's currently synchronous dispatcher. TV2
  still needs to confirm using this port in its actual Agent loop; that loop
  has not been edited or claimed as integrated in this checkpoint.
- TV2's written confirmation/date for the earlier model/rule/sample changes is
  still blank in `progress/2026-10-14-tv3.md`. Do not invent that date.
- TV1 has not yet landed `src/rag/provenance.py` on the merged main snapshot.
  Once TV1 publishes the shared `RetrievedChunk` and chunk-level `evidence_ref`,
  import that implementation at the server serialization boundary. Do not
  create a second canonical formatter in TV3. Existing document-level policy
  references in the rule checker remain distinct from chunk-level citations.
- Day 5: expose the write tool, enforce decision/evidence conditions and verify
  persisted state immediately after writing. No write tool is exposed today.
