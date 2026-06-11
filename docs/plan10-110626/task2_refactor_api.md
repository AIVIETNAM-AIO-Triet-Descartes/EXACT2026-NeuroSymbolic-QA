# Task 2: Refactor API Layer theo Spec Chính Thức

**Tiến độ:** 100% 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩

## Log
- `[2026-06-10 23:35] | Hoàn thành task | Content: Refactored API theo đúng Spec 2026. Unified schema, loại bỏ router, update notation mapping.`

## Checklist
- [x] **Task 2.1: Cập nhật `api/schemas.py`**
  - [x] Thay đổi request schema với đủ trường bắt buộc: `{query_id, type, query, premises, options}`.
  - [x] Thay đổi response schema sang format LIST chứa 1 object cho mỗi query: `{query_id, answer, unit, explanation, premises_used, reasoning}`.
- [x] **Task 2.2: Refactor Endpoint `api/router.py` & `api/main.py`**
  - [x] Xóa/Cập nhật endpoint thành `POST /predict`.
  - [x] Bỏ việc dùng logic AI phân loại để định tuyến, chuyển sang dựa theo `request.type` do server committee gửi.
- [x] **Task 2.3: Build lại Response Payload**
  - [x] Bắt buộc echo (truyền lại nguyên vẹn) `query_id`.
  - [x] Mapping `unit` từ ký hiệu LaTeX sang ASCII-hóa (VD: Ω -> ohm, μF -> uF).
  - [x] Thêm object json `reasoning` (chia nhỏ fol, cot, proof).
  - [x] Xóa `confidence` khỏi json output (chỉ giữ cho logic chọn route internal).

## Ghi chú - Lưu ý
- Layer API cũ đang trả về dict 1 phần tử, cần sửa sang JSON LIST.
- Test endpoint cẩn thận cả với định dạng bài Type 1 (MCQ) và Type 2 (Numeric).
