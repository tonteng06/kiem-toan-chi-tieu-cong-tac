"""Read-only integration with Member 2's existing deterministic claim reasoner.

This is a bounded integration facade, not the future LLM Agent loop. The question
guides retrieval for an already structured claim; it is not a general QA API.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import json

from src.agent.business_rules import calculate_claim
from src.mcp_server.contracts import AuditPreviewOutput, SearchResultItem
from src.mcp_server.evidence import parse_search_payload, source_ref
from src.models.claim import Claim, ClaimStatus


SearchTool = Callable[[str, str, int], Awaitable[object]]
DECISIONS = {"APPROVED": "APPROVED", "REJECTED": "REJECTED", "ESCALATED": "ESCALATED",
             "NEED_MORE_INFO": "NEED_MORE_INFO"}
POLICY_QUERIES = {
    "DOC002@v2.0": "Travel Expense Policy version 2.0 submit within 10 calendar days",
    "DOC003@v1.0": "Hotel Reimbursement Limits domestic city per night",
    "DOC004@v1.0": "Meal Allowance Policy domestic international alcohol daily limit",
    "DOC005@v1.0": "Ground Transportation Policy business purpose luxury vehicle upgrades",
    "DOC006@v1.0": "Receipt Requirements individual expense 500000 receipt missing",
    "DOC007@v1.0": "Expense Exception Policy exceeds limit escalate manager review",
    "DOC008@v1.0": "International Travel Policy prior approval destination hotel limits",
}


def _validated_calculation(claim: Claim, payload: object) -> dict:
    """Reject corrupt or mismatched remote calculations before making a decision."""
    if not isinstance(payload, dict) or payload.get("claim_id") != claim.claim_id:
        raise ValueError("Error: calculation does not match the requested claim")
    if not isinstance(payload.get("recommended_status"), str) or payload["recommended_status"] not in DECISIONS:
        raise ValueError("Error: calculation has an invalid recommended_status")
    if not isinstance(payload.get("summary"), str) or not payload["summary"].strip():
        raise ValueError("Error: calculation requires a summary")
    if type(payload.get("total")) is not int or payload["total"] != sum(claim.total_by_category().values()):
        raise ValueError("Error: calculation total does not match the claim")
    if payload.get("totals") != claim.total_by_category():
        raise ValueError("Error: calculation category totals do not match the claim")
    for key in ("violations", "missing_data"):
        issues = payload.get(key)
        if not isinstance(issues, list):
            raise ValueError(f"Error: calculation requires a {key} list")
        for issue in issues:
            if not isinstance(issue, dict) or any(
                not isinstance(issue.get(field), str) or not issue[field].strip()
                for field in ("code", "message", "evidence", "outcome")
            ):
                raise ValueError("Error: calculation issue is missing provenance or reasoning")
            if issue["outcome"] not in {status.value for status in ClaimStatus}:
                raise ValueError("Error: calculation issue has an invalid outcome")
    return payload


def required_policy_refs(claim: Claim, calculation: dict) -> set[str]:
    """Evidence for the rules actually checked, including clean approvals.

    This handoff maps the current deterministic rules to their policy sources.
    It must be extended with any new rules added by the business-logic owner.
    """
    refs = {"DOC002@v2.0", "DOC006@v1.0"}
    categories = {expense.category for expense in claim.expenses}
    if "hotel" in categories:
        refs.add("DOC008@v1.0" if claim.is_international else "DOC003@v1.0")
    if "meal" in categories:
        refs.add("DOC004@v1.0")
    if "transport" in categories:
        refs.add("DOC005@v1.0")
    if claim.is_international:
        refs.add("DOC008@v1.0")
    issues = calculation["violations"] + calculation["missing_data"]
    refs.update(issue["evidence"] for issue in issues)
    if any(issue["code"] in {"HOTEL_OVER_LIMIT", "MEAL_OVER_LIMIT"} for issue in issues):
        refs.add("DOC007@v1.0")
    return refs


async def preview_audit(
    claim: Claim, question: str, search: SearchTool, *,
    mode: str = "hybrid", top_k: int = 3, max_searches: int = 6,
    calculation_result: dict | None = None,
) -> AuditPreviewOutput:
    """Retrieve, preserve evidence, run the existing rules, and return no writes.

    Missing required source/version => NO_ANSWER, independent of retrieval score.
    Follow-up searches repair missing policy coverage without changing RAG weights.
    Tool or schema errors propagate so the caller can log an explicit failure.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must not be empty")
    if mode not in {"dense", "hybrid"}:
        raise ValueError("mode must be dense or hybrid")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if type(max_searches) is not int or not 1 <= max_searches <= 10:
        raise ValueError("max_searches must be between 1 and 10")
    claim.__post_init__()
    evidence: list[SearchResultItem] = []
    by_identity = {}
    searches = []

    async def retrieve(query: str) -> None:
        payload = parse_search_payload(await search(query, mode, top_k))
        searches.append({"query": query, "mode": mode, "top_k": top_k, "results": payload["results"]})
        for item in payload["results"]:
            identity = (item["doc_id"], item["version"], item["chunk_id"])
            if identity in by_identity:
                previous = by_identity[identity]
                for field in ("title", "date", "owner", "content"):
                    if previous[field] != item[field]:
                        raise ValueError("source metadata/content changed during retrieval")
            else:
                by_identity[identity] = item
                evidence.append(item)

    await retrieve(question)
    calculation = _validated_calculation(
        claim, calculate_claim(claim) if calculation_result is None else calculation_result
    )
    required = required_policy_refs(claim, calculation)
    attempted = set()
    while len(searches) < max_searches:
        available = {source_ref(item) for item in evidence}
        missing = sorted(required - available)
        next_ref = next((ref for ref in missing if ref not in attempted and ref in POLICY_QUERIES), None)
        if next_ref is None:
            break
        attempted.add(next_ref)
        await retrieve(POLICY_QUERIES[next_ref])

    missing = sorted(required - {source_ref(item) for item in evidence})
    citations = [
        {"evidence_ref": source_ref(item), "doc_id": item["doc_id"], "version": item["version"],
         "chunk_id": item["chunk_id"], "title": item["title"]}
        for item in evidence if source_ref(item) in required
    ]
    decision = "NO_ANSWER" if missing else DECISIONS[calculation["recommended_status"]]
    reasoning = calculation["summary"]
    for issue in calculation["violations"] + calculation["missing_data"]:
        reasoning += f"; {issue['message']} [{issue['evidence']}]"
    return {
        "claim_id": claim.claim_id, "question": question, "decision": decision,
        "reason": ("Missing required policy evidence: " + ", ".join(missing)) if missing else reasoning,
        "required_evidence_refs": sorted(required), "missing_evidence_refs": missing,
        "evidence": evidence, "citations": citations, "searches": searches,
        "calculation": calculation, "read_only": True,
    }


async def preview_audit_via_mcp(client, claim: Claim, question: str, **options) -> AuditPreviewOutput:
    """Use dynamic tools/list discovery and the agreed search_policy tool."""
    from src.mcp_server.client import call_tool, search_payload

    async def search(query: str, mode: str, top_k: int) -> object:
        response = await call_tool(client, "search_policy", {"query": query, "mode": mode, "top_k": top_k})
        return search_payload(response)

    return await preview_audit(claim, question, search, **options)


async def preview_registered_claim_via_mcp(
    client, claim_id: str, question: str, **options,
) -> AuditPreviewOutput:
    """Day 4: get_claim + calculate_claim through MCP and TV2's real registry.

    All claim data and business reasoning come from the server. The existing
    evidence gate still controls the final read-only decision.
    """
    from src.mcp_server.client import dispatch_mcp

    async def observe(name: str, args: dict) -> dict:
        observation = await dispatch_mcp(client, name, args)
        if observation.startswith("Error:"):
            raise ValueError(observation)
        return json.loads(observation)

    raw_claim = await observe("get_claim", {"claim_id": claim_id})
    if raw_claim.get("claim_id") != claim_id:
        raise ValueError("Error: get_claim returned a different claim")
    claim = Claim.from_dict(raw_claim)
    calculation = _validated_calculation(
        claim, await observe("calculate_claim", {"claim_id": claim_id})
    )

    async def search(query: str, mode: str, top_k: int) -> object:
        return await observe("search_policy", {"query": query, "mode": mode, "top_k": top_k})

    return await preview_audit(claim, question, search, calculation_result=calculation, **options)
