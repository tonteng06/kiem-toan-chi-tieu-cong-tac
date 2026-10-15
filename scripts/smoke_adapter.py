"""Synchronous MCP toolbox smoke; save complete schema/call evidence for Day 4.

    python scripts/smoke_adapter.py
No embedding model or API key is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.state_store import DEFAULT_PATH
from src.mcp_server.adapters import McpToolbox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/day4_adapter_smoke.json")
    args = parser.parse_args()
    before = hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest()
    with McpToolbox() as toolbox:
        schemas = toolbox.schemas()
        print(json.dumps(schemas, ensure_ascii=False, indent=2))
        assert {"search_policy", "get_claim_status", "get_claim", "calculate_claim"} <= {s["name"] for s in schemas}
        success = toolbox.call("get_claim_status", {"claim_id": "CLM-001"})
        assert json.loads(success)["claim_id"] == "CLM-001"
        missing = toolbox.call("get_claim_status", {"claim_id": "CLM-999"})
        unknown = toolbox.call("not_registered", {})
        assert missing.startswith("Error: ") and unknown.startswith("Error: ")
        assert toolbox.discovery_count == 1
        history = toolbox.history
    assert not toolbox._thread.is_alive()
    assert hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest() == before
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(), "command": "python scripts/smoke_adapter.py",
        "transport": "real stdio subprocess", "model_required": False,
        "schemas": schemas, "calls": history, "discovery_count": toolbox.discovery_count,
        "clean_shutdown": True, "claim_state_unchanged": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CLM-001:", success)
    print("CLM-999:", missing)
    print("unknown tool:", unknown)
    print("adapter stdio OK")


if __name__ == "__main__":
    main()
