"""MCP -> TV2/LLM schema and observation adapters."""
from __future__ import annotations

import copy
import json
import asyncio
import atexit
import sys
import threading
import math
from concurrent.futures import Future, TimeoutError as FutureTimeout
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from mcp.types import CallToolResult, Tool
from jsonschema import Draft202012Validator

from src.agent.dispatcher import dispatch, parse_args


def _schema_without_annotations(schema: dict) -> dict:
    """Inline local references before removing definitions and schema titles.

    Property names (including a property literally named 'title'), defaults and
    descriptions are data and are preserved. Recursive/external references fail
    explicitly instead of leaving broken references in an LLM tool schema.
    """
    root = copy.deepcopy(schema)

    def clean(node, seen=()):
        if isinstance(node, list):
            return [clean(value, seen) for value in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            reference = node["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#/") or reference in seen:
                raise ValueError("unsupported recursive or external schema reference")
            target = root
            try:
                for part in reference[2:].split("/"):
                    target = target[part.replace("~1", "/").replace("~0", "~")]
            except (KeyError, TypeError) as exc:
                raise ValueError(f"unresolved schema reference {reference}") from exc
            resolved = clean(target, (*seen, reference))
            siblings = clean({k: v for k, v in node.items() if k != "$ref"}, seen)
            return {"allOf": [resolved, siblings]} if siblings else resolved
        result = {}
        for key, value in node.items():
            if key in {"title", "$defs", "definitions", "$schema"}:
                continue
            if key in {"properties", "patternProperties", "dependentSchemas"}:
                result[key] = {name: clean(child, seen) for name, child in value.items()}
            elif key in {"default", "examples", "enum", "const"}:
                result[key] = copy.deepcopy(value)
            else:
                result[key] = clean(value, seen)
        return result

    return clean(root)


def mcp_tool_to_llm_schema(tool: Tool | Mapping) -> dict:
    """Return TV2's {name, description, input_schema} shape, without mutation."""
    if isinstance(tool, Mapping):
        name, description = tool.get("name"), tool.get("description")
        schema = tool.get("input_schema", tool.get("inputSchema"))
    else:
        name, description = tool.name, tool.description
        schema = getattr(tool, "input_schema", None)
        if schema is None:
            schema = getattr(tool, "inputSchema", None)
    if not isinstance(name, str) or not name.strip() or not isinstance(schema, dict):
        raise ValueError("MCP tool requires a name and input schema")
    if description is not None and not isinstance(description, str):
        raise ValueError("MCP tool description must be a string")
    return {"name": name, "description": description or "", "input_schema": _schema_without_annotations(schema)}


def mcp_tool_to_openai_schema(tool: Tool | Mapping) -> dict:
    schema = mcp_tool_to_llm_schema(tool)
    return {"type": "function", "function": {
        "name": schema["name"], "description": schema["description"],
        "parameters": schema["input_schema"],
    }}


def error_observation(message: object) -> str:
    text = str(message)
    if text.startswith("Error:"):
        text = text[len("Error:"):].lstrip()
    return "Error: " + text


def normalize_result(result: CallToolResult) -> str:
    """Always JSON success text or Error: text; never throw an ordinary error.

    Structured content wins. Text blocks are joined without truncation: JSON is
    re-encoded, plain text becomes a JSON string, malformed JSON-looking text
    is an error. Raw SDK content is retained separately by the toolbox history.
    """
    try:
        text = "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")
        if result.is_error:
            message = text or json.dumps(result.structured_content, ensure_ascii=False, allow_nan=False)
            return error_observation(message)
        if result.structured_content is not None:
            return json.dumps(result.structured_content, ensure_ascii=False, allow_nan=False)
        if not text:
            return json.dumps(None)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            if text.lstrip().startswith(("{", "[", '"')):
                return error_observation("tool returned malformed JSON text")
            payload = text
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        return error_observation(exc)


class LocalToolbox:
    """The same synchronous port for TV2's unchanged local ToolRegistry."""

    def __init__(self, registry):
        self.registry = registry

    def schemas(self):
        return self.registry.schemas()

    def call(self, name, args=None):
        return dispatch(self.registry, name, args)


class McpToolbox:
    """Synchronous schemas()/call() facade backed by one async worker session.

    Use as a context manager. Discovery is cached until explicit refresh().
    Calls are serialized in the owner task, keeping SDK context/cancel scopes on
    the same task. This also works when the caller already has an asyncio loop.
    `history` retains complete arguments, raw SDK results and observations.
    """

    def __init__(self, command=None, args=None, *, cwd=None, timeout=30.0, connection_factory=None):
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive")
        self.command = command or sys.executable
        self.args = list(args) if args is not None else ["-m", "src.mcp_server.server"]
        self.cwd = str(cwd or Path(__file__).resolve().parents[2])
        self.timeout = float(timeout)
        self._factory = connection_factory
        self._lock = threading.RLock()
        self._thread = None
        self._loop = None
        self._owner = None
        self._queue = None
        self._closed = True
        self._tools = {}
        self._schemas = []
        self._validators = {}
        self._history = []
        self.discovery_count = 0

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def open(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                if self._closed:
                    raise RuntimeError("Error: previous MCP connection is still closing")
                ready = self._ready
            else:
                self._closed = False
                self._loop = self._owner = self._queue = None
                self._ready = ready = Future()
                self._thread = threading.Thread(target=self._run_worker, name="McpToolbox", daemon=True)
                self._thread.start()
                atexit.register(self.close)
        try:
            ready.result(timeout=self.timeout)
        except Exception as exc:
            self.close()
            raise RuntimeError(error_observation(f"MCP connection/discovery failed: {exc}")) from exc
        return self

    def _run_worker(self):
        try:
            asyncio.run(self._serve())
        except BaseException as exc:
            if not self._ready.done():
                self._ready.set_exception(exc if isinstance(exc, Exception) else RuntimeError(str(exc)))
        finally:
            with self._lock:
                self._closed = True
            if self._queue is not None:
                while not self._queue.empty():
                    _, _, pending = self._queue.get_nowait()
                    if not pending.done():
                        pending.set_exception(RuntimeError("MCP connection closed"))

    async def _serve(self):
        from src.mcp_server.client import connect
        self._loop = asyncio.get_running_loop()
        self._owner = asyncio.current_task()
        self._queue = asyncio.Queue()
        connection = self._factory() if self._factory else connect(self.command, self.args, cwd=self.cwd)
        async with connection as client:
            await asyncio.wait_for(self._discover(client), timeout=self.timeout)
            self._ready.set_result(None)
            while True:
                operation, arguments, future = await self._queue.get()
                if operation == "close":
                    if not future.done():
                        future.set_result(None)
                    break
                if future.cancelled():
                    continue
                try:
                    if operation == "refresh":
                        value = await asyncio.wait_for(self._discover(client), timeout=self.timeout)
                    else:
                        name, args = arguments
                        response = await asyncio.wait_for(client.call_tool(name, args), timeout=self.timeout)
                        value = normalize_result(response)
                        self._record(name, args, response.model_dump(mode="json", by_alias=True), value)
                    if not future.done():
                        future.set_result(value)
                except Exception as exc:
                    if operation == "call":
                        name, args = arguments
                        detail = f"MCP call timed out after {self.timeout:g}s" if isinstance(exc, TimeoutError) else str(exc)
                        value = error_observation(detail)
                        self._record(name, args, None, value)
                        if not future.done():
                            future.set_result(value)
                    elif not future.done():
                        future.set_exception(exc)

    async def _discover(self, client):
        from src.mcp_server.client import discover_tools
        tools = await discover_tools(client, refresh=True)
        schemas = [mcp_tool_to_llm_schema(tool) for tool in tools]
        names = [schema["name"] for schema in schemas]
        if len(names) != len(set(names)):
            raise ValueError("duplicate MCP tool names")
        validators = {}
        for schema in schemas:
            Draft202012Validator.check_schema(schema["input_schema"])
            validators[schema["name"]] = Draft202012Validator(schema["input_schema"])
        with self._lock:
            self._tools = dict(zip(names, tools))
            self._schemas = schemas
            self._validators = validators
            self.discovery_count += 1
        return self.schemas()

    def schemas(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._schemas)

    @property
    def history(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._history)

    def _record(self, name, args, raw_result, observation):
        try:
            saved_args = copy.deepcopy(args)
        except Exception:
            saved_args = "<non-copyable invalid arguments>"
        with self._lock:
            self._history.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": name if isinstance(name, str) else "<invalid name>", "args": saved_args, "raw_result": raw_result,
                "observation": observation})

    def _submit(self, operation, arguments=None):
        with self._lock:
            if self._closed or self._thread is None or not self._thread.is_alive():
                raise RuntimeError("MCP toolbox is closed")
            loop, queue = self._loop, self._queue
        future = Future()
        loop.call_soon_threadsafe(queue.put_nowait, (operation, arguments, future))
        try:
            return future.result(timeout=self.timeout + 2)
        except FutureTimeout as exc:
            future.cancel()
            raise TimeoutError(f"MCP operation timed out after {self.timeout:g}s") from exc

    def refresh(self) -> list[dict]:
        return self._submit("refresh")

    def call(self, name, args=None) -> str:
        try:
            if not isinstance(name, str):
                raise ValueError("tool name must be a string")
            arguments = copy.deepcopy(parse_args(args))
            with self._lock:
                validator = self._validators.get(name)
            if validator is None:
                raise ValueError(f"unknown MCP tool {name!r}; call refresh() for new tools")
            validator.validate(arguments)
            return self._submit("call", (name, arguments))
        except Exception as exc:
            observed = error_observation(exc)
            self._record(name, args, None, observed)
            return observed

    def close(self):
        with self._lock:
            thread, loop, queue, owner = self._thread, self._loop, self._queue, self._owner
            self._closed = True
        if thread is None or not thread.is_alive() or threading.current_thread() is thread:
            atexit.unregister(self.close)
            return
        if loop is not None and queue is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(queue.put_nowait, ("close", None, Future()))
            except RuntimeError:
                pass
        thread.join(timeout=self.timeout)
        if thread.is_alive() and loop is not None and not loop.is_closed() and owner is not None:
            loop.call_soon_threadsafe(owner.cancel)
            thread.join(timeout=2)
        atexit.unregister(self.close)
