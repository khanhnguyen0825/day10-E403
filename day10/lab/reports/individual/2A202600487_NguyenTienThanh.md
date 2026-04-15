# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Tiến Thành  
**Vai trò:** Monitoring / Ops Docs / Evaluation  
**Ngày nộp:** 2026-04-15

---

## 1. Tôi phụ trách phần nào?

Trong Lab Day 10, tôi phụ trách luồng quan sát vận hành gồm ba phần chính: (1) chạy kịch bản inject dữ liệu bẩn để kiểm thử độ bền retrieval, (2) đo before/after bằng eval CSV, và (3) viết tài liệu vận hành để đội có thể phản ứng khi freshness hoặc expectation bị lỗi. Các file tôi làm trực tiếp gồm `docs/runbook.md`, `docs/quality_report.md`, cùng các artifact ở `artifacts/eval/`, `artifacts/manifests/`, `artifacts/cleaned/`, `artifacts/quarantine/`.

Tôi phối hợp với thành viên làm cleaning/quality bằng cách dùng đúng các cờ pipeline do nhóm thiết kế: `--no-refund-fix --skip-validate` để mô phỏng tình huống xấu có chủ đích, sau đó chạy lại clean run bình thường để kiểm tra cơ chế hồi phục. Tôi cũng xác minh Chroma được cập nhật theo snapshot sạch thông qua dấu hiệu prune trong log.

Bằng chứng chạy thực tế:

- `run_id=inject-bad` trong `artifacts/logs/run_inject-bad.log`.
- `run_id=sprint3-final` trong `artifacts/logs/run_sprint3-final.log`.
- Hai file eval: `artifacts/eval/after_inject_bad.csv` và `artifacts/eval/before_after_eval.csv`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất tôi chọn là lấy **freshness boundary tại manifest sau khi publish** (sau bước embed) thay vì chỉ nhìn thời điểm chạy lệnh ETL. Lý do là mục tiêu vận hành của đội là đảm bảo dữ liệu thật sự đang phục vụ agent không quá cũ. Nếu chỉ check “pipeline vừa chạy xong” nhưng `latest_exported_at` trong dữ liệu nguồn đã cũ, hệ thống vẫn có thể trả lời đúng cú pháp nhưng sai thời điểm nghiệp vụ.

Vì vậy tôi dùng lệnh `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-final.json`, đặt SLA 24 giờ và đọc trực tiếp `latest_exported_at` trong manifest để tính `age_hours`. Kết quả FAIL với `age_hours` khoảng 120 giờ cho thấy vấn đề nằm ở nguồn export chưa được refresh, không phải lỗi chạy pipeline. Cách đo này giúp tách rõ hai loại sự cố: lỗi code ETL và lỗi độ mới dữ liệu.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi tập trung xử lý là **retrieval contamination** ở câu hỏi refund window. Triệu chứng là cùng top-k có cả bằng chứng đúng và bằng chứng cũ sai. Ở run inject (`inject-bad`), do bật `--no-refund-fix`, chunk stale “14 ngày làm việc” vẫn đi vào Chroma. Điều này được phát hiện bằng hai lớp kiểm tra:

1. Expectation trong log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1` (nhưng được cho qua vì `--skip-validate` để phục vụ demo Sprint 3).
2. Eval CSV: trong `after_inject_bad.csv`, dòng `q_refund_window` có `hits_forbidden=yes`.

Sau đó tôi chạy clean pipeline với `run_id=sprint3-final` (không dùng cờ inject). Log ghi `embed_prune_removed=1`, xác nhận chunk stale bị loại khỏi snapshot đang phục vụ. Kết quả sau sửa trong `before_after_eval.csv` cho thấy `q_refund_window` chuyển từ `hits_forbidden=yes` sang `hits_forbidden=no`, trong khi vẫn giữ `contains_expected=yes`.

---

## 4. Bằng chứng trước / sau

Hai bằng chứng ngắn tôi dùng để chứng minh tác động:

- Trước (inject-bad), file `artifacts/eval/after_inject_bad.csv`, dòng `q_refund_window`: `contains_expected=yes`, `hits_forbidden=yes`, `top1_preview` chứa “14 ngày làm việc”.
- Sau (clean), file `artifacts/eval/before_after_eval.csv`, cùng dòng `q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`, `top1_preview` chuyển về chunk “7 ngày làm việc”.

Ngoài ra, bằng chứng vận hành ở `run_sprint3-final.log` cho thấy expectation pass đầy đủ và có prune cũ: `embed_prune_removed=1`.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung một job monitoring tự động chạy freshness theo lịch (ví dụ mỗi 2 giờ) và phát cảnh báo khi `age_hours` vượt ngưỡng 12h (WARN sớm) thay vì chờ đến 24h mới FAIL. Việc này giúp đội xử lý proactively trước khi dữ liệu quá hạn SLA.
