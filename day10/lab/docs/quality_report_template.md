# Quality report — Lab Day 10 (nhóm)

**run_id:** inject-bad vs 2026-06-10T06-33Z  
**Ngày:** 2026-06-10

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước | Sau | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 247 | 247 | Cùng một raw CSV đầu vào |
| cleaned_records | 41 | 41 | Số lượng cleaned không đổi, nhưng nội dung refund khác nhau do bad run tắt refund fix |
| quarantine_records | 206 | 206 | Số lượng quarantine không đổi trong experiment này |
| Expectation halt? | Có lỗi nhưng bị skip | Không halt | Bad run có `refund_no_stale_14d_window FAIL violations=3` nhưng dùng `--skip-validate`, good run pass toàn bộ halt expectations |

---

## 2. Before / after retrieval (bắt buộc)

> File eval:
> - `eval_bad_inject.csv`
> - `eval_good_after_fix.csv`

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước:** q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi đơn được xác nhận?,policy_refund_v4,Nội dung không rõ ràng: Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn.,yes,yes,yes,3

**Sau:** q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi đơn được xác nhận?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,yes,3


**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước:**  q_hr_annual_leave_under3,Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?,hr_leave_policy,Nội dung không rõ ràng: Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026.,yes,no,yes,3

**Sau:**  q_hr_annual_leave_under3,Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?,hr_leave_policy,Nội dung không rõ ràng: Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026.,yes,no,yes,3


---


## 3. Freshness & monitor

Kết quả `freshness_check` hiện là `WARN`:

```text
freshness_check=WARN {"reason": "no_timestamp_in_manifest", ...}
```

Giải thích: manifest có `run_timestamp`, nhưng fresheness checker hiện báo `no_timestamp_in_manifest`.

SLA đề xuất:
- `PASS`: manifest có timestamp parse được và latest export nằm trong ngưỡng chấp nhận.
- `WARN`: thiếu hoặc không parse được timestamp, nhưng pipeline vẫn có cleaned CSV và manifest.
- `FAIL`: không có manifest, không có cleaned artifact hoặc dữ liệu cũ vượt ngưỡng SLA.

---

## 4. Corruption inject (Sprint 3)

Corruption được inject bằng lệnh:
```
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

Bằng chững phát hiện lỗi:
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=3
WARN: expectation failed but --skip-validate → tiếp tục embed
```

---

## 5. Hạn chế & việc chưa làm

- Metric `contain_expected` không tăng (19/21).
- Metric `top1_doc_expected` đều đạt (20/21).
- `fairness_check` vẫn đang là `WARN` do vấn đề về timestamp.
