"""MCP stdio client with dynamic tool discovery."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent, Tool

from src.mcp_server.contracts import SearchPolicyOutput
from src.mcp_server.evidence import parse_search_payload


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
    parameters = StdioServerParameters(command=command, args=args, cwd=cwd)
    async with Client(parameters) as client:
        yield client


async def discover_tools(client: Client) -> list[Tool]:
    """Return the tools advertised by the connected server at runtime."""
    response = await client.list_tools()
    return response.tools


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

