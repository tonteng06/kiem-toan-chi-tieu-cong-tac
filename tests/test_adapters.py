"""MCP schema/result adapters: no embedding model required."""
import copy
import json

import pytest
from mcp.types import CallToolResult, TextContent, Tool

from src.mcp_server.adapters import mcp_tool_to_llm_schema, mcp_tool_to_openai_schema, normalize_result


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
