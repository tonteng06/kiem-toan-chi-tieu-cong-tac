import csv
import json
from pathlib import Path

from src.rag.chunker import chunk_documents
from src.rag.loader import load_documents
from src.rag.retriever import Retriever


TOP_K = 3

TESTSET_PATH = Path("tests/testset.jsonl")
RESULTS_PATH = Path("evaluation/results.csv")
SUMMARY_PATH = Path("evaluation/summary.csv")


def load_testset(path: Path) -> list[dict]:
    items = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))

    return items


def unique_doc_ids(results) -> list[str]:
    doc_ids = []

    for result in results:
        doc_id = result.chunk.doc_id

        if doc_id not in doc_ids:
            doc_ids.append(doc_id)

    return doc_ids


def evaluate() -> None:
    documents = load_documents("data/policies")
    chunks = chunk_documents(documents)

    retriever = Retriever(chunks)

    testset = load_testset(TESTSET_PATH)

    result_rows = []
    summary_rows = []

    for mode in ["dense", "hybrid"]:
        hit_scores = []
        recall_scores = []

        print(f"\n===== {mode.upper()} =====")

        for item in testset:
            results = retriever.retrieve(
                query=item["question"],
                mode=mode,
                top_k=TOP_K,
            )

            retrieved_doc_ids = unique_doc_ids(results)
            expected_doc_ids = item["expected_doc_ids"]
            no_answer = item["no_answer"]

            if no_answer:
                hit_at_3 = ""
                recall_at_3 = ""

                print(
                    item["id"],
                    "| NO_ANSWER",
                    "| retrieved:",
                    retrieved_doc_ids,
                )
            else:
                expected_set = set(expected_doc_ids)
                retrieved_set = set(retrieved_doc_ids)

                matched = expected_set & retrieved_set

                hit_at_3 = 1 if matched else 0
                recall_at_3 = len(matched) / len(expected_set)

                hit_scores.append(hit_at_3)
                recall_scores.append(recall_at_3)

                print(
                    item["id"],
                    "| expected:",
                    expected_doc_ids,
                    "| retrieved:",
                    retrieved_doc_ids,
                    "| hit:",
                    hit_at_3,
                    "| recall:",
                    round(recall_at_3, 2),
                )

            result_rows.append(
                {
                    "id": item["id"],
                    "mode": mode,
                    "question": item["question"],
                    "expected_doc_ids": ";".join(expected_doc_ids),
                    "retrieved_doc_ids": ";".join(retrieved_doc_ids),
                    "no_answer": no_answer,
                    "hit_at_3": hit_at_3,
                    "recall_at_3": recall_at_3,
                }
            )

        hit_rate = sum(hit_scores) / len(hit_scores)
        mean_recall = sum(recall_scores) / len(recall_scores)

        summary_rows.append(
            {
                "mode": mode,
                "answerable_questions": len(hit_scores),
                "hit_at_3": hit_rate,
                "recall_at_3": mean_recall,
            }
        )

        print(
            f"\n{mode.upper()} SUMMARY"
            f"\nHit@3: {hit_rate:.2%}"
            f"\nRecall@3: {mean_recall:.2%}"
        )

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=result_rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(result_rows)

    with SUMMARY_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=summary_rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(summary_rows)

    print("\nSaved:")
    print(RESULTS_PATH)
    print(SUMMARY_PATH)


if __name__ == "__main__":
    evaluate()
