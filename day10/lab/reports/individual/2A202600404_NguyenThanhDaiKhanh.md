# Báo cáo cá nhân — Lab Day 10

**Họ và tên:** Nguyễn Thành Đại Khánh
**Vai trò:** Ingestion & Cleaning Owner
**Độ dài:** ~490 từ

---

## 1. Phụ trách

Tôi phụ trách nhóm code làm sạch trong 	ransform/cleaning_rules.py (tạo 3 rules mới: missing_exported_at, làm sạch tag HTML và quarantine các chunk_text quá ngắn). Đầu ra sau khi clean (cleaned_records) và các dòng bị vứt bỏ (quarantine_records) được liên kết với file log để Thành viên 2 và 3 xây dựng Expectations và theo dõi Freshness.
Tôi cũng trực tiếp mở rộng docs/data_contract.md (khai báo Data source map) và điền SLA vào contracts/data_contract.yaml.

**Bằng chứng:** Xem các commit chứa đoạn regex _HTML_TAGS và điều kiện chunk_too_short trong logic clean_rows (sprint 1).

---

## 2. Quyết định kỹ thuật

**Quarantine vs Drop (Halt):** Trong luồng xử lý văn bản chứa HTML bẩn <script>alert(1)</script>, thay vì đẩy ra lỗi halt để dừng đứng toàn bộ quá trình ETL (tránh downtime lúc đang chạy nightly batch), tôi quyết định dùng Regex loại bỏ HTML.
Tuy nhiên, nếu văn bản sau khi bóc thẻ HTML trở nên quá ngắn (<15 ký tự) và mất ý nghĩa, nó sẽ tự động bị ném vào thư mục lưu trữ rtifacts/quarantine/ với lý do chunk_too_short thay vì bị ngầm xoá bỏ. Quyết định này giúp giữ luồng dữ liệu liên tục và vẫn rà soát lại (audit) được dữ liệu.

---

## 3. Sự cố / anomaly

**Triệu chứng:** Khi thử nghiệm regex cắt tag HTML và các note nội bộ như (ghi chú: ...), có một số dòng nguyên gốc chỉ chứa rác, nên cắt xong thì biến thành chuỗi rỗng (Empty text). 
Ban đầu pipeline vẫn đẩy các dòng rỗng này đi tiếp xuống khâu Embed, gây rác tốn tài nguyên VectorDB.

**Fix:** Tôi đã bổ sung kiểm tra kép if not text: ngay sau lệnh .strip(). Nếu text bằng rỗng sau khi xử lý, dòng đó sẽ vào Quarantine với cờ missing_chunk_text_after_html_strip.
Log bắt đầu báo chính xác: quarantine_records nhận đúng những dòng này.

---

## 4. Before/after

**Log:** Trước khi có rule, script HTML chui tọt vào DB. Sau khi làm sạch chuẩn ở run sprint1: 
aw_records=13, cleaned_records=7, quarantine_records=6.
Tất cả các chunk độc hại và chunk rỗng exported_at đều bị drop khỏi collection ở pipeline sạch.

**CSV:** Trong rtifacts/eval/before_after_eval.csv, không còn xuất hiện các dòng HTML hay văn bản trống không làm nhiễu kết quả Retrieval.

---

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian (khoảng 2h), thay vì dùng Regex thô sơ để bóc tách HTML, tôi sẽ cài đặt thư viện `BeautifulSoup` để xử lý DOM an toàn hơn (tránh cắt nhầm nội dung hữu ích). Đồng thời đổi phương thức Ingest từ Batch CSV hiện tại sang cấu hình Kafka để nạp dữ liệu Streaming thời gian thực.