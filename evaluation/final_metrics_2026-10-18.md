# Final Evaluation Metrics — 2026-10-18

## Retrieval

| Mode | Answerable questions | Hit@3 | Recall@3 |
|---|---:|---:|---:|
| Dense | 11 | 100% | 100% |
| Hybrid | 11 | 100% | 95.45% |

Hybrid Q13 retrieved DOC003, DOC008 and DOC004 for an expected set of
DOC003 and DOC007, giving Q13 Recall@3 = 0.5.

## Claim Grounding

| Mode | Grounded issues | Grounding@3 |
|---|---:|---:|
| Dense | 6/6 | 100% |
| Hybrid | 6/6 | 100% |

CLM-002 contributes two HOTEL_OVER_LIMIT issue instances in the final
merged claim data.

## Real Claim Agent Evaluation

Source: `logs/agent_run_01.jsonl`

- Cases: 4
- Correct decisions: 4
- Decision Accuracy: 100%
- Verified writes: 4/4
- Evidence-scored cases: 3
- Average Evidence Coverage: 100%
- LLM calls: 21
- Prompt tokens: 41,990
- Completion tokens: 1,608
- Total tokens: 43,598
- Average tokens per case: 10,899.5
- Maximum prompt tokens: 3,877

## Real Correct Refusal Evaluation

Source: `logs/agent_run_04.jsonl`

A refusal counts as correct when:
1. the testset marks the case as `no_answer`;
2. the Agent returns `NO_ANSWER`;
3. `stopped_reason` is `final`;
4. at least one real LLM call was made.

Evidence references may still be present because they can document retrieved
policies showing that the requested rule is absent or unsupported.

Results:

- Cases: 4
- Correct refusals: 4
- Correct Refusal Rate: 100%
- LLM calls: 14
- Prompt tokens: 37,093
- Completion tokens: 780
- Total tokens: 37,873
- Maximum prompt tokens: 4,926

## Faithfulness

See `evaluation/manual_faithfulness_2026-10-18.md`.

Four of four real claim outputs had materially supported conclusions.
CLM-006 contains one minor lexical translation issue ("rice wine" instead
of "wine") that does not change the policy conclusion or decision.

This is a manual material-claim audit, not an automated faithfulness score.
