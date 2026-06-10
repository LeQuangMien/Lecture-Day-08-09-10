# Quality report — Lab Day 10 (nhóm)

**run_id:** `inject-bad` → `2026-06-10T08-10Z`  
**Ngày:** 2026-06-10

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước: inject-bad | Sau: good-after-fix | Ghi chú |
|--------|-------------------|---------------------|---------|
| raw_records | 247 | 247 | Cùng một raw export `data/raw/policy_export_dirty.csv`. |
| cleaned_records | 32 | 32 | Số chunk giữ lại không đổi; khác biệt chính nằm ở nội dung refund được fix hay không. |
| quarantine_records | 215 | 215 | Các rule quarantine vẫn chạy như nhau; inject-bad chỉ tắt refund fix và bỏ qua validate. |
| Expectation halt? | Có lỗi halt nhưng bị bypass bằng `--skip-validate` | Không có halt expectation fail | Inject-bad fail `refund_no_stale_14d_window` với `violations=1`; run chuẩn chuyển về `violations=0`. |
| embed_upsert | 32 | 32 | Upsert theo `chunk_id`; run sau có `embed_prune_removed=1`, chứng minh collection được prune khi chunk_id thay đổi. |
| freshness_check | FAIL | FAIL | Cùng nguyên nhân: `freshness_sla_exceeded`, `latest_exported_at=2026-04-11T00:00:00`, SLA 24h. Đây là cảnh báo/monitoring, không làm pipeline halt trong Sprint 3. |

### Log chứng minh

**Inject-bad:**

```text
run_id=inject-bad
raw_records=247
cleaned_records=32
quarantine_records=215
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed (chỉ dùng cho demo Sprint 3).
embed_upsert count=32 collection=day10_kb
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1448.149, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

**Good-after-fix:**

```text
run_id=2026-06-10T08-10Z
raw_records=247
cleaned_records=32
quarantine_records=215
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
embed_prune_removed=1
embed_upsert count=32 collection=day10_kb
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1448.183, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

---

## 2. Before / after retrieval (bắt buộc)

File eval sử dụng:

- Before: `artifacts/eval/eval_bad_inject.csv`
- After: `artifacts/eval/eval_good_after_fix.csv`

### Tổng quan metric retrieval

| Metric | Before: inject-bad | After: good-after-fix | Nhận xét |
|--------|--------------------|-----------------------|----------|
| Tổng số câu eval | 21 | 21 | Cùng bộ câu hỏi. |
| `contains_expected = yes` | 20/21 | 20/21 | Không đổi ở mức aggregate, vì câu refund vẫn chứa keyword expected nhưng đồng thời chứa forbidden. |
| `hits_forbidden = no` | 20/21 | 21/21 | Cải thiện trực tiếp do loại/fix stale refund `14 ngày làm việc`. |
| `top1_doc_expected = yes` | 20/21 | 20/21 | Source top-1 gần như ổn định. |
| All checks OK | 18/21 | 19/21 | Tăng từ 18 lên 19 câu đạt đầy đủ. |

### Câu hỏi then chốt: refund window (`q_refund_window`)

**Trước — inject-bad:**

| question_id | top1_doc_id | top1_preview | contains_expected | hits_forbidden | top1_doc_expected |
|-------------|-------------|--------------|-------------------|----------------|-------------------|
| `q_refund_window` | `policy_refund_v4` | Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn. | `yes` | `yes` | `yes` |

**Sau — good-after-fix:**

| question_id | top1_doc_id | top1_preview | contains_expected | hits_forbidden | top1_doc_expected |
|-------------|-------------|--------------|-------------------|----------------|-------------------|
| `q_refund_window` | `policy_refund_v4` | Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. | `yes` | `no` | `yes` |

**Kết luận:**  
Run inject-bad vẫn retrieve đúng source `policy_refund_v4`, nhưng nội dung top-1 là bản stale `14 ngày làm việc`, khiến `hits_forbidden=yes`. Sau khi bật lại refund fix, top-1 chuyển sang bản canonical `7 ngày làm việc`, `hits_forbidden=no`. Đây là bằng chứng rõ nhất cho Sprint 3: dữ liệu bẩn làm retrieval nguy hiểm hơn, còn pipeline chuẩn loại/fix được stale policy.

### Merit: versioning HR — annual leave under 3 years

**Trước:**

| question_id | top1_doc_id | top1_preview | contains_expected | hits_forbidden | top1_doc_expected |
|-------------|-------------|--------------|-------------------|----------------|-------------------|
| `q_hr_annual_leave_under3` | `hr_leave_policy` | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. | `yes` | `no` | `yes` |

**Sau:**

| question_id | top1_doc_id | top1_preview | contains_expected | hits_forbidden | top1_doc_expected |
|-------------|-------------|--------------|-------------------|----------------|-------------------|
| `q_hr_annual_leave_under3` | `hr_leave_policy` | Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026. | `yes` | `no` | `yes` |

**Kết luận:**  
HR versioning ổn định ở cả before/after vì rule loại stale HR 2025 đã được giữ nguyên trong cả hai run. Các chunk chứa `10 ngày phép năm` đã bị quarantine trước khi embed, nên câu hỏi HR trả về đúng chính sách 2026: `12 ngày phép năm`.

---

## 3. Freshness & monitor

Kết quả freshness ở cả hai run đều là `FAIL`:

```text
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": ~1448, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Diễn giải:

- Pipeline đang chọn SLA freshness là 24 giờ.
- `latest_exported_at` trong manifest là `2026-04-11T00:00:00`.
- Tại thời điểm chạy ngày 2026-06-10, tuổi dữ liệu khoảng 1448 giờ, vượt xa SLA.
- Đây là vấn đề monitoring/freshness, không phải lỗi cleaning trực tiếp.
- Trong lab, pipeline vẫn `PIPELINE_OK` để tiếp tục demo retrieval, nhưng runbook cần ghi rõ: nếu production, freshness `FAIL` phải kích hoạt cảnh báo cho data owner hoặc yêu cầu re-export dữ liệu mới.

---

## 4. Corruption inject (Sprint 3)

Sprint 3 cố ý tạo dữ liệu xấu bằng lệnh:

```powershell
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

Ý nghĩa:

- `--no-refund-fix`: tắt rule sửa stale refund window từ `14 ngày làm việc` sang `7 ngày làm việc`.
- `--skip-validate`: cho phép pipeline tiếp tục embed dù có expectation halt fail.
- Kết quả mong muốn là collection Chroma bị nạp một chunk stale để chứng minh retrieval xấu hơn.

Cách phát hiện:

1. Expectation `refund_no_stale_14d_window` fail:
   ```text
   expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
   ```

2. Eval retrieval cho `q_refund_window` bị dính forbidden:
   ```text
   top1_preview = "Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn."
   contains_expected = yes
   hits_forbidden = yes
   ```

3. Sau khi chạy lại pipeline chuẩn, expectation pass và eval không còn forbidden:
   ```text
   expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
   top1_preview = "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
   hits_forbidden = no
   ```

---

## 5. Hạn chế & việc chưa làm

- `eval_retrieval.py` với `top_k=3` vẫn chưa hoàn hảo tuyệt đối: câu `q_p1_escalation` còn `contains_expected=no` trong cả before và after, dù `top1_doc_id=sla_p1_2026`. Nguyên nhân có thể là chunk P2 escalation cạnh tranh semantic với chunk P1 escalation trong embedding retrieval. Grading chính dùng `grading_run.py` có thể khác do dùng `top_k=5`, nhưng trong quality report cần ghi trung thực theo file eval Sprint 3.
- Freshness đang `FAIL` vì dữ liệu export đã quá cũ so với SLA 24h. Sprint 4 cần ghi rõ hành động trong runbook: cảnh báo data owner, re-export source, hoặc điều chỉnh SLA theo môi trường lab.
- Sprint 3 mới inject corruption vào refund policy. Có thể mở rộng thêm các corruption case khác như stale HR version, missing `access_control_sop`, duplicate SLA/P2 distractor, hoặc effective_date sai format.
- Chưa tạo file `before_after_eval.csv` gộp. Hiện report dẫn 2 file riêng: `eval_bad_inject.csv` và `eval_good_after_fix.csv`.
