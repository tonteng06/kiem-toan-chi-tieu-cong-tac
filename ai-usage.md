# Khai báo sử dụng AI

## Công cụ AI đã sử dụng

Trong quá trình làm project, tôi có sử dụng ChatGPT của OpenAI để hỗ trợ học lý thuyết, giải thích code, gợi ý cách triển khai và hỗ trợ debug.

Tôi không sử dụng code do AI đưa ra mà không kiểm tra. Các phần code sau khi được gợi ý đều được tôi chạy thử trên máy, xem kết quả và tìm hiểu lại cách hoạt động để có thể giải thích khi bảo vệ.

## Phần tôi phụ trách

Trong nhóm, tôi phụ trách phần:

Data + RAG + Evaluation.

Công việc chính của tôi là chuẩn bị dữ liệu policy, xây dựng phần retrieval và đánh giá kết quả tìm kiếm của hệ thống.

## Day 1

Ở Day 1, tôi dùng ChatGPT để hỗ trợ các phần sau:

- Gợi ý cách thiết kế các class `Document`, `Chunk` và `SearchResult` bằng `dataclass`.
- Giải thích và hỗ trợ viết phần đọc dữ liệu policy từ file txt.
- Hỗ trợ viết phần chia document thành chunk.
- Giải thích lý do chọn `chunk_size = 500` và `overlap = 100`.
- Giải thích embedding và cách dùng model `all-MiniLM-L6-v2`.
- Hỗ trợ triển khai Dense Search.
- Hỗ trợ triển khai BM25 Search.
- Giải thích code Hybrid Search của Week 4 và hỗ trợ đưa logic này vào project.
- Hỗ trợ xây dựng class `Retriever` để dùng chung cho Dense và Hybrid.
- Hỗ trợ xây dựng bộ test gồm 15 câu hỏi.
- Hỗ trợ viết phần evaluation với Hit@3 và Recall@3.
- Hỗ trợ phân tích kết quả Dense và Hybrid.

Các file có sử dụng gợi ý hoặc code được hỗ trợ bởi ChatGPT gồm:

- `src/models/document.py`
- `src/rag/loader.py`
- `src/rag/chunker.py`
- `src/rag/embeddings.py`
- `src/rag/dense_search.py`
- `src/rag/bm25_search.py`
- `src/rag/hybrid_search.py`
- `src/rag/retriever.py`
- `tests/testset.jsonl`
- `evaluation/evaluate_retrieval.py`
- `evaluation/failure_analysis.txt`

File `w4/ex2_1_hybrid_search.py` là bài đã làm ở Week 4 và được tái sử dụng theo yêu cầu của project. ChatGPT chủ yếu giúp tôi đọc, hiểu và tích hợp lại logic của file này vào cấu trúc project hiện tại.

Một số câu hỏi chính tôi đã dùng với ChatGPT trong Day 1 là:

- Hướng dẫn tôi làm phần Data + RAG + Evaluation từng bước.
- Giải thích code để tôi có thể hiểu và bảo vệ.
- Hướng dẫn triển khai Dense Search, BM25 và Hybrid Search.
- Giải thích cách tính Hit@3 và Recall@3.
- Phân tích vì sao Hybrid Search không lấy được DOC007 trong Q13.

## Day 2

Ở Day 2, tôi tiếp tục dùng ChatGPT để hỗ trợ phân tích sâu các câu Q13, Q14 và Q15.

ChatGPT hỗ trợ tôi viết các lệnh kiểm tra để xem:

- Dense score
- BM25 raw score
- BM25 normalized score
- Hybrid score
- thứ hạng của từng document

Đối với Q13, tôi dùng ChatGPT để hiểu vì sao Dense Search lấy được cả DOC003 và DOC007 nhưng Hybrid Search lại làm DOC007 rơi xuống hạng 4.

Sau khi xem kết quả thực tế, tôi hiểu rằng DOC007 có Dense score cao hơn DOC004, nhưng DOC004 có BM25 score cao hơn. Khi kết hợp theo công thức Hybrid hiện tại:

`Hybrid = 0.3 * BM25_normalized + 0.7 * Dense`

DOC004 có Hybrid score nhỉnh hơn DOC007 một chút nên chiếm vị trí Top 3.

Đối với Q14, ChatGPT giúp tôi kiểm tra vì sao cả Dense và Hybrid đều lấy đúng DOC005 và DOC006.

Đối với Q15, tôi kiểm tra trường hợp có nhiều version của policy, cụ thể là DOC001 version 1.0 và DOC002 version 2.0. Kết quả cho thấy cả Dense và Hybrid đều retrieve được hai document này ở Top 2, trong đó DOC002 version 2.0 đứng trước DOC001 version 1.0. Qua trường hợp này tôi hiểu rằng Retriever có nhiệm vụ lấy evidence và giữ metadata về version, còn việc quyết định version nào đang có hiệu lực sẽ thuộc phần reasoning của Agent.


Các file ở Day 2 có sử dụng gợi ý hoặc code được hỗ trợ bởi ChatGPT gồm:

- `evaluation/day2_reasoning_analysis.py`
- `evaluation/day2_reasoning_cases.csv`
- `evaluation/day2_analysis.txt`

Trong đó, ChatGPT hỗ trợ tôi xây dựng script để kiểm tra Dense score, BM25 raw score, BM25 normalized score, Hybrid score và thứ hạng của document. Tôi đã trực tiếp chạy script, kiểm tra kết quả và đối chiếu lại với kết quả retrieval trước đó.


## Day 3

Ở Day 3, tôi tích hợp phần RAG của Member 1 với Claim, Business Rules và StateStore của Member 2 để kiểm tra khả năng grounding giữa quyết định nghiệp vụ và policy evidence.

ChatGPT hỗ trợ tôi:

- Kiểm tra các commit của Member 2 trước khi tích hợp.
- Giải thích `Claim`, `Expense`, `ClaimStatus` và state transition.
- Giải thích cách hoạt động của `StateStore`.
- Giải thích và kiểm tra `calculate_claim`.
- Hỗ trợ chạy regression test để bảo đảm phần RAG Day 1 và Day 2 không bị thay đổi.
- Hỗ trợ xây dựng claim-to-policy grounding evaluation.
- Phân biệt Claim-to-policy Grounding@3 với LLM faithfulness.

Các file Day 3 có sử dụng gợi ý hoặc code được hỗ trợ bởi ChatGPT gồm:

- `evaluation/evaluate_claim_grounding.py`
- `evaluation/claim_grounding_results.csv`
- `evaluation/claim_grounding_summary.csv`
- `evaluation/day3_analysis.txt`

Trong Day 3, tôi không viết lại Agent của Member 2. Tôi sử dụng output từ `calculate_claim()` làm business-rule evidence và kiểm tra xem Retriever của phần tôi có retrieve lại đúng policy document và version hay không.

Kết quả hiện tại:

Dense:
- Claim-to-policy Grounding@3: 100% (5/5 issues)

Hybrid:
- Claim-to-policy Grounding@3: 100% (5/5 issues)

Tôi hiểu rằng metric này chưa phải LLM faithfulness. Faithfulness, correct refusal và token usage chỉ có thể được đánh giá đầy đủ khi Agent end-to-end có output và usage information.

## Các prompt chính và phần code được AI hỗ trợ trực tiếp

Một số prompt chính tôi đã sử dụng trong quá trình làm phần của mình:

- "Hướng dẫn tôi làm phần Data + RAG + Evaluation từng bước."
- "Giải thích Dense Search, BM25 và Hybrid Search để tôi có thể hiểu và bảo vệ."
- "Giải thích cách tính Hit@3 và Recall@3."
- "Phân tích vì sao Hybrid Search không lấy được DOC007 trong Q13."
- "Giúp tôi kiểm tra trường hợp multi-policy và policy version ở Q14, Q15."
- "Hỗ trợ xây dựng claim-to-policy grounding evaluation và phân biệt nó với LLM faithfulness."

Các phần có đoạn code được ChatGPT gợi ý hoặc tạo bản nháp trực tiếp gồm:

- `src/models/document.py`
- `src/rag/loader.py`
- `src/rag/chunker.py`
- `src/rag/embeddings.py`
- `src/rag/dense_search.py`
- `src/rag/bm25_search.py`
- `src/rag/hybrid_search.py`
- `src/rag/retriever.py`
- `evaluation/evaluate_retrieval.py`
- `evaluation/day2_reasoning_analysis.py`
- `evaluation/evaluate_claim_grounding.py`

Tôi không xem các đoạn code AI tạo ra là kết quả cuối cùng ngay lập tức. Tôi đã trực tiếp chạy code, kiểm tra output, đối chiếu với policy corpus và chỉnh lại khi cần trước khi đưa vào project.

## Những gì tôi đã tự kiểm tra

Tôi đã trực tiếp chạy code trên máy và kiểm tra các phần sau:

- Load đủ 8 policy document.
- Kiểm tra metadata của document.
- Kiểm tra kết quả chunking.
- Kiểm tra embedding có 384 chiều.
- Chạy Dense Search.
- Chạy BM25 Search.
- Chạy Hybrid Search.
- Kiểm tra Retriever với hai mode Dense và Hybrid.
- Chạy bộ test 15 câu.
- Xác nhận testset có 4 câu no-answer và quan sát Retriever vẫn trả về các document gần nhất. Tôi chưa đánh giá correct refusal ở Agent layer vì Agent end-to-end chưa có output.
- Chạy evaluation Dense và Hybrid.
- Phân tích Q13, Q14 và các trường hợp multi-policy.

Kết quả Day 1 hiện tại:

Dense:

- Hit@3: 100%
- Recall@3: 100%

Hybrid:

- Hit@3: 100%
- Recall@3: 95.45%

Tôi cũng giữ lại Q13 là một trường hợp retrieval chưa tốt của Hybrid để phân tích, thay vì chỉnh kết quả chỉ để metric đẹp hơn.

## Day 4

Ở Day 4, tôi tiếp tục sử dụng ChatGPT để hỗ trợ xây dựng phần Agent Evaluation Infrastructure.

ChatGPT hỗ trợ tôi:

- Kiểm tra và giải thích phần ToolRegistry và Dispatcher được tích hợp từ Member 2.
- Giải thích cách ToolRegistry giới hạn các tool mà Agent được phép gọi.
- Giải thích cách Dispatcher validate tool name, arguments và xử lý lỗi thành `Error:` observation thay vì làm Agent loop bị crash.
- Hỗ trợ thiết kế Agent evaluation output contract.
- Hỗ trợ xây dựng validation cho các field:
  - `answer`
  - `decision`
  - `evidence_refs`
  - `usage.calls`
  - `usage.prompt_tokens`
  - `usage.completion_tokens`
  - `usage.max_prompt`
- Hỗ trợ phân biệt `NO_ANSWER` và `NEED_MORE_INFO`.
- Hỗ trợ xây dựng các per-case metrics:
  - Decision Correctness
  - Correct Refusal
  - Evidence Coverage
- Hỗ trợ xây dựng aggregate metrics:
  - Decision Accuracy
  - Correct Refusal Rate
  - Average Evidence Coverage
  - Total LLM Calls
  - Prompt Tokens
  - Completion Tokens
  - Total Tokens
  - Average Tokens per Case
  - Maximum Prompt Size
- Hỗ trợ viết unit tests cho Agent evaluation contract, per-case metrics và aggregate metrics.
- Giải thích sự khác nhau giữa Evidence Coverage và Faithfulness.
- Hỗ trợ viết tài liệu phân tích Day 4 bằng tiếng Việt.

Các file Day 4 có sử dụng gợi ý hoặc code được ChatGPT hỗ trợ gồm:

- `evaluation/agent_eval_contract.py`
- `evaluation/agent_metrics.py`
- `evaluation/agent_eval_summary.py`
- `tests/test_agent_eval_contract.py`
- `tests/test_agent_metrics.py`
- `tests/test_agent_eval_summary.py`
- `evaluation/day4_analysis.txt`

Trong Day 4, các Agent output được sử dụng trong unit tests là synthetic outputs.

Các synthetic outputs này chỉ được dùng để kiểm tra correctness của evaluation logic và metric formulas.

Tôi không sử dụng các synthetic outputs này để công bố final Agent performance.

Hiện tại các metric như Decision Accuracy, Correct Refusal Rate, Agent Evidence Coverage, Faithfulness và real token usage chỉ có thể được tính chính xác sau khi Agent end-to-end cung cấp real output và usage information.

Một số prompt chính tôi đã sử dụng với ChatGPT trong Day 4 gồm:

- "Giải thích ToolRegistry và Dispatcher để tôi có thể bảo vệ."
- "Giúp tôi thiết kế Agent evaluation output contract."
- "Giải thích sự khác nhau giữa NO_ANSWER và NEED_MORE_INFO."
- "Giúp tôi xây dựng Decision Correctness, Correct Refusal và Evidence Coverage."
- "Giúp tôi tổng hợp Decision Accuracy, Correct Refusal Rate và token usage."
- "Giải thích vì sao Evidence Coverage không phải Faithfulness."
- "Hỗ trợ viết unit tests cho Agent evaluation metrics."

## Cam kết

Tôi có sử dụng AI để hỗ trợ trong quá trình làm project, chủ yếu để học, giải thích code, gợi ý cách triển khai và hỗ trợ debug.

Tôi đã chạy và kiểm tra lại các phần code được AI hỗ trợ, đồng thời học lại lý thuyết liên quan để có thể giải thích và sửa code trực tiếp trong buổi bảo vệ.
