"""Run the real LLM agent on sample claims (TV2). Needs GROQ_API_KEY and the embedding model.

    python scripts/demo_agent.py                      # CLM-001 CLM-002 CLM-003 CLM-006
    python scripts/demo_agent.py CLM-002 --log logs/agent_run_01.jsonl

Each claim runs on a temporary COPY of data/claims/claims.json, so the tracked sample data is never
changed and the same demo can be repeated. One JSON line per claim is appended to the log (steps,
tool args/results, verified write, usage). Nothing here is mocked: no key -> the run stops with an error.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.agent import RegistryToolbox, run_agent  # noqa: E402
from src.agent.llm_client import LLMConfig, make_llm  # noqa: E402
from src.agent.run_log import append_run_log  # noqa: E402
from src.agent.state_store import DEFAULT_PATH, StateStore  # noqa: E402
from src.agent.tool_registry import build_registry  # noqa: E402

DEFAULT_CLAIMS = ["CLM-001", "CLM-002", "CLM-003", "CLM-006"]


def question_for(claim_id: str) -> str:
    return (f"Audit claim {claim_id} against the travel expense policy. "
            "If the evidence is sufficient, record the decision with submit_decision.")


def run_claims(claim_ids, llm, retriever, log_path: Path, state_path: Path = DEFAULT_PATH) -> list[dict]:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "claims.json"
        shutil.copy(state_path, work)
        store = StateStore(work)
        toolbox = RegistryToolbox(build_registry(store, retriever))
        for claim_id in claim_ids:
            question = question_for(claim_id)
            result = run_agent(question, llm, toolbox)
            append_run_log(log_path, question, result, question_id=claim_id)
            write = result["write"]
            print(f"{claim_id}: {result['decision']} | stop={result['stopped_reason']} | steps={result['steps']} | "
                  f"{write['verify'] if write else 'no write'} | usage={result['usage']}")
            results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("claims", nargs="*", default=DEFAULT_CLAIMS)
    parser.add_argument("--log", type=Path, default=Path("logs/agent_run.jsonl"))
    args = parser.parse_args()

    from src.rag.chunker import chunk_documents
    from src.rag.loader import load_documents
    from src.rag.retriever import Retriever

    policy_dir = Path(__file__).resolve().parents[1] / "data" / "policies"
    retriever = Retriever(chunk_documents(load_documents(policy_dir)))
    run_claims(args.claims, make_llm(LLMConfig.from_env()), retriever, args.log)
    print(f"log: {args.log}")


if __name__ == "__main__":
    main()