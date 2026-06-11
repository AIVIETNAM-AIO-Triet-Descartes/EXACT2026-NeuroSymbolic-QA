# Task 3: Setup Deployment

**Tiến độ:** 0%

## Log
- `[2026-06-10 22:50] | Khởi tạo task | Content: Lên khung cho việc deploy server, database, và tự host LLM Inference server.`

## Checklist
- [ ] **Task 3.1: Thuê và Cài đặt VPS GPU**
  - [ ] Khảo sát/Thuê máy chủ (Khuyên dùng VRAM ~24GB để chạy nhẹ nhàng mô hình 8B FP16).
  - [ ] Cài đặt CUDA, Docker, và Python Env.
- [ ] **Task 3.2: Host local Inference Server (vLLM)**
  - [ ] Cài đặt package `vllm`.
  - [ ] Cấu hình chạy server vLLM (OpenAI API Format).
  - [ ] Đảm bảo expose `/v1/models` (bắt buộc cho check luật model ≤8B của BTC).
- [ ] **Task 3.3: Khởi chạy API Application**
  - [ ] Viết bash script hoặc Docker Compose để run cả `vLLM` server nội bộ + Web framework (FastAPI).
  - [ ] Security rules: chặn cổng vLLM public, chỉ expose cổng của `/predict`.

## Ghi chú - Lưu ý
- Luật nghiêm ngặt: KHÔNG được dùng 3rd party inference API, bắt buộc phải tự host LLM.
- Chú ý deadline cuộc thi đã dời sang 12/06/2026.
