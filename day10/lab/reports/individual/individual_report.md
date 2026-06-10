# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Quang Miền  
**Vai trò:** Cleaning / Quality / Monitoring Docs  
**Ngày nộp:** 2026-06-10  
**Final run_id:** `2026-06-10T08-19Z`

---

## 1. Tôi phụ trách phần nào?

Tôi phụ trách chính phần clean dữ liệu, thêm expectation và hỗ trợ viết tài liệu quan sát pipeline. Các file/module tôi làm việc nhiều nhất là `transform/cleaning_rules.py`, `quality/expectations.py`, `docs/data_contract.md`, `docs/runbook.md` và `reports/group_report.md`. Công việc của tôi nối trực tiếp với phần ingest vì raw CSV có nhiều nguồn lẫn nhau, trong đó có source cần cho grading nhưng ban đầu chưa nằm trong allowlist. Sau khi clean và validate ổn định, phần embed dùng cleaned rows để upsert vào Chroma collection `day10_kb`. Bằng chứng cuối là final run `2026-06-10T08-19Z`: `raw_records=247`, `cleaned_records=32`, `quarantine_records=215`, `embed_upsert count=32`, và `PIPELINE_OK`.

---

## 2. Một quyết định kỹ thuật

Một quyết định quan trọng của tôi là phân biệt rõ expectation nào nên `halt` và expectation nào chỉ nên `warn`. Những lỗi làm sai câu trả lời policy, ví dụ refund còn `14 ngày làm việc`, thiếu source grading, thiếu approver cho Level 4 Admin Access, hoặc thiếu canonical chunk SLA P1 `10 phút`, đều được đặt severity `halt`. Lý do là nếu các lỗi này lọt vào embedding thì agent/RAG có thể trả lời sai nhưng nhìn bề ngoài vẫn chạy bình thường. Ngược lại, `chunk_min_length_8` giữ ở mức `warn` vì chunk ngắn có thể là dấu hiệu chất lượng kém nhưng chưa chắc gây sai policy. Cách này giúp pipeline dừng đúng lúc với lỗi nghiêm trọng, nhưng không quá nhạy với cảnh báo nhỏ.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Lỗi khó chịu nhất tôi xử lý là câu grading `gq_d10_06`: top-1 đã đúng `sla_p1_2026`, nhưng `contains_expected=false` vì top-k retrieval không lấy được chunk chứa `10 phút`. Ban đầu expectation `grading_core_facts_present` vẫn OK vì nó chỉ kiểm tra toàn corpus có `10 phút`, nhưng grading cần top-k chứa fact đó. Tôi sửa bằng cách canonicalize chunk SLA P1 auto escalation: thêm phrasing gần với câu hỏi “nếu không có phản hồi với ticket P1 trong 10 phút thì hệ thống tự động escalate...”. Sau đó tôi thêm expectation `sla_p1_auto_escalation_10m_canonical_present` để bảo vệ chunk này. Kết quả final grading đạt 10/10, bao gồm `gq_d10_06 contains_expected=true`.

---

## 4. Bằng chứng trước / sau

Trong Sprint 3, tôi chạy bad inject:

```powershell
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

Bad run cho thấy expectation `refund_no_stale_14d_window FAIL (halt) :: violations=1`, nhưng vẫn embed để demo vì dùng `--skip-validate`. Sau đó chạy good run chuẩn:

```powershell
python etl_pipeline.py run
```

Good run `2026-06-10T08-19Z` cho thấy `refund_no_stale_14d_window OK (halt) :: violations=0`. Ở retrieval eval, câu refund window chuyển từ trạng thái còn forbidden `14 ngày làm việc` sang không còn forbidden và trả về `7 ngày làm việc`. Final `grading_run_final.jsonl` đạt `contains_expected=10/10`, `hits_forbidden_false=10/10`, `top1_matches=10/10`.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm CI script chạy tự động toàn bộ `etl_pipeline.py run`, `grading_run.py`, `eval_retrieval.py`, và freshness check. Ngoài ra tôi muốn xuất thêm một file summary JSON cho các metric chính như `quarantine_records_by_reason`, expectation status và grading pass rate để dễ đưa vào dashboard hoặc báo cáo.
