# Data contract — Lab Day 10

**Cập nhật:** 2026-06-10  
**Final run_id:** `2026-06-10T08-19Z`

> Contract này đồng bộ với `contracts/data_contract.yaml` và logic trong `transform/cleaning_rules.py`.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|--------|-------------------|-------------------|----------------|
| `policy_refund_v4` | CSV export từ policy catalog, đọc qua `etl_pipeline.py` rồi clean thành chunk | Stale refund window: bản cũ ghi `14 ngày làm việc` thay vì policy hiện hành `7 ngày làm việc`; duplicate chunk; `effective_date` sai format; sync noise | `refund_no_stale_14d_window`, `hits_forbidden` trong eval, marker `[cleaned: stale_refund_window]`, quarantine reason `repeated_sync_noise` |
| `sla_p1_2026` | CSV export từ SLA knowledge base, giữ các chunk P1 cần cho retrieval | Chunk escalation diễn đạt chưa gần câu hỏi grading; noisy text; duplicate chunk | `sla_p1_auto_escalation_10m_canonical_present`, `grading_core_facts_present`, grading `gq_d10_04`–`gq_d10_06` |
| `it_helpdesk_faq` | CSV export từ IT FAQ | Chunk rỗng, duplicate, nội dung không rõ ràng | `required_grading_doc_ids_present`, `grading_core_facts_present`, quarantine reason `missing_chunk_text` / `duplicate_chunk_text` / `noisy_uncertain_chunk` |
| `hr_leave_policy` | CSV export từ HR policy, clean theo `doc_id`, `effective_date`, `chunk_text` | Conflict version: bản HR 2025 ghi `10 ngày phép năm` lẫn với bản HR 2026 ghi `12 ngày phép năm`; `effective_date` thiếu hoặc cũ | `hr_leave_no_stale_10d_annual`, `stale_hr_policy_effective_date`, `stale_hr_policy_10d_annual` |
| `access_control_sop` | CSV export từ IT/Security SOP, cần nằm trong `ALLOWED_DOC_IDS` để phục vụ retrieval | Source từng bị thiếu trong allowlist nên bị quarantine `unknown_doc_id`; có thể có bản cũ trước 2026, duplicate hoặc `chunk_text` rỗng | `access_control_l4_admin_approver_present`, top-1 grading `gq_d10_10`, reason `stale_access_control_effective_date` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | Stable id dạng `doc_id_seq_hash`, dùng cho upsert/prune idempotent trong Chroma |
| `doc_id` | string enum | Có | Chỉ nhận doc_id nằm trong allowlist: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop` |
| `chunk_text` | string | Có | Nội dung đã clean/canonicalize; không rỗng, không chứa stale marker bị halt |
| `effective_date` | date `YYYY-MM-DD` | Có | Normalize từ ISO hoặc `DD/MM/YYYY`; format khác bị quarantine |
| `exported_at` | datetime/string | Có | Timestamp export từ nguồn raw; dùng để tính freshness trong manifest |

---

## 3. Quy tắc quarantine vs drop

Record lỗi không bị drop im lặng. Pipeline ghi vào `artifacts/quarantine/quarantine_<run_id>.csv` cùng `reason` để review lại. Các nhóm reason chính:

| Reason | Hành động | Ai review |
|--------|-----------|-----------|
| `unknown_doc_id` | Quarantine vì source chưa nằm trong contract/allowlist | Data owner + reviewer |
| `missing_effective_date`, `invalid_effective_date_format` | Quarantine vì không xác định được version hợp lệ | Ingestion owner |
| `stale_hr_policy_effective_date`, `stale_hr_policy_10d_annual` | Quarantine bản HR cũ/conflict | HR/source owner |
| `stale_access_control_effective_date` | Quarantine SOP cũ trước 2026 | Security/source owner |
| `missing_chunk_text`, `duplicate_chunk_text` | Quarantine record không đủ nội dung hoặc trùng | Cleaning owner |
| `noisy_uncertain_chunk`, `repeated_sync_noise` | Quarantine chunk có dấu hiệu sync/noise | Cleaning + Quality owner |

Chỉ merge lại record từ quarantine khi có bằng chứng source chính thức hoặc cập nhật contract.

---

## 4. Phiên bản & canonical

- Refund canonical: `policy_refund_v4`, chính sách hiện hành là `7 ngày làm việc`; mọi `14 ngày làm việc` trong policy hiện hành phải được sửa hoặc chặn bởi expectation.
- HR canonical: `hr_leave_policy` bản 2026, nhân viên dưới 3 năm là `12 ngày phép năm`; bản `10 ngày phép năm` là stale/conflict.
- SLA canonical: `sla_p1_2026`, P1 initial response `15 phút`, resolution `4 giờ`, auto escalation nếu không có phản hồi trong `10 phút`.
- Access control canonical: `access_control_sop` bản 2026; Level 4 Admin Access cần approver `IT Manager` và/hoặc `CISO`.

---

## 5. Final run evidence

| Metric | Value |
|--------|------:|
| `run_id` | `2026-06-10T08-19Z` |
| `raw_records` | 247 |
| `cleaned_records` | 32 |
| `quarantine_records` | 215 |
| `latest_exported_at` | `2026-04-11T00:00:00` |
| `chroma_collection` | `day10_kb` |
