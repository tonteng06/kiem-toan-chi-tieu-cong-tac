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
- Kiểm tra 4 câu no-answer.
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

## Cam kết

Tôi có sử dụng AI để hỗ trợ trong quá trình làm project, chủ yếu để học, giải thích code, gợi ý cách triển khai và hỗ trợ debug.

Tôi đã chạy và kiểm tra lại các phần code được AI hỗ trợ, đồng thời học lại lý thuyết liên quan để có thể giải thích và sửa code trực tiếp trong buổi bảo vệ.
