"""Real provider -> manual Agent -> dynamically discovered MCP tools, isolated state.

No mock fallback. A failed or unverified run returns a nonzero exit status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.agent import run_agent
from src.agent.llm_client import LLMConfig, make_llm
from src.agent.run_log import run_record
from src.agent.state_store import DEFAULT_PATH
from src.mcp_server.adapters import McpToolbox


class GroundedMcpToolbox:
    """Require every write citation to have been returned as text in this run.

    TV2's gate checks issue refs; this boundary also checks all MCP write refs,
    including receipt/deadline policies needed for otherwise clean approvals.
    """
    def __init__(self, toolbox):
        self.toolbox = toolbox
        self.seen_refs: set[str] = set()

    def schemas(self):
        return self.toolbox.schemas()

    def call(self, name, args=None):
        if name == "submit_decision":
            refs = args.get("evidence_refs") if isinstance(args, dict) else None
            if (not isinstance(refs, list) or not refs
                    or any(not isinstance(ref, str) or ref not in self.seen_refs for ref in refs)):
                return "Error: write blocked: every evidence_ref must first be retrieved in this run"
        observation = self.toolbox.call(name, args)
        if name == "search_policy" and not observation.startswith("Error:"):
            try:
                payload = json.loads(observation)
                for item in payload.get("results", []):
                    if (isinstance(item, dict) and isinstance(item.get("evidence_ref"), str)
                            and isinstance(item.get("content"), str) and item["content"].strip()):
                        self.seen_refs.add(item["evidence_ref"])
            except (ValueError, AttributeError, TypeError):
                pass  # malformed search output cannot authorize a write
        return observation


def run_claim(claim_id: str, llm, log_path: Path, *, max_steps: int = 16) -> dict:
    original = hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest()
    question = (f"Audit claim {claim_id} against company travel policies. Retrieve every applicable "
                "policy, calculate the recommendation, submit it only with sufficient evidence, "
                "and verify the saved decision. Use the discovered tool schemas, including evidence_refs.")
    with tempfile.TemporaryDirectory(prefix="aipr-agent-") as directory:
        state_path = Path(directory) / "claims.json"
        shutil.copyfile(DEFAULT_PATH, state_path)
        bootstrap = ("import os; os.environ['AIPR_STATE_PATH']=" + repr(str(state_path)) + "; "
                     "from src.mcp_server.server import main; main()")
        with McpToolbox(args=["-c", bootstrap], timeout=300) as toolbox:
            result = run_agent(question, llm, GroundedMcpToolbox(toolbox), max_steps=max_steps)
            result["mcp_history"] = toolbox.history
            result["discovered_tools"] = [schema["name"] for schema in toolbox.schemas()]
        written = result.get("write")
        result["disk_verified"] = False
        if written:
            saved = next(c for c in json.loads(state_path.read_text(encoding="utf-8"))
                         if c["claim_id"] == claim_id)
            result["disk_verified"] = (written["claim_id"] == claim_id
                                       and written["verify"] == "VERIFY SUCCESS"
                                       and saved["status"] == written["decision"])
    if hashlib.sha256(DEFAULT_PATH.read_bytes()).hexdigest() != original:
        raise RuntimeError("Tracked claim fixture changed")
    record = run_record(question, result, question_id=claim_id)
    # Keep wire history as well as Agent trace, including the automatic read-back call.
    record.update(run_kind="real_llm_mcp", llm_used=True, isolated_state=True,
                  disk_verified=result["disk_verified"], mcp_history=result["mcp_history"],
                  discovered_tools=result["discovered_tools"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claims", nargs="*", default=["CLM-001", "CLM-002", "CLM-003"])
    parser.add_argument("--log", type=Path, default=ROOT / "logs/agent_mcp.jsonl")
    parser.add_argument("--max-steps", type=int, default=16)
    args = parser.parse_args()
    # Resolve from the project root even when launched from another directory.
    # Explicit shell variables take precedence over values in the local file.
    load_dotenv(ROOT / ".env", override=False, encoding="utf-8-sig")
    config = LLMConfig.from_env()
    if not config.api_key:
        print("Error: set GROQ_API_KEY (or LLM_API_KEY) in the environment or project .env file.", file=sys.stderr)
        return 2
    if not 1 <= args.max_steps <= 32:
        parser.error("--max-steps must be between 1 and 32")
    passed = True
    for claim_id in args.claims:
        result = run_claim(claim_id, make_llm(config), args.log, max_steps=args.max_steps)
        ok = result["stopped_reason"] == "final" and result["disk_verified"]
        passed = passed and ok
        print(f"{claim_id}: {result['decision']}; stop={result['stopped_reason']}; "
              f"disk_verified={result['disk_verified']}; usage={result['usage']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
