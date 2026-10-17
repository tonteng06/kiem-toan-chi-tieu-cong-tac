# Khai báo sử dụng AI — Thành viên 3

**Họ và tên:** Lê Thanh Đại Dương
**Phần phụ trách:** MCP và tích hợp hệ thống
**Cập nhật:** 17/10/2026

## 1. Công cụ AI đã sử dụng

Trong quá trình thực hiện project, tôi sử dụng ChatGPT và Codex của OpenAI để hỗ trợ tìm hiểu kiến thức, giải thích mã nguồn, đề xuất cách triển khai, viết và sửa code, kiểm thử, rà soát lỗi tích hợp và soạn tài liệu.

Codex còn trực tiếp thao tác trên bản repository được cung cấp: chỉnh sửa file, chạy lệnh kiểm tra, tích hợp các nhánh đã có và tạo một số commit theo yêu cầu. Vì vậy, mức độ hỗ trợ của AI bao gồm cả tạo và sửa code trực tiếp, không chỉ giải thích hoặc gợi ý.

Tài liệu này tham khảo bố cục `ai-usage.md` của Thành viên 1 trên nhánh `origin/member1-final-eval`: công cụ sử dụng, phạm vi phụ trách, nội dung theo ngày, yêu cầu chính, file liên quan và cách kiểm chứng. Nội dung dưới đây khai báo phần Thành viên 3; phần Data, RAG và Evaluation vẫn được ghi nhận là đóng góp của Thành viên 1.

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

Một số commit được Codex tạo trực tiếp trong bản làm việc theo yêu cầu hỗ trợ Git. Lịch sử Git phản ánh identity tại thời điểm tạo commit; khai báo này ghi rõ AI đã tham gia triển khai và thao tác repository.

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
