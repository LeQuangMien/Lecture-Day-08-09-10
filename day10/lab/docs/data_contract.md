# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|--------|-------------------|-------------------|----------------|
| policy_refund_v4 | CSV export từ policy catalog, đưa vào `etl_pipeline.py` rồi clean thành chunk | Stale refund window: bản cũ ghi 14 ngày làm việc thay vì policy hiện hành 7 ngày làm việc; duplicate chunk; `effective_date` sai format | `refund_no_stale_14d_window`, số dòng bị sửa `[cleaned: stale_refund_window]`, `quarantine_records` theo reason |
| hr_leave_policy | CSV export từ HR policy, clean theo `doc_id`, `effective_date`, `chunk_text` | Conflict version: bản HR 2025 ghi 10 ngày phép năm lẫn với bản HR 2026 ghi 12 ngày phép năm; `effective_date` thiếu hoặc cũ | `hr_leave_no_stale_10d_annual`, `stale_hr_policy_effective_date`, `stale_hr_policy_10d_annual` |
| access_control_sop | CSV export từ IT/Security SOP, cần nằm trong `ALLOWED_DOC_IDS` để phục vụ retrieval | Source bị thiếu trong allowlist nên bị quarantine `unknown_doc_id`; có thể có duplicate hoặc `chunk_text` rỗng | Top-1 grading cho `gq_d10_10`, số record `access_control_sop` trong cleaned, số quarantine theo `missing_chunk_text` / `duplicate_chunk_text` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
