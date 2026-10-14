"""SDK response/wiring checks with fake client IO, not transport round-trips."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mcp.types import CallToolResult, TextContent, Tool

from src.mcp_server.client import call_tool, search_payload
from src.mcp_server.agent_bridge import preview_audit_via_mcp
from src.mcp_server.server import server, search_policy
from src.models.document import Chunk, SearchResult
from test_mcp_evidence import hotel_claim, immediate, policy_records


class MCPResponseTests(unittest.TestCase):
    def test_structured_response_roundtrip(self):
        payload = {"results": policy_records()}
        response = CallToolResult(content=[], structured_content=payload)
        self.assertEqual(search_payload(response), payload)

    def test_text_json_response_roundtrip(self):
        payload = {"results": policy_records()}
        response = CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))])
        self.assertEqual(search_payload(response), payload)

    def test_error_response_is_never_evidence(self):
        response = CallToolResult(content=[TextContent(type="text", text="No model")], is_error=True)
        with self.assertRaisesRegex(ValueError, "failed"):
            search_payload(response)

    def test_ambiguous_or_malformed_text_rejected(self):
        for texts in ([], ["not JSON"], ["{}", "{}"]):
            with self.subTest(texts=texts), self.assertRaises(ValueError):
                search_payload(CallToolResult(content=[TextContent(type="text", text=t) for t in texts]))

    def test_malformed_structured_payload_cannot_fallback_to_text(self):
        response = CallToolResult(structured_content={"wrong": []}, content=[TextContent(type="text", text=json.dumps({"results": policy_records()}))])
        with self.assertRaises(ValueError):
            search_payload(response)


class MCPWiringTests(unittest.TestCase):
    def test_tool_errors_have_agreed_prefix_and_error_flag(self):
        class Client:
            async def list_tools(self):
                return SimpleNamespace(tools=[Tool(name="get_claim_status", input_schema={"type": "object"})])
            async def call_tool(self, name, arguments):
                return CallToolResult(is_error=True, content=[TextContent(type="text", text="Error executing tool: missing claim")])
        result = immediate(call_tool(Client(), "get_claim_status", {"claim_id": "CLM-999"}))
        self.assertTrue(result.is_error)
        self.assertTrue(result.content[0].text.startswith("Error:"))

    def test_dynamic_discovery_rejects_unadvertised_name(self):
        class Client:
            async def list_tools(self):
                return SimpleNamespace(tools=[Tool(name="another_tool", input_schema={"type": "object"})])
            async def call_tool(self, name, arguments):
                raise AssertionError("Undiscovered tool was called")
        with self.assertRaisesRegex(ValueError, "Unknown MCP tool"):
            immediate(call_tool(Client(), "search_policy", {"query": "hotel"}))

    def test_bridge_uses_discovered_tool_and_arguments(self):
        calls = []
        class Client:
            async def list_tools(self):
                calls.append("tools/list")
                return SimpleNamespace(tools=[Tool(name="search_policy", input_schema={"type": "object"})])
            async def call_tool(self, name, arguments):
                calls.append((name, arguments))
                return CallToolResult(content=[], structured_content={"results": policy_records()})
        result = immediate(preview_audit_via_mcp(Client(), hotel_claim(), "Audit hotel"))
        self.assertEqual(result["decision"], "ESCALATED")
        self.assertEqual(calls, ["tools/list", ("search_policy", {"query": "Audit hotel", "mode": "hybrid", "top_k": 3})])

    def test_real_server_handler_serializes_retriever_result(self):
        chunk = Chunk("DOC003_CH001", "DOC003", "Hotel limits", "1.0", "2026-02-01", "Finance", "Da Nang: 1,500,000 VND per night.")
        result = SearchResult(chunk, 0.8, "hybrid", 0.9, 2.0)
        with patch("src.mcp_server.server._get_retriever") as retriever:
            retriever.return_value.retrieve.return_value = [result]
            payload = search_policy("Da Nang hotel limit")
            retriever.return_value.retrieve.assert_called_once_with("Da Nang hotel limit", mode="hybrid", top_k=3)
        self.assertEqual(payload["results"][0]["chunk_id"], chunk.chunk_id)
        self.assertEqual(payload["results"][0]["content"], chunk.content)

    def test_registry_contains_only_current_read_tools(self):
        tools = server._tool_manager.list_tools()
        self.assertEqual({tool.name for tool in tools}, {"search_policy", "get_claim_status"})


if __name__ == "__main__":
    unittest.main()
