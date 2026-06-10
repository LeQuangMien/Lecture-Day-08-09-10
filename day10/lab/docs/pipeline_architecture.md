# Kiến trúc pipeline — Lab Day 10

**Nhóm:** Nhóm Day 10  
**Cập nhật:** 2026-06-10  
**Final run_id:** `2026-06-10T08-19Z`

---

## 1. Sơ đồ luồng

```mermaid
flowchart LR
    A[Raw policy export\n`data/raw/policy_export_dirty.csv`\nraw_records=247] --> B[Ingest\n`load_raw_csv()`]
    B --> C[Transform / Clean\nallowlist doc_id\nnormalize effective_date\nquarantine stale/noisy/duplicate rows]
    C --> D1[Cleaned CSV\n`artifacts\cleaned\cleaned_2026-06-10T08-19Z.csv`\ncleaned_records=32]
    C --> D2[Quarantine CSV\n`artifacts/quarantine/...`\nquarantine_records=215]
    D1 --> E[Validate expectations\nhalt/warn checks]
    E --> F[Embed / Upsert\nChroma collection `day10_kb`\n`chunk_id` stable]
    F --> G[Retrieval grading\n`grading_run_final.jsonl`\n10/10 pass]
    E --> H[Manifest\n`artifacts/manifests/manifest_2026-06-10T08-19Z.json`\nrun_id + record counts]
    H --> I[Freshness monitor\nFAIL: freshness_sla_exceeded]
```

Pipeline bắt đầu từ raw CSV export, sau đó ingest bằng `csv.DictReader`, clean từng record, ghi cả `cleaned_csv` và `quarantine_csv`, chạy expectation suite, rồi embed vào Chroma. Mỗi lần chạy có `run_id`, ví dụ final run là `2026-06-10T08-19Z`. Freshness được đo từ `latest_exported_at=2026-04-11T00:00:00` trong manifest; final check báo `FAIL` vì dữ liệu export đã vượt SLA 24 giờ.

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | `data/raw/policy_export_dirty.csv` | List raw rows, `raw_records=247` | Raw / Ingestion owner |
| Transform | Raw rows + `ALLOWED_DOC_IDS` + cleaning rules | `cleaned_csv`, `quarantine_csv`, reason cho từng dòng quarantine | Cleaning owner |
| Quality | Cleaned rows | Expectation results: `OK`, `WARN`, hoặc `FAIL`; quyết định halt | Quality owner |
| Embed | Cleaned rows đã pass validation | Chroma collection `day10_kb`, upsert theo `chunk_id` | Embed owner |
| Monitor | Manifest + `latest_exported_at` | Freshness status `PASS/WARN/FAIL` | Monitoring / Docs owner |

---

## 3. Idempotency & rerun

Pipeline dùng `chunk_id` ổn định được hash từ `doc_id`, `chunk_text` và `seq`. Khi rerun, embed stage dùng upsert thay vì append mù, đồng thời prune các id không còn thuộc cleaned corpus hiện hành. Bằng chứng từ các run trước: khi đổi từ bad run sang good run, log có `embed_prune_removed=1`, sau đó `embed_upsert count=32`, đúng bằng `cleaned_records=32`. Vì vậy rerun không làm vector DB tăng duplicate theo số lần chạy; collection được đồng bộ lại với cleaned CSV hiện tại.

---

## 4. Liên hệ Day 09

Pipeline Day 10 đóng vai trò làm mới knowledge base cho retrieval trong các lab agent/RAG Day 08–09. Thay vì agent đọc trực tiếp raw policy export, Day 10 tạo một corpus đã clean, validate và embed vào Chroma collection `day10_kb`. Khi Day 09 cần trả lời về refund, SLA P1, IT helpdesk, HR leave hoặc access control, agent nên truy vấn collection này để tránh dùng dữ liệu stale như “14 ngày làm việc” hoặc “10 ngày phép năm”.

---

## 5. Rủi ro đã biết

- Freshness final đang `FAIL` vì `latest_exported_at=2026-04-11T00:00:00` đã vượt SLA 24 giờ. Đây là rủi ro dữ liệu cũ, không phải lỗi code.
- Một số rule canonicalization được viết theo pattern cụ thể của lab, ví dụ SLA P1 auto escalation. Nếu raw export đổi cách diễn đạt quá nhiều, cần cập nhật rule hoặc chuyển sang schema chuẩn hơn.
- `grading_core_facts_present` kiểm tra fact tồn tại trong toàn corpus, chưa đảm bảo mọi câu retrieval đều top-k đúng. Vì vậy vẫn cần chạy `grading_run.py` cuối cùng.
- Chroma collection phụ thuộc vào cùng cấu hình `CHROMA_DB_PATH`, `CHROMA_COLLECTION`, `EMBEDDING_MODEL`; đổi env có thể làm grading đọc nhầm collection.
