# Prompt for Claude Code — Generate CV Project Description

## Context cho Claude Code

Bạn đã làm việc cùng tôi xuyên suốt toàn bộ quá trình phát triển dự án này. Dựa trên toàn bộ lịch sử các session làm việc, hãy viết một đoạn mô tả dự án cho CV của tôi theo yêu cầu bên dưới.

---

## Thông tin cố định (đừng thay đổi)

**Tên dự án:** EXACT 2026 — The 2nd International XAI Challenge for Transparent Educational Question-Answering  
**Tổ chức:** IEEE IJCNN 2026 / WCCI 2026 (Maastricht), hosted by URA Research Group, HCMUT  
**Vai trò của tôi:** Team Leader + Lead Engineer — Track 2 (Physics QA Pipeline)  
**Kết quả:** Chưa công bố chính thức — KHÔNG đề cập ranking trong mô tả này

---

## Những đóng góp cụ thể cần phản ánh

Dựa vào lịch sử session, hãy đề cập đến các đóng góp sau của tôi:

1. **Phân tích dataset** — Tự phân tích toàn bộ 1,352 bài toán vật lý, phân loại thành 8 nhóm theo prefix ID (LD, CH, NL, TD, DDT, THCB, DT, CHLT), xác định distribution, answer types, và đặc điểm kỹ thuật của từng nhóm

2. **Gap analysis** — Phát hiện database công thức ban đầu (20 công thức, 2 domain) chỉ cover ~35% dataset; xác định cần bổ sung 32 công thức mới trải qua 4 domain mới để đạt ~85% coverage

3. **Thiết kế kiến trúc pipeline** — Phác thảo toàn bộ kiến trúc Track 2: rule-based classifier → FormulaRAG → SymPy solver → LLM reasoning → CoT builder, với LLM code-generation fallback cho edge cases

4. **Data split** — Thiết kế và implement stratified train/dev/test split (70/15/15) đảm bảo coverage đầy đủ 8 nhóm câu hỏi trong mỗi tập, với integrity verification toàn bộ 1,352 rows

5. **Inference strategy** — Nghiên cứu và quyết định strategy: llama-cpp + Q4_K_M cho development (RTX 4060 8GB), vLLM + FP16 cho production VPS; chọn DeepSeek-R1-0528-Qwen3-8B làm backbone model dựa trên benchmark physics reasoning

6. **Deploy & endpoint** — Chịu trách nhiệm deploy toàn bộ system lên VPS, serve model qua vLLM, cấp prediction endpoint `/predict` và `/v1/models` cho ban tổ chức

---

## Context ban đầu và cải thiện cần thể hiện

**Tình huống ban đầu:**
- Formula database chỉ có 20 công thức, 2 domain (`circuits`, `electrostatics`) → cover ~35% dataset
- Không có phân tích dataset có hệ thống → không biết distribution, các dạng câu hỏi đặc biệt (vector problems, qualitative, multi-answer, Yes/No)
- Chưa có data split strategy → không có unseen test set để evaluate khách quan
- Chưa xác định được model và inference backend phù hợp với hardware constraint (8GB VRAM)

**Sau đóng góp:**
- Formula database được mở rộng lên 52 công thức, 6 domain → coverage tăng từ ~35% lên ~85%
- 8 nhóm bài toán được classify rõ ràng với routing riêng biệt → pipeline xử lý đúng từng loại (Yes/No, vector, qualitative, multi-answer, error propagation)
- Stratified split 944/200/208 (train/dev/test) đảm bảo đủ 8 nhóm trong mỗi tập → dev/test set hoàn toàn unseen
- Inference stack được chọn phù hợp: dev trên Q4_K_M (4.5GB VRAM), production trên vLLM FP16 (24GB VPS) → đúng compliance requirement của ban tổ chức (vLLM `/v1/models` verifiable)

---

## Yêu cầu về định dạng output

Viết **2 phiên bản**:

### Phiên bản 1 — Ngắn (3-4 dòng, cho phần Projects trong CV 1 trang)
- Súc tích, highlight được role + impact + số liệu key nhất
- Dùng bullet points hoặc prose ngắn

### Phiên bản 2 — Dài (8-12 dòng, cho portfolio / LinkedIn / CV 2 trang)
- Đủ context: tình huống ban đầu → đóng góp → cải thiện
- Có số liệu cụ thể
- Thể hiện được cả technical depth lẫn leadership

---

## Lưu ý khi viết

- Viết bằng **tiếng Anh** (chuẩn CV quốc tế)
- Dùng **action verbs** mạnh: Led, Designed, Implemented, Analyzed, Improved, Deployed...
- Số liệu phải chính xác theo những gì chúng ta đã làm thực tế trong session (không bịa thêm)
- KHÔNG đề cập đến ranking hay kết quả thi vì chưa có kết quả chính thức
- Nếu có thêm số liệu nào từ codebase mà tôi chưa liệt kê ở trên nhưng relevant, hãy bổ sung
