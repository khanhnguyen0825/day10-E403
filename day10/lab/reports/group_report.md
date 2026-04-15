# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên Nhóm:**  Nguyen Thanh Dai Khanh - Do Trong Minh - Nguyen Tien Thanh
**Ngày nộp:** 15-04-2026

---

## 1. Tóm tắt vai trò
| Tên | Vai trò (Day 10) | Tỷ lệ đóng góp |
|-----|------------------|-------|
| Nguyen Thanh Dai Khanh | Ingestion / Cleaning Owner | 33% |
| Do Trong Minh | Quality / Embed Owner | 33% |
| Nguyen Tien Thanh | Monitoring / Docs Owner | 34% |


## 2. Các Rules và Expectations Đã Khai Báo (Sprint 1-2)

### Bảng metric_impact (bắt buộc — chống trivial)
| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule: missing_exported_at | Không lỗi | quarantine_records = + 1 | Dòng thiếu ngày xuất bị loại bỏ khỏi luồng. |
| Rule: Strip HTML & Notes | Gây lỗi Script | clean được 2 dòng | Text <script>alert(1)</script> được xoá an toàn. |
| Rule: chunk_too_short | Lọt file rỗng | quarantine_records = + 1 | Chặn thành công chunk < 15 ký tự sau khi strip. |
| Expectation: chunk_id_not_null| Embed duplicate | halt pipeline | Tránh sập Database Chroma, cấm dòng không có ID. |
| Expectation: metadata_fields_complete | Thiếu Index | warn log | Cảnh báo Data thiếu field nhưng không làm downtime. |

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

**Kịch bản inject:**
Nhóm đã sử dụng cờ --no-refund-fix --skip-validate trên dòng lệnh để ép hệ thống nhận file bẩn (Version chính sách Refund 14 ngày đã cũ kỹ) mà bỏ qua khâu Validation Expectation. 

**Kết quả định lượng (từ CSV / bảng):**
Từ log eval trong rtifacts/eval/before_after_eval.csv so với fter_inject_bad.csv:
- Khi inject lỗi: contains_expected: true nhưng hits_forbidden: yes (Truy hồi phải đoạn text cũ 14 ngày làm việc).
- Sau khi chạy lại bản gốc (đã qua clean & validate 100%): hits_forbidden: no. Đặc biệt thành công nhất ở câu 3, Agent truy hồi xuất sắc ra bản HR Policy 2026 là 12 ngày phép (Top 1) thay vì 10 ngày như bản cũ. Câu lệnh Grading trả về 	op1_doc_matches: true.

---

## 4. Freshness & monitoring

**Kịch bản Freshness Check:**
SLA được nhóm chọn là 24 hours. Khi chạy kiểm tra trên Data thô 2026-04-10 trong ứng dụng hiện tại 15-04-2026, hệ thống trả về cảnh báo FAIL, ge_hours: 120h > SLA 24h. Log này cực kỳ chuẩn xác, chứng minh bộ Monitor đã theo sát quá trình Export và gửi đi thông điệp Mitigation đúng lúc để ngăn chặn RAG Agent bị lấy dữ liệu ôi thiu.

---

## 5. Liên hệ Day 09

**Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không?**
Có! Tập dữ liệu sau khi được Upsert theo chunk_id hoàn hảo (xóa rác và giữ bản mới nhất) sẽ nằm trong DB day10_kb. Khối Agent Day 09 (như 
etrieval.py Worker) chỉ cần cấu hình trỏ sang DB Index này là sẽ lấy được thông tin Policy mượt mà nhất mà không lo Hallucination hay ngộ nhận văn bản cũ.