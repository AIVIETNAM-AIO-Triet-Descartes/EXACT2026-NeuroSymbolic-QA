# 🧠 EXACT2026-NeuroSymbolic-QA: Hybrid Neuro-Symbolic QA System

[![EXACT 2026](https://img.shields.io/badge/EXACT%202026-XAI%20Challenge-blue.svg)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Submission to EXACT 2026** — 2nd International XAI Challenge for Transparent Educational Question-Answering (IEEE IJCNN 2026).  
> **Development Team:** URA Research Group, HCMUT Vietnam (AIVIETNAM-AIO-Triet-Descartes).  
> **Triết lý cốt lõi:** *"Không để LLM tự làm toán — LLM chỉ làm nhiệm vụ giao tiếp, dịch thuật và Chain-of-Thought; phần tính toán và suy luận logic giao cho các công cụ toán học và chứng minh chuyên dụng."*

---

## 📋 Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Hướng dẫn cài đặt](#4-hướng-dẫn-cài-đặt)
5. [Cấu hình LLM Backend (vLLM / llama.cpp)](#5-cấu-hình-llm-backend-vllm--llamacpp)
6. [Hướng dẫn chạy Pipeline Offline (Batch Evaluation)](#6-hướng-dẫn-chạy-pipeline-offline-batch-evaluation)
7. [Hướng dẫn chạy trên Google Colab (với Google Drive Cache)](#7-hướng-dẫn-chạy-trên-google-colab-với-google-drive-cache)
8. [Hướng dẫn chạy API Server (Phục vụ Live API Round)](#8-hướng-dẫn-chạy-api-server-phục-vụ-live-api-round)
9. [Chạy Unit Tests](#9-chạy-unit-tests)
10. [Giấy phép (License)](#10-giấy-phép-license)

---

## 1. Tổng quan dự án

Hệ thống **NeuroSymbolic-QA** giải quyết 2 bài toán (Track) chính của cuộc thi EXACT 2026:
* **Track 1 (Logic-Based Educational Queries):** Giải quyết câu hỏi suy luận logic First-Order Logic (FOL).
* **Track 2 (Physics Problems):** Giải quyết bài toán tính toán vật lý (từ trường, điện trường, cơ học).

Để đảm bảo độ chính xác tuyệt đối, hệ thống kết hợp sức mạnh suy luận ngôn ngữ của **LLM mã nguồn mở (≤ 8B tham số)** với khả năng tính toán chính xác của **Z3 Theorem Prover** và **SymPy**.

---

## 2. Kiến trúc hệ thống

```
                           HTTP Request (POST /predict)
                                        │
                                        ▼
                                 [FastAPI Router]
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  ▼ (Type 1: Logic)                           ▼ (Type 2: Physics)
          [NL to FOL Parser]                          [Physics Parser]
                  │                                           │
                  ▼                                           ▼
         [Logic Tree / Z3 Solver]                     [Formula RAG (FAISS)]
                  │                                           │
                  ▼                                           ▼
          [LLM CoT Fallback]                         [SymPy / Vector Solver]
                  │                                           │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                               [Explainer Agent]
                                        │
                                        ▼
                               HTTP Response JSON
```

---

## 3. Cấu trúc thư mục

```
EXACT2026-NeuroSymbolic-QA/
│
├── api/                  # 🌐 [API GATEWAY] - Cổng giao tiếp FastAPI
│   ├── main.py           # Entry point FastAPI, định nghĩa các endpoint và proxy
│   ├── schemas.py        # Schema đầu vào/đầu ra chính thức (Pydantic models)
│   ├── router.py         # Router định tuyến Type 1 / Type 2
│   └── logger.py         # Logging JSON định dạng chuẩn debug
│
├── pipeline/             # ⚡ [CORE PIPELINE] - Logic xử lý Neuro-Symbolic
│   ├── state.py          # State contract chung của pipeline
│   ├── type1/            # Track 1 (Logic Tree + Z3 Solver)
│   └── type2/            # Track 2 (SymPy Solver + Vector Solver + FAISS Formula RAG)
│
├── llm/                  # 🤖 [LLM MODULE] - Module quản lý và gọi LLM (vLLM / llama.cpp)
│   ├── loader.py         # Module load model và kiểm tra trạng thái backend
│   ├── inference.py      # OpenAI-compatible Client Wrapper
│   └── prompt_templates.py # Quản lý prompts hệ thống
│
├── configs/              # ⚙️ [CONFIGURATION] - File YAML quản lý config hệ thống
│   └── config.yaml       # Đổi backend dev <-> prod chỉ bằng 1 dòng
│
├── scripts/              # 🛠️ [SCRIPTS] - Các file chạy offline và đánh giá
│   ├── run_track1.py     # Chạy offline batch evaluation cho Track 1
│   ├── demo_type2.py     # Chạy offline demo và evaluation cho Track 2
│   ├── build_faiss_index.py # Xây dựng vector DB cho công thức vật lý
│   └── serve.sh          # Script khởi động nhanh API Gateway
│
├── tests/                # ✅ [UNIT TESTS] - Bộ test kiểm thử tự động
├── data/                 # 📊 [DATASET] - Dữ liệu thô, dữ liệu RAG
├── output/               # 💾 [OUTPUTS] - Lưu kết quả predictions và evaluation
├── run_track1_colab.ipynb # 📓 Notebook hướng dẫn chạy trên Colab với Google Drive Cache
├── requirements.txt      # 📦 Thư viện Python cần thiết
└── README.md             # Tài liệu này
```

---

## 4. Hướng dẫn cài đặt

### Yêu cầu hệ thống:
* **Hệ điều hành:** Linux (vLLM chạy tốt nhất trên Ubuntu/WSL2).
* **Python:** Phiên bản 3.10 trở lên.
* **GPU:** Khuyên dùng GPU NVIDIA CUDA (ví dụ: RTX 3060+, Tesla T4, A10G) có tối thiểu 8GB VRAM.

### Các bước cài đặt:

```bash
# 1. Clone repository
git clone https://github.com/AIVIETNAM-AIO-Triet-Descartes/EXACT2026-NeuroSymbolic-QA.git
cd EXACT2026-NeuroSymbolic-QA

# 2. Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 5. Cấu hình LLM Backend (vLLM / llama.cpp)

Hệ thống hỗ trợ 2 chế độ gọi LLM thông qua file cấu hình `configs/config.yaml`. Bạn chỉ cần chỉnh sửa thuộc tính `active: dev` hoặc `active: prod` tại dòng đầu của file.

### Chế độ Dev (sử dụng llama.cpp / GGUF)
Chế độ này phù hợp khi chạy thử nghiệm trên máy local có VRAM hạn chế (chạy qua file GGUF 4-bit).
1. Tải mô hình Qwen 2.5 7B Instruct GGUF và đặt tại thư mục gốc:
   * `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf`
   * `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf`
2. Đặt `active: dev` trong `configs/config.yaml`.
3. Bật llama-server (ví dụ cổng 8000) và thực thi script.

### Chế độ Prod (sử dụng vLLM / Safetensors)
Chế độ này sử dụng vLLM trên Linux/WSL2 cho hiệu năng tối đa (chạy qua FP16/Safetensors).
1. Cài đặt vLLM: `pip install vllm`
2. Khởi chạy vLLM server:
   ```bash
   vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8001 --dtype float16
   ```
3. Đặt `active: prod` trong `configs/config.yaml` để hướng Client của FastAPI gọi tới cổng `8001`.

---

## 6. Hướng dẫn chạy Pipeline Offline (Batch Evaluation)

### 6.1 Chạy Track 1 (Logic)

Chạy script `scripts/run_track1.py` để xử lý tập dữ liệu logic và tự động chấm điểm nếu có nhãn ground truth:

```bash
# Chạy đánh giá trên 5 mẫu đầu tiên bằng GPU
python scripts/run_track1.py \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions_test.json \
    --model ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf \
    --max-samples 5 \
    --gpu-layers -1 \
    --evaluate

# Chạy đánh giá trên dải dữ liệu cụ thể (Mẫu 50 đến 100)
python scripts/run_track1.py \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions_50_100.json \
    --model ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf \
    --start-sample 50 \
    --end-sample 100 \
    --gpu-layers -1 \
    --evaluate
```

Các tham số chính:
* `--input`: Đường dẫn file dữ liệu `.json`.
* `--output`: Đường dẫn lưu file kết quả định dạng JSON của ban tổ chức.
* `--model`: Đường dẫn đến file mô hình GGUF. **Hỗ trợ cả đường dẫn tuyệt đối** (ví dụ: `/content/drive/MyDrive/...`).
* `--max-samples`: Giới hạn số lượng mẫu cần chạy.
* `--gpu-layers`: Số lượng layer đẩy lên GPU (`-1` là đẩy toàn bộ).
* `--evaluate`: Đánh giá độ chính xác (Accuracy) so với nhãn gốc.

---

### 6.2 Chạy Track 2 (Physics)

Chạy demo và đánh giá độ chính xác cho pipeline vật lý:

```bash
# Chạy demo cơ bản sử dụng SymPy + Vector Solver (Không dùng LLM)
python scripts/demo_type2.py --limit 100

# Chạy demo kết hợp LLM để phân tích đề và tự động fallback
python scripts/demo_type2.py --limit 100 --use-llm
```

---

## 7. Hướng dẫn chạy trên Google Colab (với Google Drive Cache)

Nếu bạn không có phần cứng GPU NVIDIA local đủ mạnh, bạn có thể thực hiện chạy thử nghiệm trên Google Colab qua file notebook `run_track1_colab.ipynb` được đính kèm ở thư mục gốc:

1. Tải notebook `run_track1_colab.ipynb` và mở trên môi trường Colab.
2. Chọn loại Runtime: **T4 GPU** (hoặc GPU mạnh hơn).
3. Kết nối Google Drive để mount thư mục chứa cache model và pre-compiled wheel.
4. Có hai cách cấu hình model trên Colab:
   * **Cách 1 (Khuyên dùng):** Copy file mô hình từ Drive sang ổ cứng máy ảo Colab để tăng tốc độ suy luận.
   * **Cách 2:** Đọc file mô hình trực tiếp từ Drive thông qua liên kết Fuse của Colab (không cần chờ copy, cấu hình đường dẫn tuyệt đối tới Drive).
5. Thực thi các cell cài đặt và chạy thử nghiệm.

---

## 8. Hướng dẫn chạy API Server (Phục vụ Live API Round)

Cổng API server FastAPI chịu trách nhiệm giao tiếp chính thức với hệ thống chấm điểm của ban tổ chức.

### Khởi động API Server:
```bash
# Cách 1: Chạy bằng lệnh uvicorn trực tiếp
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Cách 2: Chạy bằng script phục vụ nhanh (Linux)
bash scripts/serve.sh
```

### Các Endpoint chính:
* `POST /predict`: Nhận một yêu cầu duy nhất chứa câu hỏi, premises và options; trả về định dạng Unified Response chuẩn thi.
* `GET /v1/models`: Proxy trả về thông tin mô hình đang được chạy dưới backend vLLM để ban tổ chức kiểm tra quy định `< 8B` tham số.
* `GET /health`: Kiểm tra trạng thái hoạt động của hệ thống.

---

## 9. Chạy Unit Tests

Sử dụng `pytest` để chạy các unit test tự động nhằm kiểm tra tính năng và API:

```bash
# Chạy toàn bộ test suite
pytest tests/ -v

# Chỉ chạy test tính năng API
pytest tests/test_api_refactor.py -v
```

---

## 10. Giấy phép (License)

Dự án này được cấp phép theo Giấy phép MIT - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

*Copyright (c) 2026 Trịnh Vỹ Triết và nhóm phát triển.*
