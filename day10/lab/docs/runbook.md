# Runbook — Lab Day 10 (incident tối giản)

**Cập nhật:** 2026-06-10  
**Final run_id tham chiếu:** `2026-06-10T08-19Z`

---

## Symptom

User hoặc agent có thể gặp các triệu chứng sau:

- Trả lời sai chính sách refund, ví dụ nói khách hàng có `14 ngày làm việc` thay vì `7 ngày làm việc`.
- Trả lời sai HR leave, ví dụ dùng bản HR 2025 `10 ngày phép năm` thay vì bản 2026 `12 ngày phép năm`.
- Không trả lời được câu SLA P1 auto escalation sau `10 phút`, dù source `sla_p1_2026` có tồn tại.
- Trả lời thiếu approver cho Level 4 Admin Access vì `access_control_sop` bị quarantine nhầm hoặc thiếu trong allowlist.
- Freshness monitor báo `FAIL` do dữ liệu export quá cũ.

---

## Detection

| Tín hiệu | Cách phát hiện | Ý nghĩa |
|----------|----------------|--------|
| Expectation fail | Log `python etl_pipeline.py run` | Lỗi dữ liệu nghiêm trọng. Nếu severity `halt`, pipeline không nên embed trừ khi dùng `--skip-validate` cho demo. |
| Eval `hits_forbidden` | `python eval_retrieval.py --out ...` | Retrieval đang kéo stale/forbidden content, ví dụ `14 ngày làm việc`. |
| Grading fail | `python grading_run.py --out artifacts/eval/grading_run_final.jsonl` | Một hoặc nhiều câu không đạt `contains_expected`, `hits_forbidden=false`, hoặc `top1_doc_matches=true`. |
| Freshness FAIL | `python etl_pipeline.py freshness --manifest ...` | Raw export vượt SLA dữ liệu mới. Final run báo `freshness_sla_exceeded`. |

Final freshness check:

```text
FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1448.351, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác định `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, `latest_exported_at`, collection Chroma |
| 2 | Mở `artifacts/quarantine/*.csv` | Xem record bị loại theo `reason`: `unknown_doc_id`, `stale_*`, `duplicate_chunk_text`, `noisy_uncertain_chunk` |
| 3 | Mở `artifacts/cleaned/*.csv` | Kiểm tra fact canonical còn tồn tại: `7 ngày làm việc`, `12 ngày phép năm`, `10 phút`, `IT Manager/CISO` |
| 4 | Chạy `python eval_retrieval.py --out artifacts/eval/eval_debug.csv` | Xem câu nào còn `hits_forbidden=yes` hoặc top-k không chứa expected text |
| 5 | Chạy `python grading_run.py --out artifacts/eval/grading_run_final.jsonl` | Kỳ vọng 10/10: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` |
| 6 | Nếu freshness FAIL | So sánh `latest_exported_at` với SLA 24h; xác định cần re-export data hay chỉ ghi nhận lab data stale |

---

## Mitigation

- Nếu lỗi do stale refund: bật lại refund fix, không dùng `--no-refund-fix`, chạy lại `python etl_pipeline.py run`.
- Nếu lỗi do expectation halt: không dùng `--skip-validate` trong production; sửa cleaning rule hoặc cập nhật source rồi rerun.
- Nếu vector DB còn dữ liệu xấu từ inject run: chạy lại pipeline chuẩn. Embed stage dùng upsert/prune theo `chunk_id`, ví dụ good run trước có `embed_prune_removed=1` và `embed_upsert count=32`.
- Nếu freshness FAIL: tạm gắn banner “data stale”, yêu cầu owner export lại policy mới, sau đó rerun pipeline.
- Nếu grading fail một câu cụ thể: mở `grading_run_final.jsonl`, xem `top1_doc_id`, `contains_expected`, `hits_forbidden`, rồi kiểm tra cleaned chunk tương ứng.

---

## Prevention

- Duy trì expectation `refund_no_stale_14d_window`, `required_grading_doc_ids_present`, `grading_core_facts_present`, `access_control_l4_admin_approver_present`, `sla_p1_auto_escalation_10m_canonical_present`.
- Thêm alert freshness theo SLA 24h cho policy export. `PASS` nghĩa là data còn trong SLA, `WARN` nghĩa là thiếu/khó parse timestamp hoặc gần ngưỡng, `FAIL` nghĩa là vượt SLA và cần re-export.
- Không merge source mới vào allowlist nếu chưa cập nhật data contract và grading/expectation coverage.
- Ghi `run_id`, manifest, cleaned/quarantine artifact trong mỗi lần release để rollback/debug nhanh.
