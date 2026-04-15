# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Thành Đại Khánh 
**Vai trò:** Ingestion & Cleaning - Sprint 1
**Ngày nộp:** 15-04-2026

---

## 1. Tôi phụ trách phần nào?

**File / module:**
- `transform/cleaning_rules.py`: Tác giả chính của 3 rule làm sạch mới: `missing_exported_at`, Strip HTML tags/Internal notes bằng Regex, và Threshold lọc chunk quá ngắn `chunk_too_short`.
- `docs/data_contract.md`: Điền Source Map (định nghĩa Data source từ IT Helpdesk và HR System, cảnh báo Failure Modes).
- `contracts/data_contract.yaml`: Điền thông tin Ownership (Data Engineering Team) và gán `freshness_hours: 24` cho SLA.
- `data/raw/policy_export_dirty.csv`: Injection thêm 3 dòng dữ liệu bẩn để test pipeline.

**Kết nối với thành viên khác:**
Code làm sạch của tôi chuẩn hóa bảng dữ liệu thô đầu vào, cung cấp đầu ra `cleaned_sprint1.csv` đủ sạch để Thành viên 2 viết `expectations.py` (Validation) và Thành viên 3 đánh giá hệ thống (Monitor/Eval). 

**Bằng chứng (commit / comment trong code):**
Đoạn mã tôi đã viết nằm trong hàm `clean_rows` của `cleaning_rules.py`, xử lý loại bỏ HTML tags `_HTML_TAGS.sub("", text).strip()` và bắt điều kiện `# --- Rule 4: Chunk too short ---`.

---

## 2. Một quyết định kỹ thuật

**Quy tắc Quarantine vs Drop thay vì báo lỗi (Halt):**
Khi làm sạch nội dung, nhóm tôi gặp phải một dòng dữ liệu chứa Script thẻ bẩn: `<script>alert(1)</script>`. Thay vì bắt Expectation và báo `halt` để dừng đứng toàn bộ quá trình ETL (việc này sẽ làm gián đoạn pipeline thực tế chạy ban đêm), tôi quyết định dùng Regex để gỡ bỏ (Strip) hoàn toàn đoạn Script đó ra khỏi văn bản. 

Tuy nhiên, tôi nhận thấy có những trường hợp sau khi gỡ code bẩn, nội dung văn bản còn lại không có giá trị hoặc quá ngắn (dưới 15 ký tự). Do đó, tôi viết thêm quyết định chặn 2 lớp: "Nếu gỡ xong mà văn bản nhỏ hơn 15 ký tự, nó sẽ bị chuyển vào thư mục Archive Quarantine với mã lỗi `chunk_too_short` chứ không bị drop hoặc báo lỗi ra ngoài". Điều này giữ cho Pipeline an toàn, chạy thông suốt mà vẫn bảo tồn tối đa các chunk hữu ích còn lưu lại.

---

## 3. Một lỗi hoặc anomaly đã xử lý 

**Mô tả triệu chứng:** Trong quá trình chạy thử Rule cắt HTML, có một anomaly xảy ra là một số nội dung chỉ chứa rác hoặc câu chữ vớ vẩn. Lúc đầu regex cắt sạch luôn làm chuỗi `text` trở thành `Empty` (Rỗng). Pipeline lúc chưa được fix đã đẩy dòng rỗng này đi tiếp xuống khâu Embed, gây tốn tài nguyên ChromaDB vô ích và làm nhiễu kết quả Retrieval.

**Fix và Metric phát hiện:** Tôi đã bổ sung thêm cờ kiểm tra kép vào hàm `clean_rows`. Sau lệnh stripped nội dung, hệ thống sẽ chạy 1 khối `if not text:` để quét. Nếu text bằng rỗng, nó lập tức gán `reason`: `missing_chunk_text_after_html_strip` và đẩy vào `quarantine`. 

**Bằng chứng (Trích Log):** 
Metric đã phát hiện chính xác, log in ra: `run_id=sprint1 | raw_records=13 | cleaned_records=7 | quarantine_records=6`. Phân hệ làm sạch đã hoàn thành xuất sắc nhiệm vụ bảo vệ dữ liệu.

---

## 4. Bằng chứng trước / sau

Quá trình làm sạch của tôi đã bảo đảm Pipeline không thu nạp các dòng rác và giữ lại đủ nội dung giá trị. Dưới đây là trích log Terminal của `run_id=sprint1` chứng minh pipeline đầu cuối Ingest & Clean hoạt động ổn định trước khi chuyển giao cho khâu Validation của Thành viên 2:

```text
run_id=sprint1
raw_records=13
cleaned_records=7
quarantine_records=6
cleaned_csv=artifacts\cleaned\cleaned_sprint1.csv
quarantine_csv=artifacts\quarantine\quarantine_sprint1.csv
expectation[min_one_row] OK (halt) :: cleaned_rows=7
```
(Dòng chứa HTML bẩn `Xin hãy gửi yêu cầu vào support@example.com để biết thêm chi tiết. <script>alert(1)</script>` đã được bóc tách và chunk ID 13 đã nạp an toàn).

---

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian (khoảng 2h), thay vì dùng Regex thô sơ để bóc tách HTML, tôi sẽ cài đặt thư viện `BeautifulSoup` để xử lý DOM an toàn hơn (tránh cắt nhầm nội dung hữu ích). Đồng thời đổi phương thức Ingest từ Batch CSV hiện tại sang cấu hình Kafka để nạp dữ liệu Streaming thời gian thực.
