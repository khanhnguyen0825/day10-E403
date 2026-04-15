# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

**Kịch bản 1 — Stale data (dữ liệu cũ còn trong Chroma):**

- Agent trả lời "Khách hàng có **14 ngày làm việc** để yêu cầu hoàn tiền" thay vì 7 ngày.
- Agent trả lời "Nhân viên dưới 3 năm được **10 ngày phép năm**" thay vì 12 ngày (chính sách 2026).

**Kịch bản 2 — Pipeline freshness FAIL:**

- `freshness_check` trả về `FAIL` — log ghi `freshness_check=FAIL {"age_hours": >24, "sla_hours": 24}`.
- Manifets cho thấy `latest_exported_at` quá cũ so với thời điểm hiện tại.

**Kịch bản 3 — Expectation halt:**

- Pipeline thoát với exit code `2`, log dòng `PIPELINE_HALT: expectation suite failed (halt).`.
- Số `cleaned_records` giảm bất thường so với lần chạy trước.

---

## Detection

| Metric              | Cách kiểm tra                                                      | Dấu hiệu bất thường                     |
| ------------------- | ------------------------------------------------------------------ | --------------------------------------- |
| `freshness_check`   | Xem dòng cuối của log `artifacts/logs/run_<id>.log`                | `FAIL` hoặc `WARN` kèm `age_hours > 24` |
| `hits_forbidden`    | Mở `artifacts/eval/before_after_eval.csv`, cột `hits_forbidden`    | Giá trị `yes` ở bất kỳ dòng nào         |
| `contains_expected` | Cùng file CSV trên, cột `contains_expected`                        | Giá trị `no`                            |
| Expectation         | Log `expectation[<name>] FAIL`                                     | Severity `halt` → pipeline dừng         |
| Quarantine surge    | `quarantine_records` trong manifest tăng đột biến so với run trước | >50% tổng raw_records bị quarantine     |

Lệnh tổng hợp nhanh:

```bash
# Xem freshness và expectation của run gần nhất
cat artifacts/logs/run_<run_id>.log | grep -E "freshness|expectation|PIPELINE"

# Kiểm tra manifest
cat artifacts/manifests/manifest_<run_id>.json
```

---

## Diagnosis

| Bước | Việc làm                                                                                                     | Kết quả mong đợi                                                                               |
| ---- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| 1    | Kiểm tra `artifacts/manifests/<run_id>.json` — xem `latest_exported_at`, `no_refund_fix`, `skipped_validate` | Xác định run có bật flag inject không; `latest_exported_at` có quá cũ không                    |
| 2    | Mở `artifacts/quarantine/<run_id>.csv` — xem các dòng bị loại                                                | Nhận diện loại lỗi (stale date, HTML, chunk ngắn, thiếu field) và tần suất                     |
| 3    | Mở `artifacts/cleaned/<run_id>.csv` — xem `chunk_text` còn lại                                               | Xác nhận chunk vẫn chứa nội dung chính xác (không phải phiên bản cũ)                           |
| 4    | Chạy `python eval_retrieval.py --out /tmp/diag_eval.csv`                                                     | Xem `contains_expected` và `hits_forbidden` — nếu `hits_forbidden=yes` tức Chroma còn chunk cũ |
| 5    | So sánh `cleaned_records` với run chuẩn gần nhất trong manifest                                              | Nếu giảm quá nhiều → expectation `halt` hoặc rule mới quá aggressive                           |

**Freshness FAIL cụ thể:**

- `age_hours` trong `freshness_check` detail = `(now - latest_exported_at)` theo giờ.
- Ví dụ: manifest sprint1 có `latest_exported_at = 2026-04-10T08:00:00`, chạy ngày 2026-04-15 → `age_hours ≈ 124h` >> SLA 24h → FAIL.

---

## Mitigation

**Kịch bản 1 — Stale/dirty data trong Chroma:**

1. Chạy lại pipeline với dữ liệu sạch để upsert + prune vector cũ:
   ```bash
   python etl_pipeline.py run --run-id recovery-$(date +%Y%m%d)
   ```
2. Xác nhận log có `embed_prune_removed=<N>` (số chunk cũ bị xóa).
3. Chạy lại eval để verify `hits_forbidden=no` và `contains_expected=yes`.

**Kịch bản 2 — Freshness FAIL/WARN:**

1. Kiểm tra nguồn export: dữ liệu raw có được export từ hệ thống nguồn trong 24h qua không.
2. Nếu nguồn chưa cập nhật → thông báo tạm (banner/alert) cho end-user rằng dữ liệu đang chờ làm mới.
3. Nếu có bản export mới → copy vào `data/raw/`, chạy lại pipeline:
   ```bash
   python etl_pipeline.py run --run-id refresh-$(date +%Y%m%d)
   ```
4. Freshness WARN (chưa FAIL): log và theo dõi; chưa cần rollback ngay.

**Kịch bản 3 — Expectation halt:**

1. Xem expectation nào FAIL: `grep "FAIL (halt)" artifacts/logs/run_<id>.log`
2. Nếu E7 (`chunk_id_not_null`) → raw CSV thiếu trường `chunk_id`; kiểm tra nguồn export.
3. Nếu E1/E3/E6 → dữ liệu đầu vào có vấn đề; kiểm tra `quarantine CSV`.
4. Không dùng `--skip-validate` trong production — chỉ dùng cho demo inject Sprint 3.

---

## Prevention

| Biện pháp                                        | Mô tả                                                                                    | Chủ sở hữu |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------- | ---------- |
| Expectation E7 `chunk_id_not_null` (halt)        | Dừng pipeline ngay nếu có chunk_id trống — tránh embed chunk vô danh vào Chroma          | Member 2   |
| Expectation E8 `metadata_fields_complete` (warn) | Cảnh báo sớm khi thiếu `doc_id` hoặc `effective_date` — catch trước khi Freshness fail   | Member 2   |
| Freshness SLA 24h trong `.env`                   | Tự động check sau mỗi run; set `FRESHNESS_SLA_HOURS=24` phù hợp với chu kỳ export        | Member 3   |
| Cleaning rule `missing_exported_at`              | Quarantine các dòng không có `exported_at` — loại stale chunk không truy vết được        | Member 1   |
| Monitoring manifest định kỳ                      | Chạy `python etl_pipeline.py freshness --manifest <latest>` trong CI hoặc cron hàng ngày | Member 3   |
| Không merge code bỏ qua `--skip-validate`        | Flag này chỉ dành cho demo Sprint 3; production pipeline KHÔNG được dùng                 | Cả nhóm    |

**Kết nối Day 11:** Nếu có guardrail thêm, bổ sung expectation loại `warn` cho `age_hours > 12` (pre-warn trước khi FAIL ở 24h), và tích hợp alert webhook khi freshness breach.
