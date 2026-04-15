# Quality report — Lab Day 10 (nhóm)

**run_id:** sprint3-final  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số               | Inject-bad run                          | Clean run (sprint3-final)     | Ghi chú                                                                 |
| -------------------- | --------------------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| raw_records          | 13                                      | 13                            | Cùng file nguồn `policy_export_dirty.csv`                               |
| cleaned_records      | 7                                       | 7                             | Inject-bad vẫn bị quarantine bởi các rule khác; chỉ bỏ refund fix       |
| quarantine_records   | 6                                       | 6                             | Hai run cùng số lượng quarantine nhưng khác nội dung chunk được giữ lại |
| Expectations (total) | 8                                       | 8                             |                                                                         |
| Expectations passed  | 7                                       | 8                             | Clean run: tất cả pass                                                  |
| Expectations failed  | 1                                       | 0                             |                                                                         |
| Expectation halt?    | **YES** — bỏ qua bằng `--skip-validate` | NO                            | Sprint 3 dùng flag inject để demo                                       |
| Freshness check      | FAIL (age ≈ 120.2h > SLA 24h)           | FAIL (age ≈ 120.5h > SLA 24h) | `latest_exported_at` = 2026-04-10; nguồn chưa cập nhật                  |

> **Lưu ý:** Kết quả freshness FAIL ở **cả hai run** vì `latest_exported_at` trong raw CSV vẫn là `2026-04-10T08:00:00` — phản ánh đúng thực tế nguồn dữ liệu chưa được refresh trong hơn 5 ngày. Đây là kịch bản cần trigger mitigation (xem Runbook).

---

## 2. Before / after retrieval (bắt buộc)

Kết quả eval từ 2 file:

- **Trước (sau inject-bad):** `artifacts/eval/after_inject_bad.csv`
- **Sau (clean pipeline):** `artifacts/eval/before_after_eval.csv`

### Câu hỏi then chốt: refund window (`q_refund_window`)

|                     | Sau inject-bad                         | Sau clean                     |
| ------------------- | -------------------------------------- | ----------------------------- |
| `contains_expected` | yes                                    | yes                           |
| `hits_forbidden`    | **yes** (`14 ngày làm việc` xuất hiện) | no                            |
| top1_preview        | chunk stale chứa policy cũ "14 ngày"   | chunk sạch: "7 ngày làm việc" |

**Giải thích:** Pipeline inject bỏ qua `apply_refund_window_fix=True` nên chunk stale version cũ (14 ngày) vẫn lọt vào top-k. Vì top-k còn chứa cả chunk đúng 7 ngày nên `contains_expected` vẫn là `yes`, nhưng `hits_forbidden=yes` cho thấy retrieval đã bị nhiễu và có nguy cơ trả lời sai. Clean pipeline kích hoạt rule `refund_no_stale_14d_window` → chunk cũ bị loại khỏi Chroma → retrieval sạch hoàn toàn (`hits_forbidden=no`).

### Merit — HR leave policy versioning (`q_leave_version`)

|                     | Sau inject-bad | Sau clean |
| ------------------- | -------------- | --------- |
| `contains_expected` | yes            | yes       |
| `hits_forbidden`    | no             | no        |
| `top1_doc_expected` | yes            | yes       |

**Giải thích:** Với dataset hiện tại, inject-bad không làm hỏng truy hồi của câu HR leave. Cả hai run đều trả `top1_doc_id = hr_leave_policy` và không có từ khóa cấm `10 ngày phép năm` trong top-k. Vì vậy tác động suy giảm đo được rõ ràng nhất nằm ở câu refund window, không phải ở HR leave.

---

## 3. Freshness & monitor

**SLA được chọn:** `FRESHNESS_SLA_HOURS = 24` (cấu hình trong `.env` và `contracts/data_contract.yaml`)

**Lệnh kiểm tra:**

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-final.json
```

**Kết quả thực tế run sạch:** `FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.486, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`

**Giải thích:**

- `age_hours ≈ 120.486h` = khoảng cách từ `2026-04-10T08:00:00` tới thời điểm chạy clean run ngày `2026-04-15`.
- SLA 24h: dữ liệu phải được export trong vòng 24h qua → vi phạm rõ ràng.
- Cơ chế: `monitoring/freshness_check.py` đọc `latest_exported_at` từ manifest, tính `age_hours = (now_utc - latest_exported_at).total_seconds() / 3600`, so sánh với SLA.
- Status: `PASS` nếu `age_hours ≤ sla`; `WARN` nếu `sla < age_hours ≤ sla*2`; `FAIL` nếu `age_hours > sla*2`.

**Hành động:** Cần trigger nguồn export cập nhật dữ liệu; xem Runbook mục Mitigation.

---

## 4. Corruption inject (Sprint 3)

**Loại corruption được inject:** Stale policy chunks (version cũ của refund window và HR leave policy).

**Cơ chế:**

- Lệnh: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- `--no-refund-fix`: bỏ qua `cleaning_rules.apply_refund_window_fix` → chunk stale "14 ngày" KHÔNG bị quarantine → embed vào Chroma.
- `--skip-validate`: bỏ qua halt từ expectation suite để pipeline tiếp tục embed dù có lỗi.

**Phát hiện bằng eval:**

- `eval_retrieval.py` query câu hỏi `q_refund_window` → Chroma trả top-k với `hits_forbidden=yes` (tìm thấy "14 ngày làm việc" — từ khóa cấm).
- Đồng thời `contains_expected=yes`, nghĩa là top-k chứa cả chunk đúng lẫn chunk stale. Đây là lỗi retrieval contamination: hệ thống chưa hoàn toàn mất đáp án đúng, nhưng đã lẫn bằng chứng sai trong kết quả truy hồi.

**Phát hiện bằng expectation:**

- E3 `refund_no_stale_14d_window` → FAIL (có chunk chứa "14 ngày làm việc" trong cleaned).
- Log thực tế: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`

**Recovery:** Chạy clean pipeline (không có flag inject) → log ghi `embed_prune_removed=1`, xác nhận chunk stale đã bị xóa khỏi Chroma → eval trở về `contains_expected=yes, hits_forbidden=no`.

---

## 5. Hạn chế & việc chưa làm

- `grading_questions.json` hiện chưa có trong `day10/lab/data/`, nên chạy `python grading_run.py --out artifacts/eval/grading_run.jsonl` đang lỗi `FileNotFoundError`. Khi giảng viên cung cấp file này, có thể chạy lại ngay mà không cần đổi code.
- Freshness check chỉ đo tại boundary **publish** (sau embed); boundary **ingest** (khi nhận raw CSV) chưa được đo riêng.
- Eval hiện dùng keyword matching (không phải LLM-judge) — đủ cho demo nhưng không bắt được lỗi ngữ nghĩa phức tạp.
- Chưa có automated alert (webhook/email) khi freshness FAIL — cần tích hợp ở Day 11.
