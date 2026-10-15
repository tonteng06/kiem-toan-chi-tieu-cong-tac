"""Day 4 integration: real TV2 registry, MCP SDK and JSON/Error observations."""
import asyncio
import copy
import json
import shutil
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent, Tool as MCPTool

from src.agent.business_rules import calculate_claim
from src.agent.state_store import StateStore
from src.agent.tool_registry import Tool, ToolRegistry, build_registry
from src.mcp_server.agent_bridge import preview_registered_claim_via_mcp
from src.mcp_server.client import dispatch_mcp
from src.mcp_server.registry_adapter import dispatch_read_tool
from src.mcp_server import server as mcp_server
from test_mcp_evidence import ROOT, immediate, policy_records


@pytest.fixture
def registry(tmp_path):
    path = tmp_path / "claims.json"
    shutil.copyfile(ROOT / "data/claims/claims.json", path)
    return build_registry(StateStore(path))


@pytest.mark.parametrize("name", ["get_claim", "get_claim_status", "calculate_claim"])
def test_registry_read_adapter_uses_shared_tools(registry, name):
    payload = dispatch_read_tool(registry, name, {"claim_id": "CLM-001"})
    assert payload["claim_id"] == "CLM-001"


@pytest.mark.parametrize("name,args", [
    ("get_claim", {"claim_id": "CLM-999"}), ("calculate_claim", {}),
    ("get_claim_status", {"claim_id": True}), ("get_claim", {"claim_id": "CLM-001", "extra": 1}),
    ("missing", {}),
])
def test_registry_errors_keep_error_contract(registry, name, args):
    with pytest.raises(ValueError, match="^Error:"):
        dispatch_read_tool(registry, name, args)


def test_read_adapter_never_executes_registered_write():
    registry = ToolRegistry()
    called = []
    registry.register(Tool("write", "Not for Day 4", {}, lambda: called.append(True), writes=True))
    with pytest.raises(ValueError, match="write tool"):
        dispatch_read_tool(registry, "write", {})
    assert called == []


def test_registry_crash_becomes_error_observation():
    registry = ToolRegistry()
    def crash():
        raise OSError("unavailable store")
    registry.register(Tool("crash", "failure", {}, crash))
    with pytest.raises(ValueError, match="^Error:"):
        dispatch_read_tool(registry, "crash", {})


@pytest.mark.parametrize("raw", ["{bad", [], 123])
def test_async_adapter_rejects_malformed_args_before_io(raw):
    class NoIO:
        async def list_tools(self):
            pytest.fail("Bad arguments must not call MCP")
    assert immediate(dispatch_mcp(NoIO(), "get_claim", raw)).startswith("Error:")


def test_async_adapter_handles_discovery_failure():
    class BrokenClient:
        async def list_tools(self):
            raise OSError("disconnected")
    assert immediate(dispatch_mcp(BrokenClient(), "get_claim", {})) == "Error: disconnected"


def test_async_adapter_decodes_json_text_and_preserves_error_flag():
    class FakeClient:
        async def list_tools(self):
            return SimpleNamespace(tools=[MCPTool(name="get_claim", input_schema={"type": "object"})])
        async def call_tool(self, name, arguments):
            return CallToolResult(content=[TextContent(type="text", text='{"claim_id":"CLM-001"}')])
    assert json.loads(immediate(dispatch_mcp(FakeClient(), "get_claim", '{"claim_id":"CLM-001"}'))) == {"claim_id": "CLM-001"}


def test_async_adapter_propagates_cancellation():
    class CancelledClient:
        async def list_tools(self):
            raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        immediate(dispatch_mcp(CancelledClient(), "get_claim", {}))


def test_real_sdk_registry_pipeline_and_errors_leave_state_unchanged(registry, tmp_path):
    """Real in-process MCP transport; only retrieval candidates are controlled."""
    store_path = tmp_path / "claims.json"
    before = store_path.read_bytes()

    class ControlledRetriever:
        def retrieve(self, query, mode="hybrid", top_k=3):
            # Simulate selected policy candidates; this test is not model evaluation.
            from src.models.document import Chunk, SearchResult
            records = policy_records()
            required = {"DOC002", "DOC003", "DOC004", "DOC006", "DOC007"}
            selected = [r for r in records if r["doc_id"] in required]
            if "Receipt Requirements" in query:
                selected = [r for r in selected if r["doc_id"] == "DOC006"]
            elif "Expense Exception Policy" in query:
                selected = [r for r in selected if r["doc_id"] == "DOC007"]
            else:
                selected = selected[:top_k]
            return [SearchResult(Chunk(**{k:r[k] for k in ("chunk_id","doc_id","title","version","date","owner","content")}),r["score"],mode,r["dense_score"],r["bm25_score"]) for r in selected]

    async def run():
        async with Client(mcp_server.server) as client:
            raw = await dispatch_mcp(client, "get_claim", {"claim_id": "CLM-002"})
            assert json.loads(raw)["claim_id"] == "CLM-002"
            result = await preview_registered_claim_via_mcp(client, "CLM-002", "Audit the Da Nang hotel claim")
            assert result["decision"] == "ESCALATED"
            assert not result["missing_evidence_refs"]
            assert {"DOC003@v1.0", "DOC007@v1.0"} <= {c["evidence_ref"] for c in result["citations"]}
            assert result["calculation"] == calculate_claim(StateStore(store_path).get("CLM-002"))
            for name, args in (("get_claim", {"claim_id":"CLM-999"}), ("calculate_claim", {}), ("unknown", {})):
                assert (await dispatch_mcp(client, name, args)).startswith("Error:")

    with patch.object(mcp_server, "_get_registry", return_value=registry), patch.object(mcp_server, "_get_retriever", return_value=ControlledRetriever()):
        asyncio.run(asyncio.wait_for(run(), timeout=20))
    assert store_path.read_bytes() == before


@pytest.mark.parametrize("corruption", ["claim_id", "total", "recommended_status", "violations"])
def test_bad_remote_calculation_cannot_authorize_decision(registry, corruption):
    class FakeClient:
        async def list_tools(self):
            return SimpleNamespace(tools=[MCPTool(name=name, input_schema={"type":"object"}) for name in registry.names()])
        async def call_tool(self, name, arguments):
            result = dispatch_read_tool(registry, name, arguments)
            if name == "calculate_claim":
                result = copy.deepcopy(result)
                result[corruption] = {"claim_id":"OTHER", "total":1, "recommended_status":"APPROVE", "violations":None}[corruption]
            return CallToolResult(content=[], structured_content=result)
    with pytest.raises(ValueError, match="^Error:"):
        immediate(preview_registered_claim_via_mcp(FakeClient(), "CLM-002", "Hotel limit"))
