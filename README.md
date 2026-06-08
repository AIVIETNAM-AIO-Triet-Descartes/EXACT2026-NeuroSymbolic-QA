# 🧠 EXACT2026-NeuroSymbolic-QA

Multimodal Neuro-Symbolic QA System for **EXACT 2026** (IEEE IJCNN 2026).
Kết hợp LLM mã nguồn mở (≤ 8B tham số) với **Z3 Theorem Prover** & **SymPy** để tạo hệ thống hỏi đáp có khả năng giải thích (Explainable QA) cho bài toán logic giáo dục và vật lý.

> **Triết lý:** "Không để LLM tự làm toán — LLM chỉ làm nhiệm vụ giao tiếp và dịch thuật, phần tính toán và suy luận logic giao cho các công cụ toán học chuyên dụng."

---

## 📁 Cấu trúc thư mục dự án

```
EXACT2026-NeuroSymbolic-QA/
│
│── .env.example          # ⚙️ Template biến môi trường — copy thành .env và điền giá trị riêng
│── .env                  # 🔒 Biến môi trường cục bộ (model path, device, port...) — KHÔNG commit lên Git
│── .gitignore            # 🚫 Danh sách file/thư mục bị loại khỏi Git (models/, .env, data/...)
│── CLAUDE.md             # 🤖 Hướng dẫn cho AI agent (Claude Code) khi làm việc với repo này
│── LICENSE               # 📄 Giấy phép MIT — bản quyền Trịnh Vỹ Triết 2026
│── README.md             # 📖 Tài liệu tổng quan dự án (file này)
│── requirements.txt      # 📦 Danh sách thư viện Python cần thiết cho production
│── requirements-dev.txt  # 🧪 Thư viện bổ sung cho development (pytest, black, ruff)
│
├── api/                  # 🌐 [API GATEWAY] — Tầng giao tiếp HTTP, điểm vào duy nhất của hệ thống
│   ├── __init__.py       #     Đánh dấu api/ là Python package
│   ├── main.py           #     🚀 Entry point FastAPI — định nghĩa endpoint POST /query và GET /health
│   │                     #        Nhận request JSON, gọi pipeline xử lý, trả response
│   ├── schemas.py        #     📋 Pydantic models — định nghĩa schema cho QueryRequest & QueryResponse
│   │                     #        Đảm bảo validate input (question, premises) và output (answer, explanation)
│   ├── router.py         #     🔀 Router Agent — phân loại query thành Type 1 (Logic) hoặc Type 2 (Physics)
│   │                     #        Dựa vào: có premises → Type 1, physics keywords → Type 2, default → Type 1
│   └── logger.py         #     📝 Module logging JSON — ghi log mỗi request phục vụ debug và demo live
│                         #        Format JSON: level, name, message (hỗ trợ phân tích lỗi pipeline)
│
├── pipeline/             # ⚡ [CORE PIPELINE] — Toàn bộ logic xử lý Neuro-Symbolic, chia 2 track
│   ├── __init__.py       #     Đánh dấu pipeline/ là Python package
│   │
│   ├── type1/            # 🧩 [TRACK 1: LOGIC] — Xử lý bài toán suy luận logic / giáo dục (FOL + Z3)
│   │   ├── __init__.py   #     Đánh dấu type1/ là Python package
│   │   ├── nl_to_fol.py  #     🔤 Text Parser Agent — chuyển đổi premises ngôn ngữ tự nhiên (NL) sang
│   │   │                 #        First-Order Logic (FOL) bằng LLM ≤ 8B. Bước ③a trong pipeline
│   │   ├── z3_solver.py  #     🔬 Z3 Solver Node — nhận FOL đã validate, dùng Z3 Theorem Prover để
│   │   │                 #        chứng minh/bác bỏ từng answer option. Trả answer + proof_steps. Bước ⑤a
│   │   └── explainer.py  #     💬 Explainer Agent — nhận SolverResult từ Z3, dùng LLM sinh explanation
│   │                     #        bằng ngôn ngữ tự nhiên. Bước ⑦ (shared với Type 2)
│   │
│   └── type2/            # ⚡ [TRACK 2: PHYSICS] — Xử lý bài toán tính toán vật lý (SymPy)
│       ├── __init__.py   #     Đánh dấu type2/ là Python package
│       ├── physics_parser.py  # 🔍 Physics Parser Agent — dùng LLM trích xuất biến số (given),
│       │                      #    đại lượng cần tìm (find), xác định domain và công thức. Bước ③b
│       ├── sympy_solver.py    # 🧮 SymPy Solver Node — giải phương trình, tính toán symbolic chính xác
│       │                      #    tuyệt đối (không bị hallucination số). Trả answer + unit + steps. Bước ⑤b
│       └── cot_builder.py     # 🔗 CoT Builder — xây dựng Chain-of-Thought từ các bước giải SymPy,
│                              #    tạo chuỗi suy luận có cấu trúc cho explanation. Bước ⑥b
│
├── llm/                  # 🤖 [LLM MODULE] — Quản lý load model và inference cho toàn bộ hệ thống
│   ├── __init__.py       #     Đánh dấu llm/ là Python package
│   ├── loader.py         #     📥 Model Loader — load LLM ≤ 8B (Qwen2.5-7B, LLaMA-3.1-8B) vào RAM/VRAM
│   │                     #        Hỗ trợ quantization 4-bit (BitsAndBytes) và adapter QLoRA (PEFT)
│   └── inference.py      #     🧠 Inference Wrapper — gọi LLM generate text, hỗ trợ 2 backend:
│                         #        transformers (local dev) hoặc vLLM (production Linux + GPU)
│
├── configs/              # ⚙️ [CONFIGURATION] — Cấu hình mặc định dùng chung cả team
│   └── config.yaml       #     📋 Config chính — model name, timeout (Z3: 5s, SymPy: 10s),
│                         #        temperature, API host/port, logging level. Commit lên Git
│
├── data/                 # 📊 [DATASET] — Dữ liệu huấn luyện và đánh giá
│   ├── train/            #     🏋️ Dữ liệu training — Type 1 (464 records) + Type 2 (5,520 records)
│   └── eval/             #     📏 Dữ liệu evaluation — dùng để đánh giá hiệu năng pipeline
│
├── models/               # 💾 [MODEL WEIGHTS] — Thư mục lưu trọng số model LLM đã download
│                         #     (vd: models/qwen2.5-7b/) — KHÔNG commit lên Git (file lớn)
│
├── tests/                # ✅ [TESTING] — Bộ test tự động kiểm tra tính đúng đắn của hệ thống
│   ├── test_api.py       #     🌐 Test API endpoints — kiểm tra POST /query và GET /health
│   ├── test_type1.py     #     🧩 Test Track 1 — kiểm tra pipeline Logic (NL→FOL→Z3→Explanation)
│   └── test_type2.py     #     ⚡ Test Track 2 — kiểm tra pipeline Physics (Parser→SymPy→CoT)
│
└── docs/                 # 📚 [DOCUMENTATION] — Tài liệu kỹ thuật và nghiên cứu
    ├── SYSTEM.md         #     🏗️ SSOT — kiến trúc pipeline + bối cảnh cuộc thi (gộp CONTEXT):
    │                     #        state schema, tech stack, fallback, API schema, dev rules, spec thi
    ├── TODO.md           #     ✅ Worklist Track 2 + weakness tracker (gộp)
    ├── track2_reference.md #   📊 Data analysis + formula format + gaps + impl plan (gộp 4 file)
    ├── handoff.md        #     🔄 Session handoff — đọc trước khi nối tiếp việc
    ├── proposals.md      #     💡 PAL code-gen fallback + formula_rag review (gộp)
    └── teammates/        #     👥 Task-handoff cho teammate khác (eval harness)
```

---

## 🔄 Luồng xử lý (Pipeline Flow)

```
HTTP Request → API Gateway (FastAPI) → Router Agent
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
              TRACK 1: Logic                           TRACK 2: Physics
              NL → FOL Parser                          Physics Parser
                    ↓                                         ↓
              Logic Evaluator                          Formula RAG (FAISS)
              (retry ≤ 3 lần)                                 ↓
                    ↓                                   SymPy Solver
               Z3 Solver                                      ↓
                    │                                   CoT Builder
                    └────────────────────┬────────────────────┘
                                         ▼
                                   Explainer Agent
                                         ↓
                                   Response Builder
                                         ↓
                                   HTTP Response JSON
                                { answer, explanation, ... }
```

---

## ⚙️ Tech Stack

| Thành phần | Thư viện | Vai trò |
|------------|----------|---------|
| API Server | FastAPI + Uvicorn | HTTP endpoint, validate input/output |
| Orchestration | LangGraph | State Graph pipeline, conditional edges, retry loop |
| LLM | Transformers / vLLM | Inference LLM ≤ 8B (Qwen2.5, LLaMA 3.1) |
| Logic Solver | Z3-Solver | Theorem prover — chứng minh/bác bỏ FOL |
| Math Solver | SymPy | Tính toán symbolic chính xác tuyệt đối |
| RAG | FAISS + Sentence-Transformers | Truy xuất công thức vật lý từ Vector DB |
| Config | YAML + python-dotenv | Cấu hình dùng chung + cấu hình riêng từng máy |

---

## 🚀 Quick Start

```bash
# 1. Tạo môi trường ảo
python -m venv .venv
.venv\Scripts\activate        # Windows

# 2. Cài đặt dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # cho development

# 3. Cấu hình môi trường
cp .env.example .env          # Chỉnh sửa .env theo máy local

# 4. Download model (lần đầu)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir models/qwen2.5-7b

# 5. Chạy API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Chạy tests
pytest tests/ -v
```

---

## 📜 License

MIT License — Copyright (c) 2026 Trịnh Vỹ Triết
