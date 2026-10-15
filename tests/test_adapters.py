"""MCP schema/result adapters: no embedding model required."""
import copy
import json

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from src.mcp_server.adapters import mcp_tool_to_llm_schema, mcp_tool_to_openai_schema, normalize_result
from src.mcp_server.adapters import McpToolbox, LocalToolbox
from contextlib import asynccontextmanager
import asyncio
from types import SimpleNamespace


def search_tool():
    return Tool(name="search_policy", description="Search policies", input_schema={
        "type": "object", "title": "SearchInput", "properties": {
            "query": {"type": "string", "title": "Query"},
            "mode": {"type": "string", "enum": ["dense", "hybrid"], "default": "hybrid"},
            "top_k": {"type": "integer", "default": 3},
        }, "required": ["query"],
    })


def test_schema_keeps_required_optional_defaults_and_does_not_mutate():
    tool = search_tool()
    before = copy.deepcopy(tool.input_schema)
    converted = mcp_tool_to_llm_schema(tool)
    assert set(converted) == {"name", "description", "input_schema"}
    schema = converted["input_schema"]
    assert schema["required"] == ["query"]
    assert schema["properties"]["mode"]["default"] == "hybrid"
    assert schema["properties"]["top_k"]["default"] == 3
    assert "title" not in schema and "title" not in schema["properties"]["query"]
    assert tool.input_schema == before


def test_alias_input_schema_and_openai_conversion():
    tool = {"name": "new_tool", "description": None, "inputSchema": {"type": "object"}}
    assert mcp_tool_to_llm_schema(tool)["description"] == ""
    converted = mcp_tool_to_openai_schema(tool)
    assert converted["type"] == "function"
    assert converted["function"]["name"] == "new_tool"
    assert converted["function"]["parameters"] == {"type": "object"}


def test_inline_defs_without_losing_property_named_title_or_default_data():
    schema = {"type": "object", "$defs": {"Choice": {"type": "string", "enum": ["a", "b"]}},
              "properties": {"title": {"$ref": "#/$defs/Choice"}, "data": {"type": "object", "default": {"title": "Keep"}}}}
    actual = mcp_tool_to_llm_schema({"name": "choice", "inputSchema": schema})["input_schema"]
    assert "$defs" not in actual
    assert actual["properties"]["title"] == {"type": "string", "enum": ["a", "b"]}
    assert actual["properties"]["data"]["default"] == {"title": "Keep"}


@pytest.mark.parametrize("reference", ["https://example.test/schema", "#/$defs/Absent", "#/$defs/Loop"])
def test_invalid_or_recursive_ref_is_explicit_error(reference):
    schema = {"$defs": {"Loop": {"$ref": "#/$defs/Loop"}}, "$ref": reference}
    with pytest.raises(ValueError):
        mcp_tool_to_llm_schema({"name": "bad", "inputSchema": schema})


def test_normalize_prefers_structured_and_keeps_unicode():
    result = CallToolResult(structured_content={"city": "\u0110\u00e0 N\u1eb5ng"}, content=[TextContent(type="text", text="ignored")])
    observed = normalize_result(result)
    assert json.loads(observed) == result.structured_content
    assert "\\u" not in observed


def test_normalize_joins_text_blocks_and_preserves_full_plain_text():
    text = "a" * 12_000
    result = CallToolResult(content=[TextContent(type="text", text=text), TextContent(type="text", text="tail")])
    assert json.loads(normalize_result(result)) == text + "\ntail"


def test_normalize_valid_json_text():
    result = CallToolResult(content=[TextContent(type="text", text='{"status":"SUBMITTED"}')])
    assert json.loads(normalize_result(result)) == {"status": "SUBMITTED"}


@pytest.mark.parametrize("text", ["missing claim", "Error: missing claim", "Error:missing claim"])
def test_normalize_errors_have_exact_prefix(text):
    result = CallToolResult(is_error=True, content=[TextContent(type="text", text=text)])
    assert normalize_result(result) == "Error: missing claim"


def test_normalize_bad_json_bad_structure_and_empty_result_never_crash():
    bad = CallToolResult(content=[TextContent(type="text", text="{broken")])
    assert normalize_result(bad).startswith("Error: ")
    assert normalize_result(object()).startswith("Error: ")
    assert normalize_result(CallToolResult(content=[])) == "null"


def test_normalize_nonfinite_json_is_error():
    result = CallToolResult(content=[], structured_content={"score": float("nan")})
    assert normalize_result(result).startswith("Error: ")


@pytest.fixture
def fake_connection():
    class FakeClient:
        def __init__(self):
            self.list_count = self.call_count = self.opens = self.closes = 0
            self.tools = [search_tool()]
            self.failure = None
            self.delay = 0
        async def list_tools(self):
            self.list_count += 1
            if self.failure == "list":
                raise OSError("server unavailable")
            return SimpleNamespace(tools=self.tools)
        async def call_tool(self, name, args):
            self.call_count += 1
            if self.failure == "call":
                raise OSError("server disconnected")
            if self.delay:
                await asyncio.sleep(self.delay)
            return CallToolResult(content=[], structured_content={"name": name, "args": args, "long": "x" * 12_000})
    client = FakeClient()
    @asynccontextmanager
    async def connect():
        client.opens += 1
        try:
            yield client
        finally:
            client.closes += 1
    return client, connect


def test_toolbox_connects_lists_once_and_preserves_optional_defaults(fake_connection):
    client, connect = fake_connection
    with McpToolbox(connection_factory=connect, timeout=2) as box:
        first = box.schemas()
        assert first[0]["input_schema"]["required"] == ["query"]
        first.clear()
        assert box.schemas()
        for _ in range(3):
            assert json.loads(box.call("search_policy", {"query": "hotel"}))["args"] == {"query": "hotel"}
        assert client.list_count == box.discovery_count == 1
        assert client.opens == 1
        assert len(box.history[-1]["raw_result"]["structuredContent"]["long"]) == 12_000
    assert client.closes == 1
    assert not box._thread.is_alive()
    assert box.call("search_policy", {"query": "hotel"}).startswith("Error: ")
    box.close()  # idempotent


@pytest.mark.parametrize("args", ["{bad", [], {"query": 123}, {"query": "x", "top_k": True}, {}, {"query": "x", "mode": "wrong"}])
def test_toolbox_bad_args_are_error_observations_without_io(fake_connection, args):
    client, connect = fake_connection
    with McpToolbox(connection_factory=connect) as box:
        assert box.call("search_policy", args).startswith("Error: ")
        assert client.call_count == 0


def test_toolbox_unknown_tool_and_explicit_refresh(fake_connection):
    client, connect = fake_connection
    with McpToolbox(connection_factory=connect) as box:
        client.tools = [*client.tools, Tool(name="late_tool", input_schema={"type": "object"})]
        assert box.call("late_tool", {}).startswith("Error: ")
        assert client.call_count == 0
        box.refresh()
        assert client.list_count == box.discovery_count == 2
        assert json.loads(box.call("late_tool", {}))["name"] == "late_tool"


def test_toolbox_server_failure_is_error_and_keeps_raw_history(fake_connection):
    client, connect = fake_connection
    with McpToolbox(connection_factory=connect) as box:
        client.failure = "call"
        assert box.call("search_policy", {"query": "x"}) == "Error: server disconnected"
        assert box.history[-1]["raw_result"] is None


def test_toolbox_timeout_does_not_retry(fake_connection):
    client, connect = fake_connection
    with McpToolbox(connection_factory=connect, timeout=0.15) as box:
        client.delay = 1
        assert "timed out" in box.call("search_policy", {"query": "x"})
        assert client.call_count == 1
    assert client.closes == 1
    assert not box._thread.is_alive()


def test_failed_start_closes_connection(fake_connection):
    client, connect = fake_connection
    client.failure = "list"
    box = McpToolbox(connection_factory=connect, timeout=1)
    with pytest.raises(RuntimeError, match="connection/discovery failed"):
        box.open()
    assert client.closes == 1
    assert not box._thread.is_alive()


def test_toolbox_can_be_called_while_caller_has_asyncio_loop(fake_connection):
    _, connect = fake_connection
    async def caller():
        with McpToolbox(connection_factory=connect) as box:
            assert json.loads(box.call("search_policy", {"query": "x"}))["name"] == "search_policy"
    asyncio.run(caller())


def test_real_server_discovers_late_tool_after_refresh_without_client_changes():
    from mcp import Client
    from mcp.server import MCPServer
    server = MCPServer("dynamic-discovery-test")
    @server.tool()
    def early(value: str) -> dict:
        return {"value": value}
    with McpToolbox(connection_factory=lambda: Client(server), timeout=5) as box:
        assert {s["name"] for s in box.schemas()} == {"early"}
        @server.tool()
        def late(value: int = 3) -> dict:
            return {"value": value}
        assert box.call("late", {}).startswith("Error: ")
        box.refresh()
        assert {s["name"] for s in box.schemas()} == {"early", "late"}
        assert json.loads(box.call("late", {})) == {"value": 3}
        assert box.discovery_count == 2
    assert not box._thread.is_alive()


def test_local_toolbox_uses_same_port_as_remote():
    from src.agent.tool_registry import build_registry
    with McpToolbox(timeout=10) as remote:
        local = LocalToolbox(build_registry())
        assert json.loads(local.call("get_claim_status", {"claim_id": "CLM-001"})) == json.loads(remote.call("get_claim_status", {"claim_id": "CLM-001"}))
        assert all(set(s) == {"name", "description", "input_schema"} for s in remote.schemas())
    assert not remote._thread.is_alive()


def test_async_client_call_tool_caches_discovery_and_can_refresh(fake_connection):
    from src.mcp_server.client import call_tool, discover_tools
    client, _ = fake_connection
    async def run():
        await call_tool(client, "search_policy", {"query": "a"})
        await call_tool(client, "search_policy", {"query": "b"})
        assert client.list_count == 1
        await discover_tools(client, refresh=True)
        assert client.list_count == 2
    asyncio.run(run())


def test_real_stdio_server_crash_returns_error_without_retry(tmp_path):
    server_script = tmp_path / "crash_server.py"
    server_script.write_text('''import os
from mcp.server import MCPServer
server = MCPServer("crash-check")
@server.tool()
def crash() -> dict:
    os._exit(7)
server.run(transport="stdio")
''', encoding="utf-8")
    with McpToolbox(args=[str(server_script)], timeout=3) as box:
        assert box.call("crash", {}).startswith("Error: ")
        assert len(box.history) == 1
    assert not box._thread.is_alive()


def test_real_stdio_server_stdout_contains_only_json_rpc():
    """Inspect raw stdout, not the SDK decoder, so stray print() is detected."""
    import queue
    import subprocess
    import sys
    import threading
    from pathlib import Path
    from mcp.types import LATEST_PROTOCOL_VERSION

    root = Path(__file__).parents[1]
    process = subprocess.Popen([sys.executable, "-m", "src.mcp_server.server"], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8")
    lines = queue.Queue()
    def read():
        for line in process.stdout:
            lines.put(line)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    collected = []
    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
    def receive(expected_id):
        while True:
            raw = lines.get(timeout=10)
            collected.append(raw)
            value = json.loads(raw)
            assert value["jsonrpc"] == "2.0"
            if value.get("id") == expected_id:
                return value
    try:
        send({"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{
            "protocolVersion":LATEST_PROTOCOL_VERSION, "capabilities":{},
            "clientInfo":{"name":"stdout-check","version":"1.0"}}})
        assert "result" in receive(1)
        send({"jsonrpc":"2.0", "method":"notifications/initialized"})
        send({"jsonrpc":"2.0", "id":2, "method":"tools/list", "params":{}})
        names = {t["name"] for t in receive(2)["result"]["tools"]}
        assert {"get_claim", "calculate_claim", "get_claim_status", "search_policy"} <= names
        send({"jsonrpc":"2.0", "id":3, "method":"tools/call", "params":{
            "name":"get_claim_status", "arguments":{"claim_id":"CLM-001"}}})
        assert "result" in receive(3)
        process.stdin.close()
        process.wait(timeout=10)
        reader.join(timeout=2)
        while not lines.empty():
            collected.append(lines.get_nowait())
        assert collected
        assert all(json.loads(line).get("jsonrpc") == "2.0" for line in collected)
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        if not process.stdin.closed:
            process.stdin.close()
