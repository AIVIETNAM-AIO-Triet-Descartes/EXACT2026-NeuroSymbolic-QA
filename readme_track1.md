# 🧠 Hướng Dẫn Chạy Track 1 - Logic-Based Educational QA

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường, chuẩn bị dữ liệu/mô hình và chạy thử nghiệm hệ thống Neuro-Symbolic QA cho **Track 1 (Logic-Based Educational Queries)** của cuộc thi EXACT 2026.

---

## 📋 Mục lục
1. [Giới thiệu Track 1](#1-giới-thiệu-track-1)
2. [Cài đặt môi trường](#2-cài-đặt-môi-trường)
3. [Khởi chạy Inference Server (vLLM / llama.cpp)](#3-khởi-chạy-inference-server-vllm--llamacpp)
4. [Chạy Pipeline Offline (Batch Runner)](#4-chạy-pipeline-offline-batch-runner)
5. [Chạy trên Google Colab (Google Drive Cache)](#5-chạy-trên-google-colab-google-drive-cache)
6. [Định dạng dữ liệu đầu ra](#6-định-dạng-dữ-liệu-đầu-ra)

---

## 1. Giới thiệu Track 1

**Track 1** tập trung giải quyết các câu hỏi suy luận logic phức tạp được xây dựng từ tập mệnh đề First-Order Logic (FOL).
Hệ thống sử dụng kiến trúc lai hợp đồng thuận (Consensus Hybridization) gồm 3 tầng xử lý:
1. **Logic Tree (Đồ thị suy luận DAG):** Suy diễn tiến/lùi tự động bằng các luật logic (tốc độ cực nhanh < 1ms).
2. **Z3 Solver (Chứng minh hình thức):** Sử dụng Z3 Theorem Prover để kiểm tra tính thỏa mãn hệ thống logic (độ chính xác tuyệt đối).
3. **LLM Chain-of-Thought (Neural Fallback):** Sử dụng Qwen 2.5 7B Instruct để dịch thuật logic, sinh lời giải thích (Explanation) và suy luận ngữ nghĩa khi các bộ giải ký hiệu thất bại.

---

## 2. Cài đặt môi trường

### Yêu cầu hệ thống:
* **Hệ điều hành:** Linux, macOS hoặc Windows (được khuyến khích dùng Linux hoặc WSL2).
* **Python:** Phiên bản `3.10` trở lên.
* **GPU (nếu chạy LLM local):** GPU NVIDIA có tối thiểu 6GB-8GB VRAM để tải mô hình Qwen 2.5 7B GGUF quantized.

### Các bước cài đặt:

```bash
# 1. Di chuyển vào thư mục dự án
cd EXACT2026-NeuroSymbolic-QA

# 2. Tạo môi trường ảo python
python3 -m venv .venv
source .venv/bin/activate

# 3. Cài đặt các thư viện cơ bản
pip install -r requirements.txt

# 4. Cài đặt llama-cpp-python (Backend chạy LLM GGUF)
# Đối với hệ thống có hỗ trợ GPU CUDA (NVIDIA):
CMAKE_ARGS="-GGpuDast=ON" pip install llama-cpp-python --force-reinstall --no-cache-dir
```
*(Lưu ý: Trong file `requirements.txt` thư viện `llama-cpp-python` đã được comment lại để tránh lỗi compile tự động khi chạy trên môi trường không có sẵn compiler, bạn cần cài đặt thủ công tùy thuộc vào cấu hình phần cứng của mình).*

---

## 3. Khởi chạy Inference Server (vLLM / llama.cpp)

Hệ thống Neuro-Symbolic QA được thiết kế theo kiến trúc **Client-Server**. Mọi cuộc gọi LLM trong pipeline sẽ gửi request HTTP qua API tương thích OpenAI (không nạp trọng số mô hình trực tiếp trong tiến trình Python).

Bạn cần khởi chạy **Inference Server** trước khi chạy pipeline bằng một trong hai cách:

### Phương án A: Dành cho Production (Sử dụng `vLLM` - Khuyên dùng)
Yêu cầu GPU ≥24GB VRAM (như RunPod). Phương án này sử dụng mô hình gốc (Safetensors) tải từ HuggingFace và hỗ trợ cơ chế PagedAttention tối ưu hiệu năng.

1. Khởi chạy vLLM server:
   ```bash
   vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8001 --dtype float16
   ```
2. Trong file [configs/config.yaml](file:///home/nquocdat06/code/EXACT2026-NeuroSymbolic-QA/configs/config.yaml), thiết lập profile hoạt động sang `prod`:
   ```yaml
   llm:
     active: prod
   ```
*(Hoặc bạn có thể chạy script tiện ích `bash scripts/serve.sh` để tự động hóa toàn bộ việc cấu hình và chạy ngầm vLLM + FastAPI bằng `tmux`)*.

### Phương án B: Dành cho Development / Colab (Sử dụng GGUF qua `llama-cpp-python` / `llama-server`)
Phù hợp chạy trên GPU cá nhân (8GB VRAM) hoặc Google Colab (T4 GPU). Phương án này sử dụng các file mô hình phân mảnh GGUF (`qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` và part 2).

1. Khởi chạy server chạy ngầm ở cổng 8000:
   ```bash
   python3 -m llama_cpp.server --model ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf --port 8000 --n_gpu_layers -1 --n_ctx 2048 --alias Qwen/Qwen2.5-7B-Instruct
   ```
2. Trong file [configs/config.yaml](file:///home/nquocdat06/code/EXACT2026-NeuroSymbolic-QA/configs/config.yaml), thiết lập profile hoạt động sang `dev` (mặc định):
   ```yaml
   llm:
     active: dev
   ```

---

## 4. Chạy Pipeline Offline (Batch Runner)

Sau khi khởi động Inference Server thành công ở cổng tương ứng, dùng script `scripts/run_track1.py` để chạy đánh giá hàng loạt trên tập dữ liệu.

### Cú pháp cơ bản:
```bash
python scripts/run_track1.py \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions_test.json \
    --max-samples 5 \
    --evaluate
```

### Chi tiết các tham số dòng lệnh (CLI options):
| Tham số | Ý nghĩa | Mặc định |
| :--- | :--- | :--- |
| `--input`, `-i` | Đường dẫn tới file dataset logic đầu vào dạng JSON. | `Logic_Based_Educational_Queries.json` |
| `--output`, `-o` | Đường dẫn lưu file kết quả dự đoán dạng JSON. | `output/predictions.json` |
| `--max-samples`, `-n` | Giới hạn số lượng mẫu (sample) cần chạy thử nghiệm. | `None` (chạy toàn bộ) |
| `--start-sample` | Chỉ số mẫu bắt đầu chạy (0-indexed). | `0` |
| `--end-sample` | Chỉ số mẫu kết thúc chạy (exclusive). | `None` |
| `--no-llm` | Tắt LLM (chỉ sử dụng Z3 + Logic Tree). Chạy không cần GPU. | `False` |
| `--no-z3` | Tắt bộ giải Z3 (chỉ dùng Logic Tree + LLM). | `False` |
| `--evaluate` | So sánh kết quả dự đoán với ground truth và in bảng đánh giá độ chính xác (Accuracy). | `False` |
| `--log-level` | Mức độ log hiển thị ra console (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `--model`, `-m` | *(Deprecated)* Tham số này được giữ lại để tương thích ngược. Trình kết nối sẽ tự động lấy cấu hình server từ `configs/config.yaml`. | `./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` |

### Các ví dụ chạy cụ thể:

* **Chạy thử nhanh 5 mẫu (để kiểm tra môi trường):**
  ```bash
  python scripts/run_track1.py -n 5 --evaluate
  ```

* **Chạy đánh giá trên một dải dữ liệu (từ mẫu 50 đến mẫu 100):**
  ```bash
  python scripts/run_track1.py \
      --start-sample 50 \
      --end-sample 100 \
      --evaluate
  ```

* **Chạy ở chế độ Ký hiệu (Symbolic-Only - Không cần GPU và không cần bật Server):**
  ```bash
  python scripts/run_track1.py --no-llm --evaluate
  ```

---

## 5. Chạy trên Google Colab (Google Drive Cache)

Nếu chạy trên Google Colab, bạn hãy tận dụng notebook `run_track1_colab.ipynb` được thiết lập tối ưu sẵn các cell để tự động hóa quá trình:

1. **Mount Drive và cài dependencies:** Cài đặt nhanh dependencies và nạp file wheel `llama-cpp-python` có sẵn từ thư mục `Colab_Cache` trên Google Drive.
2. **Sao chép Model:** Di chuyển 2 file mô hình GGUF từ Drive sang bộ nhớ Colab để tăng tốc độ nạp mô hình.
3. **Khởi chạy Server chạy ngầm:**
   * Notebook cung cấp sẵn cell chạy ngầm `nohup python3 -m llama_cpp.server ...` trên cổng `8000` (sử dụng file GGUF local vừa copy).
   * Hoặc cung cấp tùy chọn chạy `vLLM` tự tải mô hình từ HuggingFace qua GPU T4.
4. **Chạy pipeline:** Gọi script chạy kiểm thử hoặc chạy đánh giá toàn bộ dataset.

---

## 6. Định dạng dữ liệu đầu ra

Sau khi chạy xong, kết quả sẽ được lưu tại thư mục chỉ định dưới dạng:

1. **`output/predictions.json` (File nộp bài chuẩn EXACT 2026):**
   ```json
   [
     {
       "idx": [[1, 2], [3, 4, 5]], 
       "answers": ["Yes", "A"],
       "explanation": [
         "Dựa trên tiền đề 1 và tiền đề 2...",
         "Phân tích lựa chọn A..."
       ]
     }
   ]
   ```
   * Trong đó `idx` chứa danh sách các chỉ số tiền đề (1-based index) được sử dụng để chứng minh cho từng câu hỏi tương ứng trong mẫu tin.

2. **`output/evaluation.json` (Nếu chạy kèm `--evaluate`):**
   * Chứa kết quả tổng hợp độ chính xác (Accuracy) chi tiết, được phân loại theo phương pháp giải thành công (Z3 solver, Logic Tree solver, LLM CoT, hoặc Default fallback).

3. **`logs/pipeline_[datetime].log`:**
   * Nhật ký chạy chi tiết, lưu vết toàn bộ quá trình dịch thuật, biên dịch mã Z3 và phản hồi từ LLM để phục vụ debug.
