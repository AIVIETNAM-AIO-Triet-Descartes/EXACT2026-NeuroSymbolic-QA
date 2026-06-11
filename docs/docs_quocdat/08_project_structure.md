# 📂 Project Structure & Setup Guide

> **Dự án:** EXACT2026-NeuroSymbolic-QA

## 1. Cấu trúc thư mục đề xuất

```text
EXACT2026-NeuroSymbolic-QA/
│
├── data/                               # Chứa dữ liệu
│   ├── Logic_Based_Educational_Queries.json # Input dataset
│   └── output_predictions.json         # Output format của hệ thống
│
├── docs/                               # Documents thiết kế pipeline
│   ├── 00_pipeline_overview.md
│   ├── 01_data_analysis.md
│   ├── ...
│
├── src/                                # Source code chính
│   ├── __init__.py
│   ├── main.py                         # Entry point (chạy loop qua dataset)
│   │
│   ├── preprocessor/                   # Stage 1
│   │   ├── __init__.py
│   │   ├── fol_normalizer.py           # Class FOLNormalizer
│   │   └── question_classifier.py      # Phân loại MCQ / YesNo
│   │
│   ├── reasoning/                      # Stage 2 & 3
│   │   ├── __init__.py
│   │   ├── logic_tree.py               # Xây dựng DAG, Forward/Backward chaining
│   │   └── z3_solver.py                # Z3Context, Z3Translator, check_entailment
│   │
│   └── llm/                            # Stage 4
│       ├── __init__.py
│       ├── llm_reasoner.py             # Llama-cpp wrapper cho Qwen 2.5
│       └── prompt_templates.py         # Các constants chứa Prompts
│
├── tests/                              # Unit tests
│   ├── test_normalizer.py
│   ├── test_z3_solver.py
│   └── test_logic_tree.py
│
├── requirements.txt                    # Python dependencies
├── test.py                             # Script test LLM đã có
└── README.md
```

## 2. Requirements & Setup

Tạo file `requirements.txt`:

```text
z3-solver>=4.12.2
sympy>=1.12
llama-cpp-python>=0.2.56
tqdm>=4.66.1
lark>=1.1.9      # Dùng cho parsing FOL nếu cần
pydantic>=2.5.3  # Dùng để define schema
```

Cài đặt môi trường:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Lộ Trình Triển Khai (Roadmap)

1. **Tuần 1: Nền Tảng (Core Foundations)**
   - Cài đặt `fol_normalizer.py` (chuyển đổi Unicode, chuẩn hóa format).
   - Cài đặt `z3_solver.py` cơ bản (map FOL sang Z3, check entailment).
   - Test trên 50 samples đầu tiên.

2. **Tuần 2: Xử Lý Logic Cây & Trích Xuất Index (Logic Tree)**
   - Implement `logic_tree.py`.
   - Implement thuật toán Unsatisfiable Core (Z3) để lấy được mảng `idx`.
   - Nâng cấp `z3_solver.py` xử lý Arithmetic Constraints.

3. **Tuần 3: LLM Integration & Tối Ưu Giải Thích**
   - Viết `llm_reasoner.py` dùng `llama-cpp-python` (sử dụng Qwen 2.5 7B GGUF hiện có).
   - Tinh chỉnh các prompt để LLM sinh ra Explanation thỏa mãn P2.
   - Thêm cơ chế LLM Fallback khi Z3 timeout.

4. **Tuần 4: Tích Hợp Toàn Bộ & Tối Ưu Tốc Độ (Integration & Speed)**
   - Hoàn thiện `main.py`.
   - Đảm bảo thời gian xử lý trung bình < 60s / sample.
   - Kiểm tra định dạng đầu ra khớp yêu cầu (JSON `idx`, `answers`, `explanation`).
