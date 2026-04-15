# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đỗ Trọng Minh  
**Vai trò:** Quality & DB Owner — Expectations & Embed Idempotency  
**Ngày nộp:** 15 tháng 4, 2026  
**Độ dài:** 580 từ

---

## 1. Tôi phụ trách phần nào? (105 từ)

**File / module:**
- `quality/expectations.py` — Thêm 2 expectation mới (E7 halt, E8 warn)
- `docs/pipeline_architecture.md` — Mermaid diagram + idempotency strategy

**Kết nối với thành viên khác:**
Tôi làm việc tiếp theo sau Thành viên 1 (cleaning rules). Input của tôi là `cleaned_records` (11 rows) từ `artifacts/cleaned/cleaned_sprint2_member2.csv`. Output là:
- Expectations validation log → sprint2_member2 manifest
- Architecture documentation giúp Thành viên 3 (observability) hiểu luồng freshness check

**Bằng chứng (commit):**
```
feat(quality): Add 2 new expectations (E7, E8) for data validation
docs(architecture): Add detailed pipeline architecture with Mermaid diagram
```

---

## 2. Một quyết định kỹ thuật (140 từ)

**Quyết định: Halt vs Warn cho Expectations**

Tôi đưa ra quyết định **phân tầng 2 loại expectation severity**:

- **E7 (HALT - chunk_id_not_null)**: Chunk_id là khóa để upsert idempotent vào ChromaDB. Nếu chunk_id rỗng → không thể track, duplicate vector, hoặc lost data → **dừng pipeline ngay**.

- **E8 (WARN - metadata_fields_complete)**: Doc_id / effective_date thiếu ảnh hưởng search context nhưng không phá vỡ embedding. Log cảnh báo nhưng cho pipeline tiếp tục.

**Idempotency Strategy**: Dùng `col.upsert(ids=chunk_ids, ...)` + prune orphans. Rerun 2 lần trên cùng cleaned_records → collection size không thay đổi (tránh duplicate vector, không bị top-k pollution). Chi tiết: `docs/pipeline_architecture.md` section 3.

---

## 3. Một lỗi hoặc anomaly đã xử lý (135 từ)

**Triệu chứng:** Sprint 2 test chạy → HALT (status = FAIL, 3/8 expectation failed)

**Expectations Failed (Halt triggers):**
1. `refund_no_stale_14d_window` — violations=1: Một chunk policy_refund_v4 vẫn chứa "14 ngày làm việc" (chưa fix)
2. `effective_date_iso_yyyy_mm_dd` — non_iso_rows=1: Một chunk có effective_date không ISO (format ngày tháng lỏng)
3. `hr_leave_no_stale_10d_annual` — violations=1: HR doc vẫn xác định "10 ngày phép" (conflict version cũ)

**Fix Applied:** Đây là kỳ vọng — Sprint 1 (TV1) chưa hoàn toàn fix hết. Tôi log rõ violations để TV1 cải tiến cleaning rules. Pipeline halt là **đúng hành vi** để tránh embed dữ liệu bẩn (tương ứng injection test Sprint 3 của TV3).

---

## 4. Bằng chứng trước / sau (125 từ)

**Run_id:** `sprint2_member2`  
**Timestamp:** 2026-04-15T05:13:34.799814+00:00

**Manifest Snapshot:**
```
raw_records: 13
cleaned_records: 11 (84.6% pass-through)
quarantine_records: 2 (lỗi doc_id allowlist / empty chunk)
expectations_total: 8
expectations_passed: 5 (E1, E2, E4, E7 new, E8 new)
expectations_failed: 3 (E3, E5, E6 — baseline, chứng minh data bẩn exists)
halt: true
```

**CSV Evidence:**
- `artifacts/cleaned/cleaned_sprint2_member2.csv` — 11 rows ready for embed to day10_kb collection
- `artifacts/quarantine/quarantine_sprint2_member2.csv` — 2 rows excluded (invalid doc_id / empty chunk)
- `artifacts/logs/run_sprint2_member2.log` — full expectation detail

---

## 5. Cải tiến tiếp theo (75 từ)

Nếu có thêm 2 giờ:

1. **Upsert timeout + retry**: ChromaDB upsert có thể timeout trên large dataset. Thêm exponential backoff + fallback to batch.

2. **Metadata consistency check**: Viết E9 (warn) — đảm bảo `run_id` trong metadata match manifest. Giúp audit trail clear.

3. **Chunk size auto-adjust**: Kiểm tra distribution chunk_text length và warn nếu outlier (quá dài / quá ngắn).
