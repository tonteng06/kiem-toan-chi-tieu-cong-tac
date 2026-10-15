# Member 1 Handoff - Data + RAG + Evaluation

## Scope

Member 1 is responsible for:

- policy corpus;
- policy metadata;
- document/chunk/search-result data models;
- policy loader;
- chunking;
- Dense retrieval;
- BM25 retrieval;
- Hybrid retrieval;
- unified Retriever interface;
- retrieval testset;
- retrieval evaluation;
- retrieval failure analysis;
- claim-to-policy grounding evaluation;
- Agent evaluation output contract;
- per-case Agent evaluation metrics;
- aggregate Agent evaluation metrics;
- token-usage evaluation infrastructure.

Member 1 does not own the final LLM Agent orchestration or MCP write-tool implementation.

## Policy Corpus

The policy corpus contains 8 synthetic documents: DOC001-DOC008.

Each document includes:

- `doc_id`
- `title`
- `version`
- `date`
- `owner`

The corpus is synthetic and was created specifically for academic evaluation of the Travel Expense Audit Agent.

Corpus provenance is documented in:

`data/policies/README.md`

## RAG Implementation

Embedding model:

`sentence-transformers/all-MiniLM-L6-v2`

Chunking:

- chunk size: 500 characters
- overlap: 100 characters

Retrieval modes:

- Dense
- BM25
- Hybrid

Hybrid formula:

`Hybrid = 0.3 * normalized_BM25 + 0.7 * Dense`

The normalization and fusion idea is reused from:

`w4/ex2_1_hybrid_search.py`

The current implementation adapts tokenization and project structure, so it should not be described as an exact unchanged copy of the Week 4 file.

## Testset

File:

`tests/testset.jsonl`

Current testset:

- 15 questions total
- 11 answerable questions
- 4 no-answer questions

No-answer questions:

- Q09
- Q10
- Q11
- Q12

The Retriever still returns nearest documents for no-answer questions because retrieval is a ranking stage.

Correct refusal must be evaluated at the Agent layer.

## Retrieval Evaluation

Script:

`evaluation/evaluate_retrieval.py`

Metrics are calculated at document level using Top-3 unique document IDs.

Current results:

### Dense

- Hit@3: 100.00%
- Recall@3: 100.00%

### Hybrid

- Hit@3: 100.00%
- Recall@3: 95.45%

Detailed results:

- `evaluation/results.csv`
- `evaluation/summary.csv`

## Main Retrieval Failure

Q13 expects:

- DOC003
- DOC007

Dense Top-3:

- DOC003
- DOC008
- DOC007

Hybrid Top-3:

- DOC003
- DOC008
- DOC004

Hybrid misses DOC007 at Top-3.

DOC004 receives a slightly higher BM25 contribution than DOC007, causing DOC007 to move from rank 3 to rank 4 after Hybrid fusion.

Detailed analysis:

- `evaluation/failure_analysis.txt`
- `evaluation/day2_analysis.txt`
- `evaluation/day2_reasoning_cases.csv`

This failure is intentionally retained instead of tuning the weights only to improve the metric.

## Claim-to-Policy Grounding

Script:

`evaluation/evaluate_claim_grounding.py`

Current results:

### Dense

- Grounding@3: 100% (5/5 issues)

### Hybrid

- Grounding@3: 100% (5/5 issues)

This metric verifies whether deterministic business-rule issues can be retrieved back to the expected policy document and version.

It is not LLM faithfulness.

The issue messages may already contain policy-specific terms or values, so this metric should be interpreted as an integration compatibility check between the business-rule layer and the Retriever.

Artifacts:

- `evaluation/claim_grounding_results.csv`
- `evaluation/claim_grounding_summary.csv`
- `evaluation/day3_analysis.txt`

## Agent Evaluation Infrastructure

Day 4 prepares Member 1's evaluation layer for the final end-to-end Agent.

Files:

- `evaluation/agent_eval_contract.py`
- `evaluation/agent_metrics.py`
- `evaluation/agent_eval_summary.py`
- `evaluation/day4_analysis.txt`

The minimum Agent evaluation output contains:

- `answer`
- `decision`
- `evidence_refs`
- `usage.calls`
- `usage.prompt_tokens`
- `usage.completion_tokens`
- `usage.max_prompt`

Valid decisions currently include:

- `APPROVED`
- `REJECTED`
- `ESCALATED`
- `NEED_MORE_INFO`
- `NO_ANSWER`

Per-case metrics:

- Decision Correctness
- Correct Refusal
- Evidence Coverage

Aggregate metrics:

- Decision Accuracy
- Correct Refusal Rate
- Average Evidence Coverage
- Total LLM Calls
- Prompt Tokens
- Completion Tokens
- Total Tokens
- Average Tokens per Case
- Maximum Prompt Size

`NO_ANSWER` means policy evidence is insufficient.

`NEED_MORE_INFO` means the relevant policy exists but required claim information is missing.

Evidence Coverage is not the same as LLM Faithfulness.

Synthetic Agent outputs are used only in unit tests to verify evaluation logic.
They are not reported as final Agent performance.

## Tests

Current integrated test result:

`69 passed`

Relevant tests:

- `tests/test_claim.py`
- `tests/test_state_store.py`
- `tests/test_business_rules.py`
- `tests/test_dispatcher.py`
- `tests/test_agent_eval_contract.py`
- `tests/test_agent_metrics.py`
- `tests/test_agent_eval_summary.py`

## AI Usage

AI usage is declared in:

`ai-usage.md`

It includes:

- tool used;
- parts supported by AI;
- representative prompts;
- code/files directly assisted by AI;
- limitations of current evaluation.

## Current Member 1 Limitations

1. Fixed character chunking may split words or sentences.
2. Dense and Hybrid searchers currently compute their own chunk embedding matrices during Retriever initialization.
3. Hybrid retrieval is weaker than Dense on Q13 with the current 0.3/0.7 baseline.
4. Claim-to-policy Grounding@3 is not an independent LLM faithfulness metric.
5. Correct refusal cannot be measured until the final Agent returns explicit no-answer/refusal output.
6. Token usage and token cost cannot be measured until the final Agent exposes usage information.

## Required Input from Agent Layer for Final Evaluation

For end-to-end evaluation, Member 1 needs the Agent to expose at least:

- generated answer;
- final decision;
- evidence references;
- explicit `NO_ANSWER` or refusal result when policy evidence is insufficient;
- LLM call count;
- prompt token count;
- completion token count;
- maximum prompt size.

With these outputs, Member 1 can evaluate:

- Decision Accuracy;
- Correct Refusal Rate;
- Agent Evidence Coverage;
- answer faithfulness;
- token usage per question;
- token cost per question.

## Final Integration Items Not Yet Completed

These are group-level integration tasks rather than Member 1 RAG implementation tasks:

- complete Agent loop;
- final LLM API usage interface;
- correct refusal evaluation;
- token usage/cost evaluation;
- MCP write tool;
- write-then-read verification;
- at least 3 real JSONL run logs;
- final README reproduction commands;
- Makefile;
- `.env.example`;
- final report.

## Reproduction Commands for Member 1

Run unit tests:

`PYTHONPATH=. python -m pytest -q`

Run retrieval evaluation:

`PYTHONPATH=. python evaluation/evaluate_retrieval.py`

Run Day 2 reasoning analysis:

`PYTHONPATH=. python evaluation/day2_reasoning_analysis.py`

Run claim-to-policy grounding evaluation:

`PYTHONPATH=. python evaluation/evaluate_claim_grounding.py`

## Important Git Checkpoint

Latest completed Day 4 checkpoint before this cleanup:

`cbe9c65 - Translate evaluation analyses to Vietnamese`
