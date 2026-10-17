"""Real stdio check: start the server as a subprocess, discover tools, call one.

    python scripts/smoke_stdio.py
Uses only claim tools, so it needs no embedding model.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mcp_server.client import call_tool, connect, discover_tools


async def main() -> None:
    async with connect(sys.executable, ["-m", "src.mcp_server.server"], cwd=str(ROOT)) as client:
        names = [tool.name for tool in await discover_tools(client)]
        print("tools:", names)
        assert {"search_policy", "get_claim_status"} <= set(names), names

        ok = await call_tool(client, "get_claim_status", {"claim_id": "CLM-001"})
        assert not ok.is_error and ok.structured_content["claim_id"] == "CLM-001"
        print("CLM-001:", ok.structured_content)

        bad = await call_tool(client, "get_claim_status", {"claim_id": "CLM-999"})
        assert bad.is_error
        assert bad.content[0].text.startswith("Error:")
        print("CLM-999 -> error as expected")
    print("stdio OK")


if __name__ == "__main__":
    asyncio.run(main())
