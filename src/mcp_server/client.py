"""MCP stdio client with dynamic tool discovery."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import os
from weakref import ref

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent, Tool

from src.mcp_server.contracts import SearchPolicyOutput
from src.mcp_server.evidence import parse_search_payload
from src.agent.dispatcher import parse_args

# SDK Client is unhashable, so WeakKeyDictionary cannot key it directly.
# Identity + weak reference avoids retaining closed clients or reusing stale IDs.
_DISCOVERY = {}


def _cache_tools(client, tools):
    key = id(client)
    def forget(reference):
        cached = _DISCOVERY.get(key)
        if cached is not None and cached[0] is reference:
            _DISCOVERY.pop(key, None)
    try:
        reference = ref(client, forget)
    except TypeError:
        return  # non-SDK test doubles may not support weak references
    _DISCOVERY[key] = (reference, tuple(tools))


def search_payload(response: CallToolResult) -> SearchPolicyOutput:
    """Unpack SDK 2.x structured content, or its JSON text representation."""
    if response.is_error:
        raise ValueError(f"Error: search_policy failed: {response.content}")
    if response.structured_content is not None:
        return parse_search_payload(response.structured_content)
    texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if len(texts) != 1:
        raise ValueError("Error: search_policy returned no unambiguous structured/JSON response")
    try:
        payload = json.loads(texts[0])
    except json.JSONDecodeError as exc:
        raise ValueError("Error: search_policy returned malformed JSON") from exc
    return parse_search_payload(payload)


@asynccontextmanager
async def connect(
    command: str,
    args: list[str],
    *,
    cwd: str | None = None,
) -> AsyncIterator[Client]:
    """Start an MCP server process and open a client connection to it."""
    # The SDK inherits a minimal environment. Forward only documented runtime
    # configuration so retrieval can use the host proxy/cache and isolated state.
    keys = {"AIPR_STATE_PATH", "HF_HOME", "HF_HUB_CACHE", "HF_HUB_OFFLINE",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
            "http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    environment = {key: value for key, value in os.environ.items() if key in keys}
    parameters = StdioServerParameters(command=command, args=args, cwd=cwd, env=environment)
    async with Client(parameters) as client:
        yield client


async def discover_tools(client: Client, *, refresh: bool = False) -> list[Tool]:
    """Cache runtime discovery per client; refresh=True explicitly lists again."""
    cached = _DISCOVERY.get(id(client))
    if not refresh and cached is not None and cached[0]() is client:
        return list(cached[1])
    response = await client.list_tools()
    _cache_tools(client, response.tools)
    return list(response.tools)


async def call_tool(
    client: Client,
    tool_name: str,
    arguments: dict[str, object],
) -> CallToolResult:
    """Call a tool by its discovered name without a hard-coded tool registry."""
    available = await discover_tools(client)
    if not any(tool.name == tool_name for tool in available):
        names = ", ".join(tool.name for tool in available) or "(none)"
        raise ValueError(f"Error: Unknown MCP tool {tool_name!r}; available tools: {names}")
    response = await client.call_tool(tool_name, arguments)
    if response.is_error:
        message = "\n".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ) or f"Tool {tool_name} failed"
        if not message.startswith("Error:"):
            message = "Error: " + message
        return response.model_copy(update={"content": [TextContent(type="text", text=message)]})
    return response


async def dispatch_mcp(client: Client, name: object, raw_args: object = None) -> str:
    """Async Agent adapter: JSON success or Error: observation, like TV2 dispatch.

    Use `await` from the Agent loop; never nest asyncio.run inside a tool function.
    Discovery/calls are made at runtime; ordinary failures become observations.
    Cancellation still propagates, so a stopped run remains stopped.
    """
    try:
        if not isinstance(name, str):
            raise ValueError("tool name must be a string")
        arguments = parse_args(raw_args)
        response = await call_tool(client, name, arguments)
        if response.is_error:
            message = "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text")
            return message if message.startswith("Error:") else "Error: " + message
        if name == "search_policy":
            payload = search_payload(response)
        elif response.structured_content is not None:
            payload = response.structured_content
        else:
            texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
            if len(texts) != 1:
                raise ValueError("tool returned no unambiguous JSON result")
            payload = json.loads(texts[0])
        if not isinstance(payload, dict):
            raise ValueError("tool result must be a JSON object")
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        message = str(exc)
        return message if message.startswith("Error:") else f"Error: {message}"

