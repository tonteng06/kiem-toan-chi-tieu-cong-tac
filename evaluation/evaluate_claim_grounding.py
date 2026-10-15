import csv
import json
from pathlib import Path

from src.agent.business_rules import calculate_claim
from src.models.claim import Claim
from src.rag.chunker import chunk_documents
from src.rag.loader import load_documents
from src.rag.retriever import Retriever


CLAIMS_PATH = Path("data/claims/claims.json")
RESULTS_PATH = Path("evaluation/claim_grounding_results.csv")
SUMMARY_PATH = Path("evaluation/claim_grounding_summary.csv")

TOP_K = 3
MODES = ["dense", "hybrid"]


def load_claims() -> list[Claim]:
    raw = json.loads(
        CLAIMS_PATH.read_text(encoding="utf-8")
    )
    return [Claim.from_dict(item) for item in raw]


def top_document_refs(
    retriever: Retriever,
    query: str,
    mode: str,
    top_k: int,
) -> list[str]:
    """
    Return unique document references such as DOC003@v1.0.

    Retriever ranks chunks, but this evaluation is document-level.
    Therefore duplicate chunks from the same document/version are removed.
    """
    results = retriever.retrieve(
        query=query,
        mode=mode,
        top_k=len(retriever.chunks),
    )

    refs: list[str] = []

    for result in results:
        ref = (
            f"{result.chunk.doc_id}"
            f"@v{result.chunk.version}"
        )

        if ref not in refs:
            refs.append(ref)

        if len(refs) == top_k:
            break

    return refs


def main() -> None:
    claims = load_claims()

    documents = load_documents("data/policies")
    chunks = chunk_documents(documents)
    retriever = Retriever(chunks)

    result_rows: list[dict] = []
    summary_rows: list[dict] = []

    for mode in MODES:
        total_issues = 0
        grounded_issues = 0

        print("\n" + "=" * 80)
        print(f"{mode.upper()} CLAIM GROUNDING")

        for claim in claims:
            decision = calculate_claim(claim)

            issues = (
                decision["violations"]
                + decision["missing_data"]
            )

            if not issues:
                print(
                    f"{claim.claim_id} | "
                    f"{decision['recommended_status']} | "
                    "NO ISSUES"
                )
                continue

            for issue in issues:
                total_issues += 1

                expected_ref = issue["evidence"]

                retrieved_refs = top_document_refs(
                    retriever=retriever,
                    query=issue["message"],
                    mode=mode,
                    top_k=TOP_K,
                )

                grounded = (
                    expected_ref in retrieved_refs
                )

                if grounded:
                    grounded_issues += 1

                result_rows.append(
                    {
                        "mode": mode,
                        "claim_id": claim.claim_id,
                        "recommended_status": decision[
                            "recommended_status"
                        ],
                        "issue_code": issue["code"],
                        "message": issue["message"],
                        "expected_ref": expected_ref,
                        "retrieved_refs": ";".join(
                            retrieved_refs
                        ),
                        "grounded_at_3": int(grounded),
                    }
                )

                print(
                    f"{claim.claim_id} | "
                    f"{issue['code']} | "
                    f"expected={expected_ref} | "
                    f"retrieved={retrieved_refs} | "
                    f"grounded={grounded}"
                )

        grounding_rate = (
            grounded_issues / total_issues
            if total_issues
            else 0.0
        )

        summary_rows.append(
            {
                "mode": mode,
                "total_issues": total_issues,
                "grounded_issues": grounded_issues,
                "grounding_at_3": grounding_rate,
            }
        )

        print()
        print(f"{mode.upper()} SUMMARY")
        print(f"Total issues: {total_issues}")
        print(
            f"Grounded issues: "
            f"{grounded_issues}"
        )
        print(
            f"Grounding@3: "
            f"{grounding_rate:.2%}"
        )

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "mode",
                "claim_id",
                "recommended_status",
                "issue_code",
                "message",
                "expected_ref",
                "retrieved_refs",
                "grounded_at_3",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(result_rows)

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "mode",
                "total_issues",
                "grounded_issues",
                "grounding_at_3",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\nSaved:")
    print(RESULTS_PATH)
    print(SUMMARY_PATH)


if __name__ == "__main__":
    main()
