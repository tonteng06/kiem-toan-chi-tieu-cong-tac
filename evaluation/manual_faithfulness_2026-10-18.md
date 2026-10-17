# Manual Faithfulness Audit — 2026-10-18

## Scope

This audit reviews the four unique real-provider claim outputs in
`logs/agent_run_01.jsonl`.

Faithfulness is assessed manually against:
- claim data returned by `get_claim`;
- deterministic calculations returned by `calculate_claim`;
- policy text returned by `search_policy`;
- the evidence references included in the final answer.

This is a manual material-claim audit, not an automated LLM-as-judge metric.

## Results

| Claim | Decision | Result | Notes |
|---|---|---|---|
| CLM-001 | APPROVED | PASS | Hotel, meal, taxi, submission timing and totals are supported by claim data and DOC002/DOC003/DOC004/DOC005. |
| CLM-002 | ESCALATED | PASS | 4.8M VND/night exceeds the 1.5M VND Da Nang limit in DOC003; meal statement is supported by DOC004. |
| CLM-003 | NEED_MORE_INFO | PASS | Missing receipt for a 2.4M VND hotel expense is supported by DOC006 and DOC002; total and no-limit-violation statement agree with calculate_claim. |
| CLM-006 | REJECTED | PASS WITH MINOR WORDING NOTE | Alcohol is non-reimbursable under DOC004. The answer says "rice wine and beer" while the source description says "Ruou vang va bia" (wine and beer). This lexical translation issue does not affect the policy conclusion or decision. |

## Summary

- Outputs reviewed: 4
- Material conclusions supported: 4/4
- Unsupported material decisions: 0
- Minor wording issues: 1
- Automated faithfulness metric: not implemented

The result should therefore be reported as:

**4/4 real claim outputs had materially supported conclusions, with one minor lexical wording issue in CLM-006.**

Do not describe this as a perfect automated faithfulness score.
