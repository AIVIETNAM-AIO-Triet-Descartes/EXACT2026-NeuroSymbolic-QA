# 🧠 Hướng Dẫn Chạy Track 1 - Logic-Based Educational QA

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường, chuẩn bị dữ liệu/mô hình và chạy thử nghiệm hệ thống Neuro-Symbolic QA cho **Track 1 (Logic-Based Educational Queries)** của cuộc thi EXACT 2026.

---

## 📋 Mục lục
1. [Giới thiệu Track 1](#1-giới-thiệu-track-1)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Cài đặt môi trường](#3-cài-đặt-môi-trường)
4. [Khởi chạy Inference Server (vLLM / llama.cpp)](#4-khởi-chạy-inference-server-vllm--llamacpp)
5. [Chạy Pipeline Offline (Batch Runner)](#5-chạy-pipeline-offline-batch-runner)
6. [Chạy trên Google Colab (Google Drive Cache)](#6-chạy-trên-google-colab-google-drive-cache)
7. [Định dạng dữ liệu đầu ra](#7-định-dạng-dữ-liệu-đầu-ra)
8. [Chiến lược cải tiến (Option A — Logical Correctness + Report)](#8-chiến-lược-cải-tiến-option-a)
9. [Báo cáo lỗi dữ liệu (Dataset Bug Report)](#9-báo-cáo-lỗi-dữ-liệu)

---

## 1. Giới thiệu Track 1

**Track 1** tập trung giải quyết các câu hỏi suy luận logic phức tạp được xây dựng từ tập mệnh đề First-Order Logic (FOL).
Hệ thống sử dụng kiến trúc lai hợp đồng thuận (Consensus Hybridization) gồm 3 tầng xử lý:
1. **Logic Tree (Đồ thị suy luận DAG):** Suy diễn tiến/lùi tự động bằng các luật logic (tốc độ cực nhanh < 1ms).
2. **Z3 Solver (Chứng minh hình thức):** Sử dụng Z3 Theorem Prover để kiểm tra tính thỏa mãn hệ thống logic (độ chính xác tuyệt đối).
3. **LLM Chain-of-Thought (Neural Fallback):** Sử dụng Qwen 2.5 7B Instruct để dịch thuật logic, sinh lời giải thích (Explanation) và suy luận ngữ nghĩa khi các bộ giải ký hiệu thất bại.

### Điểm đánh giá Track 1 (theo BTC)
| Thành phần | Trọng số | Mô tả |
|:---|:---:|:---|
| `answers` | **50%** | Đáp án đúng (MCQ: A/B/C/D, Yes/No: Yes/No/Unknown) |
| `premises_used` | **50%** | Danh sách chỉ mục tiền đề đã sử dụng (1-based index) |
| Speed Bonus | **+10%** | Chỉ tính trên câu ĐÚNG, nếu trả lời nhanh hơn trung bình |
| Dataset Bug Report | **+10%** | Nộp báo cáo lỗi dữ liệu lên `#dataset-issue-report` |

---

## 2. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT (JSON Sample)                       │
│  premises-FOL, premises-NL, questions, answers (GT)         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 1: PREPROCESSING                         │
│  • FOL Normalization (fol_normalizer.py)                    │
│  • Question Classification (MCQ / Yes-No)                   │
│  • Text Normalization & Entity Extraction (preprocessing.py)│
│  • Eligibility-vs-Actuality Detection                       │
│  • Question Criterion Hints (fewest/strongest/correct)      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 2: LOGIC TREE (DAG)                      │
│  • Parse FOL → Facts + Rules                                │
│  • Forward Chaining (derive all conclusions)                │
│  • Backward Chaining (prove specific goals)                 │
│  • Negation Handling (CWA + Contraposition)                 │
│  • Negation Proof (can_prove_negation → "No" answers)       │
│  • Missing Condition Detection (check_missing_conditions)   │
│  • Proof Trace Extraction (premises_used)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│ Stage 3: Z3      │  │ Stage 4: LLM Chain-of-Thought (CoT)  │
│ Theorem Prover   │  │ • Enhanced Prompts (SAFE Verification)│
│ (Fallback for    │  │ • Few-Shot: Fewest, Strongest,        │
│  short premises) │  │   Eligibility≠Actuality, Unknown      │
└────────┬─────────┘  │ • Preprocessing Hints injected        │
         │            │ • 0-based premises extraction          │
         │            └──────────────┬───────────────────────┘
         │                           │
         └─────────┬─────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│           CONSENSUS HYBRIDIZATION (Phase 2)                  │
│  • Logic Tree ∩ CoT agree → high confidence (1.0)           │
│  • Conflict → Trust Logic Tree (override) at confidence 0.9  │
│  • Only CoT available → confidence 0.8                      │
│  • Only Logic Tree → confidence 0.7                         │
│  • All fail → Z3 fallback → Ultimate fallback: "Unknown"    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT (JSON)                             │
│  idx (premises_used), answers, explanation                  │
└─────────────────────────────────────────────────────────────┘
```

### Các module chính

| File | Vai trò |
|:---|:---|
| [`scripts/run_track1.py`](scripts/run_track1.py) | Pipeline chính — orchestrate toàn bộ flow |
| [`pipeline/type1/logic_tree.py`](pipeline/type1/logic_tree.py) | Logic Tree (DAG): Forward/Backward Chaining, Negation, Contraposition |
| [`pipeline/type1/preprocessing.py`](pipeline/type1/preprocessing.py) | **Mới:** Tiền xử lý dữ liệu, entity extraction, eligibility detection |
| [`pipeline/type1/fol_normalizer.py`](pipeline/type1/fol_normalizer.py) | Chuẩn hóa FOL premises |
| [`pipeline/type1/question_classifier.py`](pipeline/type1/question_classifier.py) | Phân loại câu hỏi (MCQ / Yes-No) |
| [`pipeline/type1/z3_solver.py`](pipeline/type1/z3_solver.py) | Z3 Theorem Prover integration |
| [`llm/prompt_templates.py`](llm/prompt_templates.py) | Prompt templates cho CoT reasoning |
| [`llm/llm_reasoner.py`](llm/llm_reasoner.py) | LLM Reasoner: CoT, Z3 code gen, explanation |
| [`configs/config.yaml`](configs/config.yaml) | Cấu hình LLM backend (dev/prod) |

---

## 3. Cài đặt môi trường

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

## 4. Khởi chạy Inference Server (vLLM / llama.cpp)

Hệ thống Neuro-Symbolic QA được thiết kế theo kiến trúc **Client-Server**. Mọi cuộc gọi LLM trong pipeline sẽ gửi request HTTP qua API tương thích OpenAI (không nạp trọng số mô hình trực tiếp trong tiến trình Python).

Bạn cần khởi chạy **Inference Server** trước khi chạy pipeline bằng một trong hai cách:

### Phương án A: Dành cho Production (Sử dụng `vLLM` - Khuyên dùng)
Yêu cầu GPU ≥24GB VRAM (như RunPod). Phương án này sử dụng mô hình gốc (Safetensors) tải từ HuggingFace và hỗ trợ cơ chế PagedAttention tối ưu hiệu năng.

1. Khởi chạy vLLM server:
   ```bash
   vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8001 --dtype float16
   ```
2. Trong file [configs/config.yaml](configs/config.yaml), thiết lập profile hoạt động sang `prod`:
   ```yaml
   llm:
     active: prod
   ```
*(Hoặc bạn có thể chạy script tiện ích `bash scripts/serve.sh` để tự động hóa toàn bộ việc cấu hình và chạy ngầm vLLM + FastAPI bằng `tmux`)*.

### Phương án B: Dành cho Development / Colab (Sử dụng GGUF qua `llama-cpp-python` / `llama-server`)
Phù hợp chạy trên GPU cá nhân (8GB VRAM) hoặc Google Colab (T4 GPU).

*   **Lựa chọn 1: Sử dụng Qwen 2.5 7B Instruct**
    1. Khởi chạy server chạy ngầm ở cổng 8000:
       ```bash
       python3 -m llama_cpp.server --model ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf --port 8000 --n_gpu_layers -1 --n_ctx 4096 --model_alias Qwen/Qwen2.5-7B-Instruct
       ```
    2. Cấu hình [configs/config.yaml](configs/config.yaml):
       ```yaml
       llm:
         active: dev
       ```

*   **Lựa chọn 2: Sử dụng DeepSeek-R1-0528-Qwen3-8B**
    1. Khởi chạy server chạy ngầm ở cổng 8000:
       ```bash
       python3 -m llama_cpp.server --model ./DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf --port 8000 --n_gpu_layers -1 --n_ctx 4096 --model_alias DeepSeek-R1-0528-Qwen3-8B
       ```
    2. Cấu hình [configs/config.yaml](configs/config.yaml):
       ```yaml
       llm:
         active: dev
         profiles:
           dev:
             model_name: "DeepSeek-R1-0528-Qwen3-8B"
       ```

---

## 5. Chạy Pipeline Offline (Batch Runner)

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

## 6. Chạy trên Google Colab (Google Drive Cache)

Nếu chạy trên Google Colab, bạn hãy tận dụng notebook `run_track1_colab.ipynb` được thiết lập tối ưu sẵn các cell để tự động hóa quá trình:

1. **Mount Drive và cài dependencies:** Cài đặt nhanh dependencies và nạp file wheel `llama-cpp-python` có sẵn từ thư mục `Colab_Cache` trên Google Drive.
2. **Sao chép Model:** Di chuyển 2 file mô hình GGUF từ Drive sang bộ nhớ Colab để tăng tốc độ nạp mô hình.
3. **Khởi chạy Server chạy ngầm:**
   * Notebook cung cấp sẵn cell chạy ngầm `nohup python3 -m llama_cpp.server ...` trên cổng `8000` (sử dụng file GGUF local vừa copy).
   * Hoặc cung cấp tùy chọn chạy `vLLM` tự tải mô hình từ HuggingFace qua GPU T4.
4. **Chạy pipeline:** Gọi script chạy kiểm thử hoặc chạy đánh giá toàn bộ dataset.

---

## 7. Định dạng dữ liệu đầu ra

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

---

## 8. Chiến lược cải tiến (Option A)

Hệ thống đã được cải tiến theo **Phương án A (Logically Correct + Report)**: giữ engine suy luận hoàn toàn đúng logic và nộp báo cáo lỗi dữ liệu để nhận **+10% Dataset Correction Bonus**.

### 8.1. Tiền xử lý dữ liệu (Preprocessing)

Module mới [`pipeline/type1/preprocessing.py`](pipeline/type1/preprocessing.py) cung cấp:

| Chức năng | Mô tả |
|:---|:---|
| **Text Normalization** | Chuẩn hóa khoảng trắng, dấu câu, Unicode arrows |
| **Entity Extraction** | Trích xuất tên thực thể từ FOL và NL (e.g., Sophia, Alex, PhD) |
| **Premise Graph Filter** | Lọc premises không liên quan dựa trên entity overlap với câu hỏi |
| **Eligibility-vs-Actuality Detection** | Phát hiện pattern "eligible for X" thiếu "has X" → sinh cảnh báo |
| **Question Criterion Hints** | Nhận diện tiêu chí đặc biệt: "fewest premises", "strongest conclusion" |

### 8.2. Logic Tree nâng cao

Module [`pipeline/type1/logic_tree.py`](pipeline/type1/logic_tree.py) đã được bổ sung:

| Method mới | Mô tả |
|:---|:---|
| `can_prove_negation(goal)` | Kiểm tra xem ¬P(x) có chứng minh được không → trả lời "No" thay vì "Unknown" |
| `check_missing_conditions(goal)` | Tìm antecedent conditions bị thiếu (e.g., "has_trainer") → cảnh báo cho LLM |

### 8.3. Prompt tối ưu (SAFE Verification)

Hai prompt template CoT đã được tối ưu hóa theo kỹ thuật Step-Aware Verification (SAFE):

| Cải tiến | Chi tiết |
|:---|:---|
| **Few-Shot Eligibility ≠ Actuality** | Ví dụ minh họa: "eligible for a coach" ≠ "has a coach" |
| **Few-Shot Strongest Conclusion** | Ví dụ minh họa chọn kết luận cuối cùng trong chuỗi (dùng nhiều premises nhất) |
| **Few-Shot Fewest Premises** | Ví dụ minh họa đếm premises cho từng option và chọn ít nhất |
| **Question Criterion Detection** | Bước 5 trong CoT yêu cầu LLM đọc kỹ tiêu chí câu hỏi trước khi trả lời |
| **Preprocessing Hints Injection** | Cảnh báo ⚠️ từ preprocessing được inject vào symbolic hints |

### 8.4. Quy trình xử lý cải tiến (Pipeline Flow)

```
Input → Preprocessing (entity filter, criterion hints, eligibility warnings)
    → Logic Tree (forward chain + negation proof + missing conditions)
    → LLM CoT (enhanced prompts + symbolic hints + preprocessing hints)
    → Consensus Hybridization (Logic Tree ∩ CoT)
    → Z3 Fallback (if needed)
    → Output
```

Điểm khác biệt chính so với phiên bản trước:
1. **Logic Tree giờ trả được "No"** qua negation proof và missing-condition detection.
2. **LLM CoT nhận thêm hints** từ preprocessing (eligibility warnings, question criterion).
3. **Prompt tối ưu** với 4 few-shot examples bao phủ các error mode chính.
4. **Không emulate lỗi dataset** — giữ logic đúng, nộp báo cáo.

### 8.5. Phase 2 — Nâng cấp hiệu suất

Sau khi đánh giá trên 50 mẫu đầu (73/93 accuracy ≈ 78.5%), chúng tôi phát hiện 3 lỗi hệ thống:

| Lỗi | Nguyên nhân | Sửa chữa |
|:---|:---|:---|
| **Conflict Override sai** | Pipeline tin tưởng LLM CoT khi xung đột với Logic Tree, nhưng Logic Tree đúng 100% | Đảo ngược: **Logic Tree luôn được ưu tiên** khi có đáp án Yes/No |
| **Question Classifier bypass** | Câu hỏi dạng "According to..." bị phân loại OPEN, bỏ qua Logic Tree | **Tất cả câu hỏi non-MCQ** giờ được phân loại YES_NO |
| **Disjunctive path bug** | `check_missing_conditions` báo thiếu điều kiện kể cả khi đã có 1 path thỏa mãn | Chỉ báo thiếu khi **tất cả** đường dẫn đều bị chặn |
| **Backward chain NOT_ bug** | `backward_chain("NOT_X")` match nhầm rule dương `Y → X` | Chỉ match rule có `consequent == goal_predicate` |

**Prompt Engineering (Phase 2):**
- Thêm quy tắc **No Extrapolations**: Không chọn option chứa tuyên bố vượt quá premises.
- Thêm quy tắc **Affirming the Consequent**: Không suy ngược (nếu P→Q và Q đúng, không suy ra P).
- Thêm hướng dẫn **Disjunctive Path Check**: Nếu có nhiều rule dẫn đến cùng goal, chỉ cần 1 path thỏa mãn.
- Thêm quy tắc **Universal Chain**: ∀x(P(x)→Q(x)) + ∀x P(x) = ∀x Q(x) áp dụng cho tất cả cá thể.

---

## 9. Báo cáo lỗi dữ liệu

### Tóm tắt phát hiện

Trong quá trình đánh giá, chúng tôi phát hiện **≥12 lỗi gán nhãn nghiêm trọng** trong tập validation `Logic_Based_Educational_Queries.json`. Các lỗi này có đặc điểm chung: trường `explanation` (do BTC viết) phân tích logic đúng, nhưng trường `answers` lại ghi ngược giá trị.

### Ví dụ điển hình

| Sample | Câu hỏi | Nhãn sai | Nhãn đúng | Bằng chứng từ `explanation` |
|:---:|:---|:---:|:---:|:---|
| 7-Q1 | "Does Dr. John's PhD make him eligible as research mentor?" | `No` | `Yes` | *"...so his PhD qualification entails mentorship eligibility."* |
| 20-Q1 | "Student with 3 courses > 8.5 will graduate?" | `Yes` | `No` | *"...high scores don't guarantee graduation, and the answer is No."* |
| 21-Q1 | "High-quality essay guarantees fellowship?" | `Yes` | `No` | *"...a high-quality essay does not ensure a fellowship."* |
| 1-Q0 | "Which is the strongest conclusion?" | `C` | `A` | *"...making A the strongest conclusion. C is true but weaker."* |

### Tài liệu chi tiết

Xem file đầy đủ: [`docs/dataset_bugs_report.md`](docs/dataset_bugs_report.md)

### Cách nộp

1. Đăng nhập Discord server EXACT 2026.
2. Vào kênh `#dataset-issue-report`.
3. Đăng bài kèm nội dung từ file `docs/dataset_bugs_report.md`.
4. Ghi rõ **Team Name** và **Track 1**.
