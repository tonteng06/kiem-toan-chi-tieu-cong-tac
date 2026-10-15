"""MCP -> TV2/LLM schema and observation adapters."""
from __future__ import annotations

import copy
import json
from collections.abc import Mapping

from mcp.types import CallToolResult, Tool


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
