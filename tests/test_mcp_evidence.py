"""Evidence/bridge unit tests; no SDK, model download, or event-loop IO required."""
import copy
import json
import unittest
from datetime import date
from pathlib import Path

from src.mcp_server.agent_bridge import preview_audit
from src.mcp_server.evidence import parse_search_payload, serialize_search_result, source_ref
from src.models.claim import Claim, Expense
from src.models.document import Chunk, SearchResult
from src.rag.chunker import chunk_documents
from src.rag.loader import load_documents


ROOT = Path(__file__).parents[1]


def immediate(coroutine):
    """Drive only immediate fake awaits; not a substitute for MCP transport tests."""
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Unit-test coroutine attempted real async IO")


def hotel_claim():
    return Claim("DEMO", "Employee", "Da Nang", "VN", date(2026, 10, 12),
                 date(2026, 10, 13), date(2026, 10, 14), "Meeting",
                 [Expense("hotel", 1_800_000, date(2026, 10, 12), "One night", True)])


def policy_records():
    return [serialize_search_result(SearchResult(chunk, 0.4, "hybrid", 0.5, 1.2))
            for chunk in chunk_documents(load_documents(ROOT / "data" / "policies"))]


class EvidenceSerializationTests(unittest.TestCase):
    def test_full_provenance_and_scores_survive_json(self):
        chunk = Chunk("DOC003_CH001", "DOC003", "Hotel limits", "1.0", "2026-02-01", "Finance", "Exact source content")
        result = SearchResult(chunk, 0.7, "hybrid", 0.8, 2.0)
        item = serialize_search_result(result)
        decoded = parse_search_payload(json.loads(json.dumps({"results": [item]})))["results"][0]
        for field in ("chunk_id", "doc_id", "title", "version", "date", "owner", "content"):
            self.assertEqual(decoded[field], getattr(chunk, field))
        self.assertEqual((decoded["score"], decoded["dense_score"], decoded["bm25_score"]), (0.7, 0.8, 2.0))
        self.assertEqual(source_ref(decoded), "DOC003@v1.0")

    def test_dense_null_optional_scores_preserved(self):
        chunk = Chunk("A", "D", "T", "v2.0", "2026-01-01", "F", "Content")
        item = serialize_search_result(SearchResult(chunk, 0.7, "dense", 0.7, None))
        self.assertIsNone(item["bm25_score"])
        self.assertEqual(source_ref(item), "D@v2.0")

    def test_missing_provenance_is_error(self):
        original = policy_records()[0]
        for key in original:
            with self.subTest(key=key):
                item = original.copy()
                del item[key]
                with self.assertRaises(ValueError):
                    parse_search_payload({"results": [item]})

    def test_nonfinite_or_boolean_scores_are_error(self):
        for score in (float("nan"), float("inf"), True, "0.9"):
            with self.subTest(score=score), self.assertRaises(ValueError):
                parse_search_payload({"results": [{**policy_records()[0], "score": score}]})

    def test_empty_evidence_is_valid_but_malformed_response_is_not(self):
        self.assertEqual(parse_search_payload({"results": []}), {"results": []})
        for payload in (None, [], {}, {"results": {}}, {"results": [None]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_search_payload(payload)


class AgentBridgeTests(unittest.TestCase):
    def test_hotel_case_escalates_with_citations_without_mutation(self):
        claim = hotel_claim()
        before = claim.to_dict()
        original_file = (ROOT / "data/claims/claims.json").read_bytes()
        async def search(query, mode, top_k):
            return {"results": policy_records()}
        result = immediate(preview_audit(claim, "Audit hotel claim", search))
        self.assertEqual(result["decision"], "ESCALATED")
        self.assertFalse(result["missing_evidence_refs"])
        self.assertIn("DOC003@v1.0", result["required_evidence_refs"])
        self.assertIn("DOC007@v1.0", result["required_evidence_refs"])
        self.assertTrue(result["citations"])
        self.assertTrue(result["read_only"])
        self.assertEqual(claim.to_dict(), before)
        self.assertEqual((ROOT / "data/claims/claims.json").read_bytes(), original_file)

    def test_missing_exception_policy_triggers_bounded_followup(self):
        records = policy_records()
        calls = []
        async def search(query, mode, top_k):
            calls.append((query, mode, top_k))
            return {"results": [r for r in records if r["doc_id"] != "DOC007"] if len(calls) == 1 else [r for r in records if r["doc_id"] == "DOC007"]}
        result = immediate(preview_audit(hotel_claim(), "Hotel limit", search))
        self.assertEqual(result["decision"], "ESCALATED")
        self.assertEqual(len(calls), 2)
        self.assertIn("Expense Exception Policy", calls[1][0])
        self.assertEqual(calls[0][1:], ("hybrid", 3))

    def test_high_score_does_not_replace_missing_evidence(self):
        async def search(query, mode, top_k):
            return {"results": [{**r, "score": 1.0} for r in policy_records() if r["doc_id"] == "DOC003"]}
        result = immediate(preview_audit(hotel_claim(), "Hotel limit", search, max_searches=2))
        self.assertEqual(result["decision"], "NO_ANSWER")
        self.assertEqual(len(result["searches"]), 2)
        self.assertIn("DOC007@v1.0", result["missing_evidence_refs"])

    def test_old_policy_does_not_satisfy_required_version(self):
        async def search(query, mode, top_k):
            return {"results": [r for r in policy_records() if r["doc_id"] != "DOC002"]}
        result = immediate(preview_audit(hotel_claim(), "Deadline", search))
        self.assertEqual(result["decision"], "NO_ANSWER")
        self.assertIn("DOC002@v2.0", result["missing_evidence_refs"])

    def test_tool_error_propagates_without_decision(self):
        async def search(query, mode, top_k):
            raise RuntimeError("retriever unavailable")
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            immediate(preview_audit(hotel_claim(), "Hotel limit", search))

    def test_bad_schema_propagates_without_decision(self):
        async def search(query, mode, top_k):
            return {"results": [{"content": "unsupported answer"}]}
        with self.assertRaises(ValueError):
            immediate(preview_audit(hotel_claim(), "Hotel limit", search))

    def test_every_sample_maps_to_expected_agent_decision(self):
        expected = ["APPROVED", "ESCALATED", "NEED_MORE_INFO", "ESCALATED", "APPROVED", "REJECTED", "ESCALATED"]
        async def search(query, mode, top_k):
            return {"results": policy_records()}
        samples = json.loads((ROOT / "data/claims/claims.json").read_text(encoding="utf-8"))
        for raw, decision in zip(samples, expected):
            with self.subTest(claim_id=raw["claim_id"]):
                result = immediate(preview_audit(Claim.from_dict(raw), "Audit claim", search))
                self.assertEqual(result["decision"], decision)

    def test_conflicting_source_content_is_rejected(self):
        count = 0
        records = policy_records()
        async def search(query, mode, top_k):
            nonlocal count
            count += 1
            selected = copy.deepcopy([r for r in records if r["doc_id"] == "DOC003"])
            if count > 1:
                selected[0]["content"] = "Changed policy mid-run"
            return {"results": selected}
        with self.assertRaisesRegex(ValueError, "changed"):
            immediate(preview_audit(hotel_claim(), "Hotel limit", search))

    def test_search_budget_validation(self):
        async def search(query, mode, top_k):
            self.fail("invalid inputs must not call a tool")
        for budget in (0, 11, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                immediate(preview_audit(hotel_claim(), "Hotel limit", search, max_searches=budget))


if __name__ == "__main__":
    unittest.main()
