"""Adapt TV2's synchronous registry/dispatcher to MCP's typed read tools."""
from __future__ import annotations

import json

from src.agent.dispatcher import dispatch, is_error
from src.agent.tool_registry import ToolRegistry


def dispatch_read_tool(registry: ToolRegistry, name: str, arguments: dict) -> dict:
    """Keep the shared dispatcher responsible for argument and tool errors.

    Only already-registered read tools can cross this boundary. Day 5 writes
    need their own action/verification boundary and must not be exposed here.
    """
    tool = registry.get(name)
    if tool is None:
        raise ValueError(f"Error: unknown registry tool {name!r}")
    if tool.writes:
        raise ValueError(f"Error: write tool {name!r} is not allowed by the read adapter")
    observation = dispatch(registry, name, arguments)
    if is_error(observation):
        raise ValueError(observation)
    try:
        payload = json.loads(observation)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Error: registry returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Error: registry read tool must return a JSON object")
    return payload
