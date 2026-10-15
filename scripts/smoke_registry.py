"""Day 4: real stdio -> MCP read tools -> TV2 registry/dispatcher (no model)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.state_store import DEFAULT_PATH
from src.mcp_server.client import connect, discover_tools, dispatch_mcp


async def main() -> None:
    before = hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest()
    async with connect(sys.executable, ["-m", "src.mcp_server.server"], cwd=str(ROOT)) as client:
        names = {tool.name for tool in await discover_tools(client)}
        assert {"search_policy", "get_claim", "calculate_claim", "get_claim_status"} <= names
        assert "submit_decision" not in names
        print("tools:", sorted(names))
        for claim_id, expected in (("CLM-001", "APPROVED"), ("CLM-002", "ESCALATED"),
                                   ("CLM-003", "NEED_MORE_INFO"), ("CLM-006", "REJECTED")):
            claim = json.loads(await dispatch_mcp(client, "get_claim", {"claim_id": claim_id}))
            calculation = json.loads(await dispatch_mcp(client, "calculate_claim", {"claim_id": claim_id}))
            status = json.loads(await dispatch_mcp(client, "get_claim_status", {"claim_id": claim_id}))
            assert claim["claim_id"] == calculation["claim_id"] == status["claim_id"] == claim_id
            assert calculation["recommended_status"] == expected
            assert status["status"] == claim["status"]
            print(claim_id, "recommendation:", expected, "persisted:", status["status"])
        for name, args in (("get_claim", {"claim_id": "CLM-999"}),
                           ("calculate_claim", {}), ("get_claim", "{bad JSON"),
                           ("not_registered", {})):
            error = await dispatch_mcp(client, name, args)
            assert error.startswith("Error:"), error
        print("error observations OK")
    assert hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest() == before
    print("registry stdio OK; claim state unchanged")


if __name__ == "__main__":
    asyncio.run(main())
