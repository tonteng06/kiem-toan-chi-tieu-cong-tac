"""MCP stdio client with dynamic tool discovery."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool


@asynccontextmanager
async def connect(
    command: str,
    args: list[str],
) -> AsyncIterator[Client]:
    """Start an MCP server process and open a client connection to it."""
    parameters = StdioServerParameters(command=command, args=args)
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
        raise ValueError(f"Unknown MCP tool {tool_name!r}; available tools: {names}")
    return await client.call_tool(tool_name, arguments)

