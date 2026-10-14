"""Tool dispatcher (TV2, Day 3): run one tool call and always return a string.

Success -> JSON text. Any failure -> "Error: ...". Nothing here raises, so a bad
tool call never kills the agent run; the model just sees the error as an
observation and can try again.
"""
from __future__ import annotations

import json
from typing import Any

from src.agent.state_store import StateStoreError
from src.agent.tool_registry import Tool, ToolRegistry

ERROR_PREFIX = "Error: "


class ToolArgError(ValueError):
    """The model sent arguments that do not match the tool."""


def is_error(observation: str) -> bool:
    return observation.startswith(ERROR_PREFIX)


def parse_args(raw: Any) -> dict:
    """Accept a dict or a JSON string; anything else is an error."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ToolArgError(f"arguments are not valid JSON ({exc.msg})") from None
    if not isinstance(raw, dict):
        raise ToolArgError("arguments must be a JSON object")
    return raw


def validate_args(tool: Tool, args: dict) -> None:
    unknown = sorted(set(args) - set(tool.params))
    if unknown:
        raise ToolArgError(f"unknown argument(s) for {tool.name}: {unknown}")
    missing = [k for k in tool.params if k not in args]
    if missing:
        raise ToolArgError(f"missing argument(s) for {tool.name}: {missing}")
    for key, expected in tool.params.items():
        # exact type check: True must not pass as an int
        if type(args[key]) is not expected:
            raise ToolArgError(
                f"argument '{key}' must be {expected.__name__}, got {type(args[key]).__name__}"
            )


def dispatch(registry: ToolRegistry, name: Any, raw_args: Any = None) -> str:
    tool = registry.get(name) if isinstance(name, str) else None
    if tool is None:
        return f"{ERROR_PREFIX}unknown tool {name!r}. Available tools: {', '.join(registry.names())}"
    try:
        args = parse_args(raw_args)
        validate_args(tool, args)
        return json.dumps(tool.func(**args), ensure_ascii=False, default=str)
    except (ToolArgError, StateStoreError) as exc:  # expected, model-fixable errors
        return f"{ERROR_PREFIX}{exc}"
    except Exception as exc:  # a bug inside a tool must not crash the run
        return f"{ERROR_PREFIX}tool '{name}' failed ({type(exc).__name__}: {exc})"