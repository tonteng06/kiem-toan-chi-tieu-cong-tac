import csv
from pathlib import Path

import numpy as np

from src.rag.bm25_search import BM25Searcher, tokenize
from src.rag.chunker import chunk_documents
from src.rag.embeddings import EmbeddingModel
from src.rag.hybrid_search import normalise_scores
from src.rag.loader import load_documents


TOP_K = 5
OUTPUT_PATH = Path("evaluation/day2_reasoning_cases.csv")

CASES = [
    {
        "id": "Q13",
        "question": (
            "An employee stays one night in Da Nang for 1800000 VND. "
            "The hotel limit is exceeded. "
            "Which policies are relevant to decide what should happen?"
        ),
        "expected_doc_ids": {"DOC003", "DOC007"},
    },
    {
        "id": "Q14",
        "question": (
            "An employee takes a taxi for an approved business purpose "
            "costing 600000 VND but has no receipt. "
            "Which policies are relevant?"
        ),
        "expected_doc_ids": {"DOC005", "DOC006"},
    },
    {
        "id": "Q15",
        "question": (
            "An employee submits a travel expense claim 12 calendar days "
            "after the trip. Which versions of the travel expense policy "
            "are relevant for checking the submission deadline?"
        ),
        "expected_doc_ids": {"DOC001", "DOC002"},
    },
]


def main() -> None:
    documents = load_documents("data/policies")
    chunks = chunk_documents(documents)

    embedding_model = EmbeddingModel()

    chunk_embeddings = embedding_model.encode(
        [chunk.content for chunk in chunks]
    )

    bm25_searcher = BM25Searcher(chunks)

    rows = []

    for case in CASES:
        case_id = case["id"]
        question = case["question"]
        expected_doc_ids = case["expected_doc_ids"]

        query_embedding = embedding_model.encode_one(question)

        dense_scores = (
            chunk_embeddings
            @ query_embedding
        )

        raw_bm25_scores = (
            bm25_searcher.bm25.get_scores(
                tokenize(question)
            )
        )

        bm25_norm = np.array(
            normalise_scores(
                [
                    float(score)
                    for score
                    in raw_bm25_scores
                ]
            )
        )

        hybrid_scores = (
            0.3 * bm25_norm
            + 0.7 * dense_scores
        )

        rankings = {
            "dense": np.argsort(
                dense_scores
            )[::-1],
            "hybrid": np.argsort(
                hybrid_scores
            )[::-1],
        }

        print(
            f"\n{'=' * 70}"
        )
        print(
            f"{case_id}: {question}"
        )
        print(
            "Expected:",
            sorted(expected_doc_ids),
        )

        for mode, ranked_indices in rankings.items():
            print(
                f"\n----- {mode.upper()} TOP {TOP_K} -----"
            )

            for rank, index in enumerate(
                ranked_indices[:TOP_K],
                start=1,
            ):
                chunk = chunks[index]

                is_expected = (
                    chunk.doc_id
                    in expected_doc_ids
                )

                print(
                    f"{rank}. "
                    f"{chunk.doc_id} "
                    f"| version={chunk.version} "
                    f"| dense={dense_scores[index]:.4f} "
                    f"| bm25_raw={raw_bm25_scores[index]:.4f} "
                    f"| bm25_norm={bm25_norm[index]:.4f} "
                    f"| hybrid={hybrid_scores[index]:.4f} "
                    f"| expected={is_expected}"
                )

                rows.append(
                    {
                        "case_id": case_id,
                        "mode": mode,
                        "rank": rank,
                        "doc_id": chunk.doc_id,
                        "chunk_id": chunk.chunk_id,
                        "version": chunk.version,
                        "date": chunk.date,
                        "dense_score": (
                            f"{dense_scores[index]:.4f}"
                        ),
                        "bm25_raw": (
                            f"{raw_bm25_scores[index]:.4f}"
                        ),
                        "bm25_norm": (
                            f"{bm25_norm[index]:.4f}"
                        ),
                        "hybrid_score": (
                            f"{hybrid_scores[index]:.4f}"
                        ),
                        "is_expected": is_expected,
                    }
                )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id",
                "mode",
                "rank",
                "doc_id",
                "chunk_id",
                "version",
                "date",
                "dense_score",
                "bm25_raw",
                "bm25_norm",
                "hybrid_score",
                "is_expected",
            ],
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"\nSaved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
