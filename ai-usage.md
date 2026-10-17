# Khai báo sử dụng AI — Thành viên 3

**Họ và tên:** Lê Thanh Đại Dương
**Phần phụ trách:** MCP và tích hợp hệ thống
**Cập nhật:** 17/10/2026

## 1. Công cụ AI đã sử dụng

Trong quá trình thực hiện project, tôi sử dụng ChatGPT và Codex của OpenAI để hỗ trợ tìm hiểu kiến thức, giải thích mã nguồn, đề xuất cách triển khai, viết và sửa code, kiểm thử, rà soát lỗi tích hợp và soạn tài liệu.

## 2. Phần tôi phụ trách

Tôi phụ trách lớp MCP và kết nối các thành phần của nhóm, gồm:

- Xây dựng MCP server/client, khám phá công cụ khi chạy qua `tools/list` và gọi công cụ qua `tools/call`.
- Kết nối MCP với bộ truy xuất policy của Thành viên 1 và registry, quy tắc nghiệp vụ, bộ lưu trạng thái của Thành viên 2.
- Chuyển đổi schema và kết quả MCP sang định dạng Agent sử dụng.
- Triển khai ghi quyết định, kiểm tra bằng chứng và đọc lại trạng thái ngay sau ghi.
- Bổ sung kiểm thử, demo, log và hướng dẫn chạy để phục vụ tích hợp và tái lập kết quả.

Agent và kết nối nhà cung cấp LLM của Thành viên 2 được tích hợp từ nhánh của thành viên đó. Việc merge và kiểm thử tích hợp không được tính là tôi tự xây dựng toàn bộ Agent hoặc RAG.

## 3. Nội dung được AI hỗ trợ theo tiến độ

### Ngày 13/10 — Tìm kiếm policy và đọc trạng thái

AI hỗ trợ xây dựng MCP server/client, công cụ tìm policy và đọc trạng thái claim. Công cụ tìm kiếm sử dụng `Retriever` có sẵn, giữ lại nội dung cùng metadata document, version và chunk để truy vết nguồn. Công cụ đọc trạng thái sử dụng `StateStore` của nhóm.

AI hỗ trợ kiểm tra import, cú pháp, handler và viết smoke test cho discovery/call. Retrieval ở bước này dùng embedding xác định trước, chỉ xác nhận kết nối và cấu trúc dữ liệu. Kiểm tra stdio trong phiên ngày 13/10 chưa hoàn tất do event loop của môi trường bị treo.

### Ngày 14/10, rà soát ngày 15/10 — Chuẩn hóa và sửa lỗi tích hợp

AI hỗ trợ chuẩn hóa package thành `src/mcp_server`, tên công cụ thành `search_policy`, thống nhất quyết định có thể lưu và phản hồi lỗi với tiền tố `Error:`. `NO_ANSWER` được phân biệt với quyết định lưu vào trạng thái claim.

Trong đợt rà soát trước tích hợp, Codex trực tiếp sửa model claim, quy tắc nghiệp vụ và dữ liệu mẫu: kiểm tra kiểu dữ liệu, phân bổ tiền theo ngày/đêm, mục đích di chuyển và phê duyệt nâng hạng. Các thay đổi ngoài lớp MCP này được khai báo tại đây và trong `progress/2026-10-14-tv3.md`. Ghi chú tiến độ chưa có ngày xác nhận của Thành viên 2; tài liệu này không coi đó là xác nhận đã được cung cấp.

Theo log đợt rà soát, Codex chạy được 75 tests và 71 subtests, đồng thời chạy smoke stdio thành công. Demo dùng embedding thật ở bước này bị timeout và không được ghi nhận là thành công.

### Ngày 15/10 — Kết nối registry và giao diện cho Agent

AI hỗ trợ tích hợp `main` sau phần việc của Thành viên 1, tái sử dụng registry/dispatcher của Thành viên 2 và bổ sung adapter cho các công cụ đọc claim, tính toán, tìm policy và đọc trạng thái.

AI hỗ trợ chuyển đổi schema MCP, chuẩn hóa kết quả JSON/lỗi, xây dựng `McpToolbox` đồng bộ với một phiên MCP trên luồng riêng, cache discovery, refresh và đóng tài nguyên. Kiểm thử bổ sung bao gồm công cụ được thêm sau kết nối, đối số sai, lỗi server, timeout, subprocess bị dừng và stdout JSON-RPC.

Kết quả cuối đợt này được ghi nhận là 177 tests và 71 subtests đạt, cùng smoke adapter stdio thành công. Đây là kiểm tra lớp công cụ và tích hợp; chưa có lượt chạy LLM thật được xác nhận trong đợt này.

### Ngày 16/10 — Ghi quyết định và đọc lại để xác minh

AI hỗ trợ triển khai `submit_decision` dựa trên `StateStore` và quy tắc nghiệp vụ của Thành viên 2. Kiểm tra bao gồm lý do, nguồn policy, quyết định phù hợp và chuyển trạng thái hợp lệ.

AI hỗ trợ tạo demo trên bản sao trạng thái, gọi ghi rồi đọc lại ngay, đối chiếu trạng thái, lý do, thời điểm cập nhật và dữ liệu JSON thực tế. Ba log `logs/run_01.jsonl` đến `logs/run_03.jsonl` ghi nhận retrieval thật bằng MiniLM và thao tác MCP/lưu trạng thái thật. Quyết định trong các demo dựa trên quy tắc xác định; số lượt gọi và token LLM bằng 0.

AI hỗ trợ bổ sung Makefile, hướng dẫn thiết lập, `.env.example`, tài liệu bàn giao và cấu hình truyền cho subprocess. Theo tiến độ đã lưu, pytest đạt 218 tests và 71 subtests tại checkpoint này; các smoke stdio và ghi/đọc lại cũng đạt. Các kết quả này thuộc lần chạy ngày 16/10, không thay cho kiểm chứng lại ở ngày cuối.

### Ngày 17/10 — Rà soát cuối và kết nối Agent với MCP

AI hỗ trợ đọc tài liệu phân công và yêu cầu nộp bài, rà soát code, phát hiện lỗi thiếu API Agent làm pytest dừng khi thu thập test, rồi merge nhánh `origin/tv2-final-agent` đã có sẵn trong repository. Lịch sử và tác giả các commit của Thành viên 2 được giữ lại.

AI hỗ trợ bổ sung `scripts/demo_agent_mcp.py` để kết nối Agent/LLM hiện có với MCP, trạng thái riêng và bước đọc lại sau ghi. Lớp kiểm tra bổ sung yêu cầu nguồn trích dẫn khi ghi phải thực sự được truy xuất kèm nội dung trong lượt chạy đó.

Các test mới dùng phản hồi model và retrieval theo kịch bản để kiểm tra `APPROVED`, `ESCALATED`, `NEED_MORE_INFO`, `REJECTED` và nguồn trích dẫn chưa được truy xuất. Các test gọi handler ghi thật và đọc lại file; chúng không phải lượt chạy LLM thật qua stdio.

AI đồng thời cập nhật README, Makefile, cấu hình mẫu, checklist bàn giao và tiến độ. Kết quả cùng giới hạn kiểm chứng được trình bày ở mục 6.

## 4. Các yêu cầu chính đã giao cho AI

Các nội dung dưới đây tóm tắt yêu cầu làm việc, không phải bản chép nguyên văn toàn bộ lịch sử hội thoại:

- Phân tích tài liệu phân công và thực hiện phần MCP/tích hợp của Thành viên 3 theo từng ngày.
- Giải thích discovery, schema, lời gọi công cụ và xử lý lỗi để phục vụ việc học và bảo vệ.
- Kết nối RAG, registry và trạng thái claim bằng giao diện sẵn có của các thành viên.
- Kiểm tra contract, viết regression test và xử lý lỗi tích hợp phát hiện được.
- Xây dựng demo ghi rồi đọc lại, lưu log và giữ nguyên dữ liệu claim mẫu.
- Rà soát yêu cầu ngày cuối, chỉ rõ kết quả đã chạy được và mục còn thiếu trước khi nộp.
- Hỗ trợ thao tác Git và viết tài liệu bàn giao, tiến độ, khai báo AI bằng tiếng Việt.

## 5. Các file có AI hỗ trợ trực tiếp

Danh sách tập trung vào phần TV3 và các thay đổi liên quan đã ghi trong tiến độ. Các file có thể chứa cả code sẵn có của nhóm và phần AI hỗ trợ bổ sung; việc liệt kê không có nghĩa toàn bộ file do AI tạo ra. Các tên file trong cùng một ô sử dụng thư mục của đường dẫn đầu tiên, trừ khi đã ghi đường dẫn khác.

| Nhóm công việc | File liên quan |
| --- | --- |
| MCP server/client và contract | `src/mcp_server/server.py`, `client.py`, `contracts.py` |
| Adapter, kết nối Agent và bằng chứng | `src/mcp_server/adapters.py`, `registry_adapter.py`, `agent_bridge.py`, `evidence.py` |
| Smoke test và demo | `scripts/smoke_stdio.py`, `smoke_mcp_tools.py`, `smoke_registry.py`, `smoke_adapter.py`, `demo_readonly_audit.py`, `demo_verified_audit.py`, `demo_agent_mcp.py` |
| Kiểm thử MCP và tích hợp | `tests/test_mcp_sdk.py`, `test_mcp_registry.py`, `test_adapters.py`, `test_mcp_evidence.py`, `test_mcp_write.py`, `test_agent_mcp_contract.py` |
| Sửa lỗi model/quy tắc trước tích hợp | `src/models/claim.py`, `src/agent/business_rules.py`, `data/claims/claims.json`, `tests/test_regressions.py` |
| Thiết lập và tài liệu | `README.md`, `Makefile`, `.env.example`, `ai-usage.md`, tài liệu MCP/tích hợp trong `docs/` và tiến độ TV3 trong `progress/` |
| Bằng chứng chạy tự động | `evaluation/day4_adapter_smoke.json`, `day6_validation.json`, `day7_validation.json`; `logs/run_01.jsonl` đến `logs/run_03.jsonl` |

## 6. Kết quả kiểm chứng và giới hạn

Các kết quả dưới đây được Codex chạy hoặc kiểm tra trong môi trường làm việc và ghi lại trong repository. Tôi không trình bày kết quả tự động này như xác nhận rằng mình đã tự chạy lại hoặc đã hiểu đầy đủ mọi thay đổi.

| Nội dung | Kết quả ghi nhận đến phiên rà soát 17/10 |
| --- | --- |
| Regression ngày cuối | 236 tests và 71 subtests đạt; 21 kiểm tra phụ thuộc event loop/transport chưa được xác nhận trong lệnh chạy chọn lọc. Chưa phải toàn bộ pytest đạt. |
| Retrieval bằng MiniLM thật | Chạy lại trên 15 câu, gồm 11 câu có đáp án và 4 câu `no_answer`. Trên 11 câu có đáp án: Dense Hit@3/Recall@3 = 100%/100%; Hybrid = 100%/95,45%. |
| Trường hợp retrieval chưa tốt | Q13 của Hybrid thiếu DOC007 trong Top-3, recall của câu bằng 0,5; không chỉnh metric để che kết quả. |
| Ghi và đọc lại qua MCP | Ba log thực tế ngày 16/10 có retrieval, lưu trạng thái và xác minh file; LLM usage bằng 0. |
| Test Agent/MCP ngày cuối | Bốn quyết định và chặn citation chưa truy xuất được kiểm tra bằng phản hồi theo kịch bản; không dùng làm metric Agent cuối cùng. |
| Lượt chạy LLM thật | Chưa thực hiện trong phiên rà soát ngày cuối vì chưa cấu hình API key của nhà cung cấp. |
| Chất lượng Agent và token | Chưa có kết quả LLM thật để công bố Decision Accuracy, Correct Refusal, Evidence Coverage, Faithfulness hoặc token usage thực tế. |
| Chạy từ môi trường mới | Đã sao chép file và tạo venv; cài dependency thất bại vì package index của môi trường không tìm được `mcp>=2,<3`. Chưa xác nhận cold start hoàn chỉnh. |
| Stdio ngày cuối | Bị chặn do event loop/socket của môi trường; smoke đạt ở ngày trước không được ghi thành kết quả chạy mới. |

Retrieval tốt, test theo kịch bản đạt hoặc log ghi file thành công chưa đủ để kết luận Agent trả lời đúng, từ chối đúng và trung thực với nguồn. Những nội dung đó cần đầu ra LLM thật và đánh giá tương ứng.

Bằng chứng chi tiết nằm trong các file tiến độ TV3 từ ngày 13/10 đến 17/10, `evaluation/day7_validation.json` và `docs/final-review-2026-10-17.md`. Tại thời điểm rà soát ngày cuối, `report.docx`, lượt chạy LLM thật và kiểm chứng đầy đủ trên máy nộp bài vẫn chưa hoàn tất; kết nối GitHub bị lỗi nên chưa xác nhận trạng thái remote mới nhất.

## 7. Trách nhiệm của người thực hiện

Tôi khai báo việc sử dụng AI vì AI đã tham gia trực tiếp vào quá trình viết code, sửa lỗi, kiểm thử và soạn tài liệu của phần TV3. Tôi chịu trách nhiệm rà soát nội dung được đưa vào bài nộp, ghi nhận đúng đóng góp của các thành viên và đối chiếu kết luận với bằng chứng thực tế.

Trước khi nộp và bảo vệ, tôi cần tự chạy lại các bước còn thiếu trên máy phù hợp, đọc và hiểu thay đổi để giải thích được discovery, schema, xử lý lỗi, kiểm tra bằng chứng, ghi trạng thái và đọc lại. Tài liệu này không xác nhận thay rằng các bước đó đã hoàn thành.

Các kết quả chưa đo được phải được ghi là chưa đo; dữ liệu kiểm thử theo kịch bản phải được ghi rõ nguồn; không dùng kết quả retrieval hoặc demo không gọi LLM để thay thế đánh giá Agent thật.
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


# Khai báo sử dụng AI — Thành viên 2 (Agent + LLM)

Các phần phía trên là của Thành viên 1 (dùng ChatGPT). Phần này do Thành viên 2 viết; trong phần này "tôi" là Thành viên 2.

Công cụ AI đã sử dụng

Tôi dùng Claude (trợ lý chat của Anthropic) để hỗ trợ viết code, debug và soạn ghi chú tiến độ. Model chạy agent thật trong các log là qwen/qwen3.8-27b trên Groq (một model preview).

# Phần tôi phụ trách

Agent + Business Logic + LLM: vòng lặp agent, evidence gate, ghi quyết định bằng submit_decision rồi đọc lại để verify, call_llm (retry, timeout, ghi log lỗi HTTP) và log usage.

AI đã hỗ trợ những gì
Công việc	AI làm gì	Tôi làm và kiểm tra thế nào
Script chạy thật scripts/demo_agent.py	Viết bản nháp, gồm phần đọc .env và chạy mỗi hồ sơ trên một bản sao tạm của claims.json	Tự chạy; kiểm tra git status không bao giờ liệt kê .env
Sửa src/agent/llm_client.py	Hai thay đổi: thêm header User-Agent trong urllib_transport, và chờ theo gợi ý "try again in Ns" của server khi gặp HTTP 429 (tối đa 60 giây)	Chạy toàn bộ test (135 passed), rồi chạy agent thật
Debug lần chạy thật đầu tiên	Chẩn đoán lỗi HTTP 403 (Cloudflare, mã 1010), 404 model_not_found, 400 với openai/gpt-oss-120b, 429 do giới hạn token mỗi phút; gợi ý liệt kê model bằng GET /models và dùng qwen/qwen3.8-27b	Tự chạy mọi lệnh trên máy; danh sách model lấy từ key của tôi
Ghi chú progress/2026-10-17-tv2.md	Soạn bản nháp kết quả chạy thật và các blocker	Số liệu chép từ output terminal các lần chạy của tôi
Vòng lặp agent, evidence gate, submit_decision và các test Chạy python -m pytest -q (135 passed) và chạy agent thật trên 4 hồ sơ
Phần AI không làm

AI không chạy các lệnh gọi LLM và không tạo ra log nào. Cả ba file log (logs/agent_run_01.jsonl, 02, 03) đến từ các lần chạy tôi tự thực hiện trên máy. Các số liệu trong report lấy từ những log này.

Những chỗ AI gợi ý chưa đúng
Ban đầu AI gợi ý llama-3.3-70b-versatile, nhưng key Groq của tôi không truy cập được (HTTP 404). Tôi kiểm tra bằng GET /models và chuyển sang model mà key của tôi dùng được.
Sau đó AI gợi ý openai/gpt-oss-120b, nhưng model này lỗi HTTP 400 vì cơ chế gọi công cụ riêng của nó xung đột với giao thức JSON-action trong prompt của agent. Không dùng model này.
Những gì tôi đã tự kiểm tra
Chạy python -m pytest -q: 135 passed.
Chạy agent thật với qwen/qwen3.8-27b trên 4 hồ sơ mẫu (CLM-001, CLM-002, CLM-003, CLM-006). Kết quả: APPROVED, ESCALATED, NEED_MORE_INFO, REJECTED; cả 4 đều VERIFY SUCCESS (đọc lại bằng get_claim_status thấy trạng thái khớp).
Tổng usage lần chạy 01: 21 lần gọi model, 41990 prompt token, 1608 completion token.
Có ba log thật, nhưng log 02 và 03 chạy lại các hồ sơ của log 01 và cho cùng số token vì temperature=0, nên đó là lần lặp lại, không phải bằng chứng độc lập. Riêng logs/agent_run_02.jsonl chứa hai lần chạy giống hệt nhau của CLM-001 và CLM-006 (19:04 và 19:15), cả hai đều thành công.
Hạn chế cần nói rõ
qwen/qwen3.8-27b là model preview, Groq có thể ngừng bất ngờ. Gói free giới hạn 7000 token đầu vào mỗi phút nên một lần chạy 4 hồ sơ mất khoảng 12 phút do chờ.
VERIFY SUCCESS chỉ cho biết trạng thái đã ghi và đọc lại khớp nhau. Việc quyết định có đúng hay không được đo riêng bởi Thành viên 1 (Decision Accuracy) từ các log này.
Các tình huống NO_ANSWER, output sai định dạng và MAX_STEPS hiện được kiểm tra bằng unit test với model giả lập, chưa có lần chạy thật với LLM.
# Cam kết

Tôi có sử dụng AI để hỗ trợ trong quá trình làm project, chủ yếu để học, giải thích code, gợi ý cách triển khai và hỗ trợ debug.

Tôi đã chạy và kiểm tra lại các phần code được AI hỗ trợ, đồng thời học lại lý thuyết liên quan để có thể giải thích và sửa code trực tiếp trong buổi bảo vệ.
