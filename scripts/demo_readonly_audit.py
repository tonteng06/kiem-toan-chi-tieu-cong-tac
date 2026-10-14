"""Day 3: real MCP search -> evidence -> deterministic reasoning -> decision."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.state_store import DEFAULT_PATH, StateStore
from src.mcp_server.agent_bridge import preview_audit_via_mcp
from src.mcp_server.client import connect
from src.models.claim import Claim, Expense


def example_claim() -> Claim:
    return Claim(
        claim_id="DEMO-DANANG", employee="Demo employee", city="Da Nang", country="VN",
        start_date=date(2026, 10, 12), end_date=date(2026, 10, 13),
        submitted_date=date(2026, 10, 14), purpose="Client meeting",
        expenses=[Expense("hotel", 1_800_000, date(2026, 10, 12), "One hotel night", True)],
    )


async def run(args) -> dict:
    claim = StateStore().get(args.claim_id) if args.claim_id else example_claim()
    before = hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest()
    if args.transport == "inprocess":
        from mcp import Client
        from src.mcp_server.server import server

        async with Client(server) as client:
            result = await preview_audit_via_mcp(client, claim, args.question, mode=args.mode, top_k=args.top_k)
    else:
        # An explicit cwd also makes the subprocess importable from outside repo root.
        async with connect(sys.executable, ["-m", "src.mcp_server.server"], cwd=str(ROOT)) as client:
            result = await preview_audit_via_mcp(client, claim, args.question, mode=args.mode, top_k=args.top_k)
    if before != hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest():
        raise RuntimeError("Read-only demo unexpectedly changed claim state")
    return {"transport": args.transport, "embedding": "real", **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default="Da Nang hotel 1800000 VND exceeds the limit; which decision and policies apply?")
    parser.add_argument("--claim-id", help="Use a sample claim instead of the in-memory 1.8M hotel example")
    parser.add_argument("--mode", choices=["dense", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--transport", choices=["stdio", "inprocess"], default="stdio")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    result = asyncio.run(asyncio.wait_for(run(args), timeout=args.timeout))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
