"""Run the real LLM agent on free-form questions from tests/testset.jsonl (e.g. the no_answer cases).

    python scripts/demo_agent_questions.py --list
    python scripts/demo_agent_questions.py Q09 --log logs/agent_run_04.jsonl
    python scripts/demo_agent_questions.py Q10 Q11 Q12 --log logs/agent_run_04.jsonl

Same setup as scripts/demo_agent.py (same registry toolbox, same .env loading, a temporary copy of the
claims file), but the question comes from the testset instead of "Audit claim CLM-xxx". One JSON line
per question is appended to the log. Nothing is mocked: no key -> the run ends with an llm_error.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_agent import load_env_file  # noqa: E402
from src.agent.agent import RegistryToolbox, run_agent  # noqa: E402
from src.agent.llm_client import LLMConfig, make_llm  # noqa: E402
from src.agent.run_log import append_run_log  # noqa: E402
from src.agent.state_store import DEFAULT_PATH, StateStore  # noqa: E402
from src.agent.tool_registry import build_registry  # noqa: E402

ID_KEYS = ("id", "qid", "question_id")
TEXT_KEYS = ("question", "query")


def read_testset(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        qid = next((str(record[k]) for k in ID_KEYS if k in record), None)
        text = next((record[k] for k in TEXT_KEYS if k in record), None)
        if qid is None or text is None:
            raise SystemExit(f"Unexpected testset fields: {sorted(record)}. Edit ID_KEYS / TEXT_KEYS at the top.")
        rows.append((qid, text))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="question ids from the testset, e.g. Q09 Q10")
    parser.add_argument("--testset", type=Path, default=Path("tests/testset.jsonl"))
    parser.add_argument("--log", type=Path, default=Path("logs/agent_run_04.jsonl"))
    parser.add_argument("--list", action="store_true", help="print the ids and questions, then exit")
    args = parser.parse_args()

    rows = read_testset(args.testset)
    if args.list or not args.ids:
        for qid, text in rows:
            print(f"{qid}: {text}")
        return
    by_id = dict(rows)
    missing = [i for i in args.ids if i not in by_id]
    if missing:
        raise SystemExit(f"ids not found: {missing}. Available: {sorted(by_id)}")

    load_env_file(Path(__file__).resolve().parents[1] / ".env")

    from src.rag.chunker import chunk_documents
    from src.rag.loader import load_documents
    from src.rag.retriever import Retriever

    policy_dir = Path(__file__).resolve().parents[1] / "data" / "policies"
    retriever = Retriever(chunk_documents(load_documents(policy_dir)))
    llm = make_llm(LLMConfig.from_env())

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "claims.json"
        shutil.copy(DEFAULT_PATH, work)
        toolbox = RegistryToolbox(build_registry(StateStore(work), retriever))
        for qid in args.ids:
            question = by_id[qid]
            result = run_agent(question, llm, toolbox)
            append_run_log(args.log, question, result, question_id=qid)
            write = result["write"]
            print(f"{qid}: {result['decision']} | stop={result['stopped_reason']} | steps={result['steps']} | "
                  f"{write['verify'] if write else 'no write'} | usage={result['usage']}")
    print(f"log: {args.log}")


if __name__ == "__main__":
    main()