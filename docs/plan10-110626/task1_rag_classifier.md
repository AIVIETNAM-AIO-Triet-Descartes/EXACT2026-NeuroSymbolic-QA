# Task 1: Xây dựng RAG & Classifier

**Tiến độ:** 100%

## Log
- `[2026-06-10 23:14] | Hoàn thành | Content: Hoàn thành Task 1.2 - Viết script evaluate_classifier.py.`
- `[2026-06-10 23:10] | Hoàn thành | Content: Hoàn thành Task 1.1 - Viết script evaluate_rag.py.`
- `[2026-06-10 22:50] | Khởi tạo task | Content: Setup script đánh giá độc lập cho Formula RAG và Physics Classifier.`

## Checklist
- [x] **Task 1.1: Viết script `scripts/evaluate_rag.py`**
  - [x] Đọc dataset `physics_dev.csv` (200 câu).
  - [x] Khởi tạo `physics_parser_node` ở chế độ regex-only (bypass LLM).
  - [x] Gọi retrieval component để lấy `retrieved_formulas`.
  - [x] Tính các score `keyword_match` và `rank_of_correct`.
  - [x] Xuất file report ra `reports/rag_evaluation.csv`.
- [x] **Task 1.2: Viết script `scripts/evaluate_classifier.py`**
  - [x] Đọc dataset `physics_dev.csv`.
  - [x] Gọi hàm phân loại `PhysicsClassifier` để test rule base.
  - [x] Parse `ground_truth_answer_type` từ file CSV sử dụng hàm `parse_number`.
  - [x] Tích hợp tính logic `anomaly_flag`.
  - [x] Xuất file report ra `reports/classifier_evaluation.csv`.

## Ghi chú - Lưu ý
- Cần tái sử dụng hàm `parse_number` và logic phân loại lấy từ `evaluation/answer_compare.py`. Đừng tự viết lại.
- **Server-down safe**: Đảm bảo code eval vẫn chạy bình thường khi không bật vLLM (bằng cách dùng regex-only).
