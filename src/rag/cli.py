"""Run one question against the policy corpus and print the top-k chunks.

Example:
    python -m src.rag.cli "What is the hotel limit in Da Nang?" --mode hybrid --top-k 3
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.rag.chunker import chunk_documents
from src.rag.loader import load_documents
from src.rag.retriever import Retriever


POLICY_DIR = Path(__file__).parents[2] / "data" / "policies"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search the policy corpus."
    )
    parser.add_argument("query")
    parser.add_argument(
        "--mode",
        choices=["dense", "hybrid"],
        default="hybrid",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
    )
    args = parser.parse_args()

    documents = load_documents(POLICY_DIR)
    chunks = chunk_documents(documents)
    retriever = Retriever(chunks)

    results = retriever.retrieve(
        args.query,
        mode=args.mode,
        top_k=args.top_k,
    )

    for rank, result in enumerate(results, start=1):
        chunk = result.chunk

        print(
            f"{rank}. "
            f"{chunk.doc_id}@v{chunk.version} "
            f"({chunk.date}) "
            f"score={result.score:.4f}"
        )
        print(f"   {chunk.content[:160]!r}")


if __name__ == "__main__":
    main()
