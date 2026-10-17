# Travel Expense Audit Agent (AIPR – đề tài T2)

Kiểm toán chi tiêu công tác: tra cứu policy (RAG) → tính toán/đối chiếu hạn mức → evidence gate → quyết định → ghi trạng thái (JSON) → đọc lại để verify.
Quyết định được lưu: `APPROVED`, `REJECTED`, `ESCALATED`, `NEED_MORE_INFO`. `NO_ANSWER` chỉ là phản hồi của Agent khi thiếu bằng chứng policy, không ghi vào claim.

Yêu cầu: **Python 3.11+**, internet ở lần chạy đầu (tải model `sentence-transformers/all-MiniLM-L6-v2`).

## 1. Chạy một lệnh (cold start)

Linux / macOS:

```bash
python3 -m venv .venv && . .venv/bin/activate
make setup && make demo
```

Windows PowerShell (không có `make`):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/demo_verified_audit.py
```

`make demo` chạy thật RAG + MCP + ghi quyết định + đọc lại verify trên **bản sao tạm** của `data/claims/claims.json` (file gốc không bị sửa). Demo này **không gọi LLM** (số lần gọi LLM = 0), nên không cần API key.

Đã có cache model thì có thể chạy offline: `HF_HUB_OFFLINE=1`.

## 2. Các lệnh

| Lệnh | Tương đương Python | Nội dung |
|---|---|---|
| `make setup` | `pip install -r requirements.txt` | Cài thư viện |
| `make demo` | `python scripts/demo_verified_audit.py` | RAG + MCP + write + verify, không LLM |
| `make eval` | `python -m evaluation.evaluate_retrieval` | Dense vs Hybrid trên `tests/testset.jsonl`, ghi `evaluation/results.csv`, `summary.csv` |
| `make test` | `python -m pytest -q` | Toàn bộ test |
| `make smoke` | xem `Makefile` | Discovery, đọc, ghi/đọc lại qua stdio |
| `make logs` | `python scripts/demo_verified_audit.py --three` | Tạo lại 3 log tích hợp (không LLM) |
| `make agent-demo` | `python scripts/demo_agent_mcp.py` | Agent LLM thật qua MCP, cần `GROQ_API_KEY` |

## 3. Chạy Agent với LLM thật

Ứng dụng **không tự đọc `.env`**. Nạp key vào terminal trước khi chạy (không commit `.env`):

PowerShell:

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
    [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim('"').Trim("'"), 'Process')
  }
}
python scripts/demo_agent_mcp.py CLM-001 --log logs/agent_mcp_01.jsonl
```

Linux / macOS: `set -a; . ./.env; set +a` rồi chạy cùng lệnh Python.

`.env.example` liệt kê các biến (key, model, endpoint, timeout, retry). Model dùng cho các log thật: `qwen/qwen3.8-27b` (Groq, bản preview). Gói free giới hạn khoảng 7000 token đầu vào mỗi phút, nên chạy từng hồ sơ một và chấp nhận thời gian chờ.

- `scripts/demo_agent_mcp.py`: Agent (vòng lặp tự viết) → `McpToolbox` → MCP server qua stdio. Schema tool lấy từ `tools/list` lúc chạy. Hợp đồng `submit_decision(claim_id, decision, reason, evidence_refs)`; model phải tự truy xuất và truyền đúng `evidence_refs` (dạng `DOC003@v1.0`), hệ thống không tự bịa evidence. Thiếu key, lỗi provider hoặc verify thất bại → exit code khác 0, không có mock fallback.
- `scripts/demo_agent.py`: runner thay thế dùng registry cục bộ (không đi qua MCP transport). Các log `agent_run_*` bên dưới do runner này tạo.
- Giới hạn bước: module Agent mặc định `MAX_STEPS = 8`; runner MCP cho phép 16 (cấu hình tối đa 32).

## 4. MCP server

Khởi động: `python -m src.mcp_server.server` (stdio; stdout chỉ dành cho giao thức MCP, log chẩn đoán ghi ra stderr).

Năm tool: `search_policy`, `get_claim`, `calculate_claim`, `submit_decision` (ghi), `get_claim_status` (đọc lại để verify). Client discover bằng `tools/list`, không hard-code danh sách.
Chi tiết: `docs/tool_contracts.md`, `docs/mcp_toolbox_handoff.md`, `docs/claim_format.md`.

## 5. Kết quả đã đo (từ output chạy thật)

**Test:** `python -m pytest -q` → 257 passed, 71 subtests passed (chạy ngày 17/10/2026 trên `main`).

**Retrieval** (`make eval`, MiniLM thật, `tests/testset.jsonl`: 15 câu, gồm 11 câu có đáp án và 4 câu `no_answer`; chỉ số tính trên 11 câu có đáp án):

| Chế độ | Hit@3 | Recall@3 |
|---|---|---|
| Dense | 100% | 100% |
| Hybrid (BM25 + dense) | 100% | 95,45% |

Q13 ở chế độ Hybrid không đưa DOC007 vào Top-3; phân tích trong `evaluation/failure_analysis.txt`. Chunking: kích thước 500, overlap 100.

**Agent thật (LLM)** – xem `logs/README.md` để biết từng file:

| File | Nội dung |
|---|---|
| `logs/agent_run_01.jsonl` | 4 hồ sơ CLM-001, 002, 003, 006 → APPROVED, ESCALATED, NEED_MORE_INFO, REJECTED; cả 4 verify thành công. Tổng usage: 21 lần gọi, 41.990 prompt token, 1.608 completion token |
| `logs/agent_run_02.jsonl`, `agent_run_03.jsonl` | Chạy lại các hồ sơ của run 01 (temperature=0), không phải bằng chứng độc lập |
| `logs/agent_run_04.jsonl` | Chạy thật trên 4 câu `no_answer` Q09–Q12 (kết quả `NO_ANSWER`) |

Mỗi log ghi timestamp, các bước, tool args/kết quả và `usage` (calls, prompt_tokens, completion_tokens, max_prompt).

**Log tích hợp không gọi LLM:** `logs/run_01..03.jsonl` (ngày 16/10: retrieval MiniLM thật + MCP + ghi/đọc lại file thật, LLM usage = 0). Không dùng làm bằng chứng chất lượng Agent.

**Cách tính chỉ số Agent:** Decision Accuracy, Correct Refusal Rate, Evidence Coverage và tổng token tính bằng `evaluation/agent_metrics.py` / `agent_eval_summary.py` từ log thật; số liệu cuối nằm trong `report.docx`. Faithfulness được chấm thủ công trên các hồ sơ đã chạy.

## 6. Hạn chế đã biết

- Hybrid thua Dense về Recall@3 trên Q13 (thiếu DOC007 trong Top-3).
- `qwen/qwen3.8-27b` là model preview của Groq, có thể bị ngừng bất ngờ; gói free giới hạn token/phút nên một lượt 4 hồ sơ mất khoảng 12 phút.
- Các tình huống `MAX_STEPS` và output LLM sai định dạng được kiểm tra bằng unit test với model giả lập, chưa có lần chạy thật.
- Trạng thái claim là một file JSON dành cho **một writer**; nhiều server không được dùng chung một file state.
- Log LLM thật hiện có do runner cục bộ (`demo_agent.py`) tạo; đường Agent → MCP bằng LLM thật chạy bằng `demo_agent_mcp.py` (xem mục 3).

## 7. Cấu trúc

```
data/         policy (metadata: doc_id, title, version, owner) và claims mẫu
src/rag/      loader, chunker, embeddings, dense, BM25, hybrid, retriever
src/agent/    vòng lặp Agent, business rules, evidence gate, llm_client, prompts/
src/mcp_server/  server, client, adapters, contracts
scripts/      demo, smoke test
evaluation/   evaluate_retrieval, agent_metrics, results.csv, summary.csv, failure_analysis.txt
tests/        testset.jsonl và các test
logs/         agent_run_*.jsonl (LLM thật), run_*.jsonl (tích hợp)
progress/     nhật ký tiến độ từng thành viên theo ngày
```

Không commit `.env`, API key, `.venv`, `__pycache__`.
