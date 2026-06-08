# Kế hoạch Đánh giá Độc lập: RAG & Classifier
*Tài liệu phân chia công việc (Handoff) dành cho Teammates.*

## Mục tiêu
Tạo ra các script đánh giá độc lập (Unit Evaluation) cho 2 "chốt chặn" quan trọng nhất của hệ thống: **Formula RAG** (tìm công thức) và **Physics Classifier** (phân loại bài toán).
Việc đánh giá độc lập giúp khoanh vùng lỗi, trả lời câu hỏi: *Hệ thống giải sai là do RAG lấy nhầm công thức, Classifier định tuyến sai, hay do LLM/SymPy tính toán dở?*

---

## Task 1: Đánh giá chất lượng Formula RAG
**Mục đích:** Kiểm tra xem với một câu hỏi đầu vào, hệ thống có lấy ra đúng công thức vật lý cần thiết từ FAISS Vector DB hay không.

### Yêu cầu kỹ thuật:
- **Tạo script:** `scripts/evaluate_rag.py`
- **Dataset:** dùng `data/physics/physics_dev.csv` (200 câu, đã phân tầng đủ 8 prefix — KHÔNG cần tự sample first-N).
- **Luồng chạy (Bypass):** Script không chạy toàn bộ pipeline. NHƯNG **không được** truyền mỗi `question` thẳng vào RAG — Layer 1 của `formula_rag` match theo `domain` + `find`, và query Layer 2 = `f"{domain} {find} {question}"`. Vì vậy phải:
  1. Chạy `physics_parser_node` ở chế độ **regex-only** (vLLM tắt — `llm_server_available()` trả False, parser tự bỏ qua LLM augment) để lấy `domain` + `find`.
  2. Đưa state `{question, parsed_physics}` vào `formula_rag_node` (hoặc gọi trực tiếp hàm retrieval với `domain/find/question`).
  > Đo trên path regex-only là "sàn deterministic" (tái lập được, không phụ thuộc LLM). Nếu muốn đo thêm path có LLM augment thì chạy lần 2 khi server bật.
- **Output:** Xuất kết quả ra file `reports/rag_evaluation.csv` (hoặc `.xlsx`).

### Các cột (Columns) bắt buộc trong file Output:
1. `id`: Mã câu hỏi (VD: CH001).
2. `question`: Nội dung câu hỏi gốc.
3. `ground_truth_cot`: Các bước giải mẫu (Chain of Thought) từ dataset gốc. Cực kỳ quan trọng để con người đối chiếu xem công thức chuẩn cần dùng là gì.
4. `retrieved_formulas`: Danh sách các công thức mà FAISS trả về (chỉ cần lấy text ở trường `formula_sympy` hoặc `formula_natural`).
5. `keyword_match` *(Tùy chọn, chấm tự động)*: Thuật toán check nhanh xem các biến số xuất hiện trong `question` có nằm trong `retrieved_formulas` không (True/False).
6. `rank_of_correct` *(Tùy chọn, chấm tự động)*: Vị trí (1-based) của công thức ĐÚNG trong danh sách top-k retrieved (so khớp thô `formula_sympy` với công thức suy ra từ `ground_truth_cot`); `-1` nếu không có trong top-k. Cột này đo trực tiếp vấn đề "RAG chọn nhầm giữa 16 formula `ac_circuits`" — rank=1 là tốt, rank cao/`-1` là retrieval kém.
7. `human_eval` *(Cột trống)*: Để người review đánh giá thủ công (Điền: Đúng / Sai / Thiếu).

---

## Task 2: Đánh giá chất lượng Physics Classifier
**Mục đích:** Kiểm tra xem Classifier phân loại domain (chủ đề) và question_type (dạng bài) có chuẩn xác hay không, từ đó đảm bảo câu hỏi không bị fallback oan.

### Yêu cầu kỹ thuật:
- **Tạo script:** `scripts/evaluate_classifier.py`
- **Dataset:** `data/physics/physics_dev.csv` (200 câu, đủ 8 prefix).
- **Luồng chạy (Bypass):** Đọc dataset, chỉ khởi tạo và gọi duy nhất hàm phân loại của class `PhysicsClassifier`.
- **Output:** Xuất kết quả ra file `reports/classifier_evaluation.csv` (hoặc `.xlsx`).

### Các cột (Columns) bắt buộc trong file Output:
1. `id`: Mã câu hỏi.
2. `question`: Nội dung câu hỏi gốc.
3. `predicted_domain`: Chủ đề hệ thống dự đoán (VD: `ac_circuits`, `electrostatics`).
4. `predicted_type`: Dạng bài hệ thống dự đoán (VD: `YES_NO`, `SINGLE_FORMULA`, `MULTI_STEP`).
5. `target_variable`: Biến mục tiêu mà Classifier đang đoán mù (VD: `find = "U"`).
6. `ground_truth_answer_type` *(Cột check chéo tự động)*: Quét cột `answer` dataset gốc. **⚠️ KHÔNG dùng rule "chứa chữ cái → qualitative"** — đáp số LUÔN kèm unit có chữ (`0.045 J`, `640000 V/m`, `100 mJ`) nên rule đó sẽ gắn cờ nhầm gần như MỌI câu numeric. **Phải tái dụng `evaluation/answer_compare`** (đã có `parse_number` + logic phân loại kind chuẩn) — đừng tự viết lại:
   - `answer` ∈ {Yes, No} (case-insensitive) → `yes_no`.
   - `answer` chứa `;` → `multi_answer`.
   - Bóc unit rồi `parse_number()` ra số được → `numeric`.
   - Còn lại (text thuần không parse được số, vd "upward parabola") → `qualitative`.
7. `anomaly_flag` *(Tính tự động)*: Nếu `predicted_type` là dạng toán (vd `SINGLE_FORMULA`/`MULTI_STEP`) nhưng `ground_truth_answer_type` là `qualitative`/`yes_no`, đánh cờ `True` — báo hiệu Classifier route sai (sẽ fallback oan / giải sai dạng). Lưu ý: dataset **không có nhãn `domain`/`question_type` thật**, nên `predicted_domain` + `predicted_type` chỉ auto-check chéo được với answer-type ở mức thô này; phần còn lại để `human_eval` soi.

---

## Hướng dẫn thực thi chung cho cả 2 Task:
- **Dataset = `data/physics/physics_dev.csv`** (200 câu, ĐÃ phân tầng đủ 8 prefix: LD 59 · CH 43 · NL 28 · TD 26 · DDT 19 · THCB 12 · DT 10 · CHLT 3). Không cần tự sample first-N (first-N nặng TD, thiếu CH/CHLT/THCB). Cột: `id, question, cot, answer, unit`. (Tập lớn hơn: `physics_train.csv` 944 câu nếu cần.)
- **Tái dụng, đừng viết lại:** đọc CSV + `parse_number`/phân loại kind lấy từ `evaluation/answer_compare.py`; đọc dataset có thể tham khảo `scripts/demo_type2.py`.
- **Server-down safe:** code phải chạy không lỗi kể cả khi vLLM tắt. Task 1 chủ động chạy parser **regex-only** (xem trên); Task 2 (`PhysicsClassifier`) vốn không gọi LLM.
