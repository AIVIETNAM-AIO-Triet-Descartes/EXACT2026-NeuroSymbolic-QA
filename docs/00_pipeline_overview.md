# 🧠 EXACT 2026 - Logic-Based QA Pipeline Overview (Part 1)

> **Cuộc thi:** EXACT 2026 - 2nd International XAI Challenge for Transparent Educational Question-Answering  
> **Phần:** Part 1 - Logic-Based Educational Queries  
> **Mục tiêu:** Xây dựng hệ thống Neuro-Symbolic QA kết hợp LLM (≤8B) với Z3 Solver

---

## 1. Phân Tích Bài Toán

### 1.1 Tổng Quan Dataset

| Thuộc tính | Giá trị |
|:---|:---|
| Tổng số mẫu | **411 samples** |
| Tổng số câu hỏi | **~808 questions** |
| Số câu hỏi/mẫu | 2 (397 mẫu), 1 (14 mẫu) |
| Số premises/mẫu | min=3, max=36, avg=10.9 |

### 1.2 Phân Loại Câu Hỏi

| Loại | Số lượng | Mô tả |
|:---|:---|:---|
| **MCQ (A/B/C/D)** | 346 | Câu hỏi trắc nghiệm 4 đáp án |
| **Yes/No** | 416 | Câu hỏi đúng/sai dựa trên premises |
| **Unknown** | 43 | Không đủ thông tin để kết luận |
| **Open-ended** | 3 | Câu hỏi mở |

### 1.3 Phân Phối Đáp Án

```
Q1 (thường MCQ): A=89, B=36, C=20, D=18, Yes=34, No=31, Unknown=183
Q2 (thường Y/N):  Yes=82, No=269, A=16, B=3, D=1, Unknown=26
```

### 1.4 Cấu Trúc FOL

| Toán tử | Tần suất | Ý nghĩa |
|:---|:---|:---|
| `→` | 3152 | Phép kéo theo (Implication) |
| `∀` / `ForAll` | 2053 / 1629 | Lượng tử phổ dụng |
| `¬` | 1198 | Phủ định (Negation) |
| `∧` | 476 | Phép hội (Conjunction) |
| `∃` | 384 | Lượng tử tồn tại |
| `∨` | 46 | Phép tuyển (Disjunction) |
| `≥` / `≤` | 52 / 11 | So sánh số học |
| `↔` | 10 | Tương đương (Biconditional) |

> **QUAN TRỌNG:** Dataset sử dụng **2 hệ notation khác nhau** cho FOL:
> - Unicode: `∀x (P(x) → Q(x))`
> - Text: `ForAll(x, P(x) → Q(x))`
> → Cần **bộ normalizer** thống nhất trước khi xử lý.

---

## 2. Kiến Trúc Hệ Thống (System Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                      📥 INPUT LAYER                             │
│  JSON: premises-NL, premises-FOL, questions                    │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  🔧 STAGE 1: PREPROCESSING                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Question     │  │  FOL         │  │  Premise     │          │
│  │  Classifier   │  │  Normalizer  │  │  Selector    │          │
│  │  MCQ/YN/UNK   │  │  Unicode→Z3  │  │  Relevance   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              🌳 STAGE 2: LOGIC TREE CONSTRUCTION                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Tree Builder │  │ Path Finder  │  │ Contradiction│          │
│  │  DAG from     │  │ Forward/     │  │  Detector    │          │
│  │  premises     │  │ Backward     │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               ⚡ STAGE 3: SYMBOLIC SOLVER                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  FOL → Z3    │  │  Z3 Solver   │  │  Fallback:   │          │
│  │  Translator  │  │  SAT/UNSAT   │  │  SymPy       │          │
│  │  LLM-assisted│  │  Check       │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              🤖 STAGE 4: LLM REASONING                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Chain-of-   │  │  Explanation  │  │  Self-       │          │
│  │  Thought     │  │  Generator   │  │  Refinement  │          │
│  │  Prompting   │  │  NL Output   │  │  Z3 Feedback │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      📤 OUTPUT LAYER                            │
│  answer | explanation | fol | cot | premises | confidence       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Nghiên Cứu Nền Tảng (State-of-the-Art)

### 3.1 Các Framework Nổi Bật

| Framework | Tác giả | Ý tưởng chính | Áp dụng |
|:---|:---|:---|:---|
| **Logic-LM** | Pan et al., 2023 | LLM → Symbolic Program → Z3 + Self-Refinement | ✅ Core pipeline |
| **LINC** | Olausson et al., 2023 | NL → FOL → External Theorem Prover | ✅ FOL translation |
| **ProRef** | 2024 | Prototype-then-Refine symbolic programs | ✅ Self-correction |
| **SAFE** | Liu et al., ACL 2025 | Step-aware formal verification | ✅ Step verification |
| **Tree-of-Thought** | Yao et al., 2023 | Tree search cho reasoning | ✅ Logic Tree |
| **MATH-VF** | Zhou & Zhang, 2025 | Formalizer + Critic + external tools | ✅ Feedback loop |
| **PRoSFI** | 2026 | Formal prover validates intermediate steps | ✅ Reward shaping |

### 3.2 Pipeline Lấy Cảm Hứng Từ Logic-LM + LINC

```
NL Premises ──→ LLM Semantic Parser ──→ FOL Formalization ──→ Z3 Solver
                                                               │
                                                        ┌──────┴──────┐
                                                        │             │
                                                   ✅ SAT/UNSAT  ❌ Error
                                                        │             │
                                                   Answer + Proof  Self-Refinement
                                                        │             │
                                                NL Explanation    ──→ Back to LLM
```

> **Điểm khác biệt của pipeline này so với Logic-LM gốc:**
> 1. Dataset đã cung cấp sẵn `premises-FOL` → giảm lỗi NL→FOL translation
> 2. Thêm **Logic Tree** để tìm inference path tối ưu
> 3. Sử dụng `idx` field để validate premise selection
> 4. Hỗ trợ cả 3 loại câu hỏi: MCQ, Yes/No, Unknown

---

## 4. Cây Luận Lý (Logic Tree) - Thiết Kế Tổng Quan

### 4.1 Định Nghĩa

**Logic Tree** là một **Directed Acyclic Graph (DAG)** trong đó:
- **Nodes** = các mệnh đề (propositions/predicates)
- **Edges** = quan hệ suy luận (implication/derivation)
- **Root** = goal/conclusion cần chứng minh
- **Leaves** = premises (facts) đã cho

### 4.2 Thuật Toán Xây Dựng Logic Tree

```
Algorithm: BUILD_LOGIC_TREE(premises, goal)
Input:  Set of premises P = {p1, ..., pn}, goal proposition G
Output: Logic Tree T as DAG

1. PARSE all premises into (antecedent, consequent) pairs
2. BUILD adjacency list: for each rule A → B, add edge A → B
3. IDENTIFY leaf nodes (atomic facts without antecedents)
4. FORWARD CHAINING:
   a. Start from leaf nodes (known facts)
   b. For each rule where ALL antecedents are satisfied:
      - Mark consequent as derived
      - Add to derived facts
   c. Repeat until no new facts derived or goal reached
5. BACKWARD CHAINING (if forward fails):
   a. Start from goal G
   b. Find rules where G is consequent
   c. Recursively try to prove each antecedent
6. RETURN tree with derivation path
```

→ Chi tiết tại [03_logic_tree.md](./03_logic_tree.md)

---

## 5. Tiêu Chí Đánh Giá (Scoring Criteria)

| Tiêu chí | Trọng số | Mô tả |
|:---|:---|:---|
| **P1 - Correctness** | Cao nhất | Đáp án chính xác (MCQ/Yes/No/Unknown) |
| **P2 - Explanation Quality** | Trung bình | Giải thích rõ ràng, logic, đúng ngữ pháp |
| **P3 - Reasoning Depth** | Bổ sung | Số bước suy luận, sử dụng FOL, chuỗi CoT |

> **Ràng buộc kỹ thuật:**
> - LLM ≤ 8B parameters (open-source)
> - Response time < 60 giây
> - Không dùng API đóng (GPT-4, Claude, Gemini)
> - Phải cung cấp explanation cho mỗi câu trả lời

---

## 6. Công Cụ & Stack Kỹ Thuật

| Thành phần | Công cụ | Mục đích |
|:---|:---|:---|
| **LLM** | Qwen 2.5 7B Instruct (GGUF) | Reasoning + NL generation |
| **LLM Runtime** | llama-cpp-python | GPU inference (RTX 3050) |
| **Symbolic Solver** | Z3-solver (Python) | Formal verification |
| **Math Engine** | SymPy | Arithmetic constraints |
| **API Framework** | FastAPI | Endpoint serving |
| **FOL Parser** | Custom (lark/pyparsing) | Parse FOL notation |

---

## 7. Tham Chiếu Tới Các File Skill Khác

| File | Nội dung |
|:---|:---|
| [01_data_analysis.md](./01_data_analysis.md) | Phân tích chi tiết dataset |
| [02_fol_normalizer.md](./02_fol_normalizer.md) | Thiết kế bộ chuẩn hóa FOL |
| [03_logic_tree.md](./03_logic_tree.md) | Chi tiết xây dựng Logic Tree |
| [04_z3_solver.md](./04_z3_solver.md) | Tích hợp Z3 Solver |
| [05_llm_reasoning.md](./05_llm_reasoning.md) | Prompt Engineering & LLM |
| [06_pipeline_implementation.md](./06_pipeline_implementation.md) | Hướng dẫn triển khai code |
| [07_evaluation_strategy.md](./07_evaluation_strategy.md) | Chiến lược tối ưu điểm |
| [08_project_structure.md](./08_project_structure.md) | Cấu trúc thư mục dự án |
