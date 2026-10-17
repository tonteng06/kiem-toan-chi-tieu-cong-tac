# Khai báo sử dụng AI — Nhóm T2 (Travel Expense Audit Agent)

Mỗi thành viên khai báo phần của mình: công cụ dùng, dùng cho việc gì, prompt chính, file nào có AI sinh hoặc gợi ý, và những gì đã tự chạy/kiểm tra. Số liệu chạy thật nằm trong `logs/`, `evaluation/` và `report.docx`.

| Thành viên | Phần phụ trách | Công cụ AI |
|---|---|---|
| Thành viên 1 | Data + RAG + Evaluation | ChatGPT |
| Thành viên 2 | Agent + Business logic + LLM | Claude |
| Thành viên 3 (Lê Thanh Đại Dương) | MCP + Tích hợp + Tái lập | ChatGPT, Codex |

---

## Thành viên 1 — Data + RAG + Evaluation (ChatGPT)

### Phần phụ trách
Corpus policy và metadata; loader, chunking (size 500, overlap 100); embedding; Dense, BM25, Hybrid, Retriever; testset; retrieval evaluation (Hit@3, Recall@3); failure analysis; claim-to-policy grounding; hạ tầng đánh giá Agent (contract, per-case và aggregate metrics).

### AI hỗ trợ
- Giải thích Dense, BM25, Hybrid (min-max normalization, trọng số), Hit@3, Recall@3 và phân tích Q13, Q14, Q15 (multi-policy, version).
- Gợi ý hoặc viết bản nháp code các file: `src/models/document.py`, `src/rag/loader.py`, `chunker.py`, `embeddings.py`, `dense_search.py`, `bm25_search.py`, `hybrid_search.py`, `retriever.py`, `evaluation/evaluate_retrieval.py`, `evaluation/day2_reasoning_analysis.py`, `evaluation/evaluate_claim_grounding.py`.
- Ngày 14–15/10 (Agent evaluation): `evaluation/agent_eval_contract.py`, `agent_metrics.py`, `agent_eval_summary.py`, `tests/test_agent_eval_contract.py`, `test_agent_metrics.py`, `test_agent_eval_summary.py`, `evaluation/day4_analysis.txt`.

### Prompt chính
- "Hướng dẫn tôi làm phần Data + RAG + Evaluation từng bước."
- "Giải thích Dense Search, BM25 và Hybrid Search để tôi có thể hiểu và bảo vệ."
- "Giải thích cách tính Hit@3 và Recall@3."
- "Phân tích vì sao Hybrid Search không lấy được DOC007 trong Q13."
- "Giúp tôi kiểm tra trường hợp multi-policy và policy version ở Q14, Q15."
- "Hỗ trợ xây dựng claim-to-policy grounding evaluation và phân biệt nó với LLM faithfulness."
- "Giúp tôi thiết kế Agent evaluation output contract."
- "Giải thích sự khác nhau giữa NO_ANSWER và NEED_MORE_INFO."
- "Giải thích vì sao Evidence Coverage không phải Faithfulness."

### Đã tự chạy và kiểm tra
- Load đủ 8 policy document, kiểm tra metadata, chunking, embedding 384 chiều.
- Chạy Dense, BM25, Hybrid và Retriever hai chế độ; chạy testset 15 câu (4 câu `no_answer`).
- Kết quả: Dense Hit@3/Recall@3 = 100%/100%; Hybrid = 100%/95,45%. Q13 của Hybrid thiếu DOC007 trong Top-3, được giữ lại làm failure case, không chỉnh để metric đẹp hơn.
- Retrieval không chứng minh được Agent từ chối đúng (`no_answer`); phần đó cần output Agent thật.
- Các Agent output dùng trong unit test của metrics là dữ liệu giả lập, chỉ để kiểm tra công thức, không dùng làm kết quả cuối.

---

## Thành viên 2 — Agent + Business logic + LLM (Claude)

### Phần phụ trách
Vòng lặp agent tự viết, evidence gate, business rules, `submit_decision` rồi đọc lại để verify, `call_llm` (retry, timeout, ghi log lỗi HTTP), prompt tách file (`src/agent/prompts/agent_system.txt`), log usage.

### AI hỗ trợ
| Công việc | AI làm gì | Tôi làm và kiểm tra thế nào |
|---|---|---|
| `scripts/demo_agent.py` | Viết bản nháp: đọc `.env`, chạy mỗi hồ sơ trên bản sao tạm của `claims.json` | Tự chạy; kiểm tra `git status` không liệt kê `.env` |
| `src/agent/llm_client.py` | Hai thay đổi: thêm header `User-Agent` trong `urllib_transport`; chờ theo gợi ý "try again in Ns" khi gặp HTTP 429 (tối đa 60 giây) | Chạy toàn bộ test, rồi chạy agent thật |
| Debug lần chạy thật đầu tiên | Chẩn đoán HTTP 403 (Cloudflare, mã 1010), 404 `model_not_found`, 400 với `openai/gpt-oss-120b`, 429 do giới hạn token/phút; gợi ý liệt kê model bằng `GET /models` và dùng `qwen/qwen3.8-27b` | Tự chạy mọi lệnh; danh sách model lấy từ key của tôi |
| `progress/2026-10-17-tv2.md` | Soạn bản nháp kết quả chạy thật và blocker | Số liệu chép từ output terminal của các lần chạy tôi tự thực hiện |
| Vòng lặp agent, evidence gate, `submit_decision` và các test | *(điền: phần nào do AI sinh bản nháp, phần nào tự viết, và đã sửa gì)* | Chạy `python -m pytest -q` và chạy agent thật |

### Prompt chính
*(điền 4–6 prompt chính đã dùng với Claude, ví dụ prompt xây dựng vòng lặp agent, evidence gate, parse action, retry/429)*

### AI không làm
AI không chạy các lệnh gọi LLM và không tạo ra log nào. Các file `logs/agent_run_01..04.jsonl` đến từ các lần chạy tôi tự thực hiện trên máy.

### Những chỗ AI gợi ý chưa đúng
- Ban đầu AI gợi ý `llama-3.3-70b-versatile`, nhưng key Groq của tôi không truy cập được (HTTP 404). Tôi kiểm tra bằng `GET /models` và chuyển sang model mà key dùng được.
- Sau đó AI gợi ý `openai/gpt-oss-120b`, nhưng model này lỗi HTTP 400 vì cơ chế gọi công cụ riêng của nó xung đột với giao thức JSON-action trong prompt của agent. Không dùng model này.

### Đã tự chạy và kiểm tra
- Agent thật với `qwen/qwen3.8-27b` trên 4 hồ sơ mẫu (CLM-001, CLM-002, CLM-003, CLM-006): APPROVED, ESCALATED, NEED_MORE_INFO, REJECTED; cả 4 đều VERIFY SUCCESS (đọc lại bằng `get_claim_status`, trạng thái khớp).
- Usage lần chạy 01: 21 lần gọi model, 41.990 prompt token, 1.608 completion token.
- `agent_run_02` và `agent_run_03` chạy lại hồ sơ của run 01 và cho cùng số token (temperature=0), nên là lần lặp lại, không phải bằng chứng độc lập; `agent_run_02` chứa hai lần chạy giống hệt nhau của CLM-001 và CLM-006.
- `agent_run_04`: chạy thật trên các câu `no_answer` Q09–Q12.

### Hạn chế
- `qwen/qwen3.8-27b` là model preview; gói free giới hạn 7000 token đầu vào mỗi phút nên một lượt 4 hồ sơ mất khoảng 12 phút do chờ.
- `VERIFY SUCCESS` chỉ cho biết trạng thái ghi và đọc lại khớp nhau; quyết định đúng hay sai được đo riêng bằng Decision Accuracy.
- Các tình huống output sai định dạng và `MAX_STEPS` hiện kiểm tra bằng unit test với model giả lập, chưa có lần chạy thật.

---

## Thành viên 3 — MCP + Tích hợp + Tái lập (ChatGPT, Codex)

### Phần phụ trách
MCP server/client, khám phá tool qua `tools/list`, gọi qua `tools/call`; kết nối bộ truy xuất policy (TV1) với registry, business rules, state store (TV2); `submit_decision` và `get_claim_status`; logs, Makefile, README, `.env.example`.
Agent và kết nối LLM do Thành viên 2 xây dựng, được tích hợp từ nhánh `tv2-final-agent`; RAG do Thành viên 1 xây dựng. Việc merge và test tích hợp không có nghĩa tôi tự xây dựng toàn bộ Agent hoặc RAG.

### AI hỗ trợ theo tiến độ
- **13/10:** xây MCP server/client, tool `search_policy` (dùng `Retriever` có sẵn, giữ document, version, chunk để truy vết nguồn) và `get_claim_status` (dùng `StateStore`); smoke test discovery/call.
- **14–15/10:** chuẩn hóa package `src/mcp_server`, tên tool, tiền tố lỗi `Error:`; phân biệt `NO_ANSWER` (không lưu) với các quyết định lưu được. Codex sửa model claim, business rules và dữ liệu mẫu (kiểu dữ liệu, phân bổ tiền theo ngày/đêm, mục đích di chuyển, phê duyệt nâng hạng) — các thay đổi này nằm ngoài lớp MCP và được ghi tại `progress/2026-10-14-tv3.md`. Xây `McpToolbox` đồng bộ, cache discovery, adapter cho các tool đọc claim, tính toán, tìm policy, đọc trạng thái.
- **16/10:** `submit_decision` dựa trên `StateStore`; demo ghi rồi đọc lại ngay trên bản sao state; ba log `logs/run_01..03.jsonl` (retrieval MiniLM thật, thao tác MCP/lưu trạng thái thật, LLM usage = 0); Makefile, hướng dẫn thiết lập, `.env.example`.
- **17/10:** merge `tv2-final-agent`; thêm `scripts/demo_agent_mcp.py` nối Agent/LLM với MCP, state riêng và bước đọc lại sau ghi; kiểm tra nguồn trích dẫn khi ghi phải thực sự được truy xuất trong lượt chạy đó; cập nhật README, Makefile, tài liệu bàn giao.

### Các yêu cầu chính đã giao cho AI
- Phân tích tài liệu phân công và thực hiện phần MCP/tích hợp theo từng ngày.
- Giải thích discovery, schema, lời gọi tool và xử lý lỗi.
- Kết nối RAG, registry và trạng thái claim bằng giao diện sẵn có.
- Viết regression test; xử lý lỗi tích hợp; xây demo ghi rồi đọc lại; viết tài liệu bàn giao và tiến độ bằng tiếng Việt.

### File có AI hỗ trợ trực tiếp
| Nhóm | File |
|---|---|
| MCP server/client, contract | `src/mcp_server/server.py`, `client.py`, `contracts.py` |
| Adapter, kết nối Agent, evidence | `src/mcp_server/adapters.py`, `registry_adapter.py`, `agent_bridge.py`, `evidence.py` |
| Smoke test và demo | `scripts/smoke_stdio.py`, `smoke_mcp_tools.py`, `smoke_registry.py`, `smoke_adapter.py`, `demo_readonly_audit.py`, `demo_verified_audit.py`, `demo_agent_mcp.py` |
| Test MCP/tích hợp | `tests/test_mcp_sdk.py`, `test_mcp_registry.py`, `test_adapters.py`, `test_mcp_evidence.py`, `test_mcp_write.py`, `test_agent_mcp_contract.py` |
| Sửa model/quy tắc trước tích hợp | `src/models/claim.py`, `src/agent/business_rules.py`, `data/claims/claims.json`, `tests/test_regressions.py` |
| Thiết lập, tài liệu | `README.md`, `Makefile`, `.env.example`, `ai-usage.md`, `docs/`, `progress/*-tv3.md` |

Danh sách này không có nghĩa toàn bộ file do AI tạo; các file có thể gồm cả code sẵn có của nhóm.

### Kết quả kiểm chứng
| Nội dung | Kết quả |
|---|---|
| Toàn bộ test (`python -m pytest -q`, 17/10/2026, `main`) | 257 passed, 71 subtests passed |
| Retrieval MiniLM thật (15 câu, 11 có đáp án) | Dense Hit@3/Recall@3 = 100%/100%; Hybrid = 100%/95,45%; Q13 Hybrid thiếu DOC007 |
| Ghi và đọc lại qua MCP | Ba log 16/10 có retrieval, lưu trạng thái, xác minh file; LLM usage = 0 |
| Test Agent/MCP | `APPROVED`, `ESCALATED`, `NEED_MORE_INFO`, `REJECTED` và chặn citation chưa truy xuất được kiểm tra bằng phản hồi giả lập, không dùng làm metric Agent cuối cùng |
| Cold start trên máy sạch | *(điền kết quả sau khi chạy `pip install -r requirements.txt` trong venv mới)* |

Retrieval tốt, test giả lập đạt hoặc log ghi file thành công chưa đủ để kết luận Agent trả lời đúng, từ chối đúng và trung thực với nguồn; điều đó cần output LLM thật.

---

## Cam kết

Mỗi thành viên xác nhận: đã dùng AI như khai báo ở phần của mình, đã chạy và kiểm tra các phần code có AI hỗ trợ, và có thể giải thích, sửa trực tiếp phần mình phụ trách khi bảo vệ.

- Thành viên 1: *(ký tên / viết 1–2 câu của riêng bạn)*
- Thành viên 2: *(ký tên / viết 1–2 câu của riêng bạn)*
- Thành viên 3: *(ký tên / viết 1–2 câu của riêng bạn)*
