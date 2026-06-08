# Track 2 — Proposals & Code Review

**Mục lục (gộp từ 2 file):**
- Kế hoạch Cải tiến LLM Fallback (Program-Aided Language Model)  *(← `pal_fallback_strategy.md`)*
- Code Review — `pipeline/type2/formula_rag.py`  *(← `formula_rag_review.md`)*

---

## Kế hoạch Cải tiến LLM Fallback (Program-Aided Language Model)

Tài liệu này phác thảo chiến lược nâng cấp nhánh fallback trong pipeline giải toán vật lý (Track 2), đặc biệt nhắm tới việc tận dụng tối đa năng lực của các model LLM cỡ nhỏ (ví dụ: Qwen-2.5-7B/8B).

### 1. Vấn đề hiện tại của LLM Fallback (Direct CoT)

Khi các thuật toán giải logic (như SymPy Solver) thất bại, hệ thống thường gọi LLM để giải bài toán trực tiếp qua phương pháp **Chain-of-Thought (CoT)**. 
Tuy nhiên, với các mô hình 8B:
- **Điểm mạnh:** Khả năng đọc hiểu bài toán, lập luận logic chọn đúng công thức và thế số cực kỳ tốt.
- **Điểm yếu (Arithmetic Hallucination):** Khả năng thực hiện các phép tính dấu phẩy động (floating point), phép chia phức tạp, hoặc làm việc với ký pháp khoa học (scientific notation như $10^{-6}$) rất kém. Thường xuyên dẫn đến đáp án tính toán sai lệch dù công thức đúng.

### 2. Giải pháp: PAL (Program-Aided Language Models)

Để giải quyết vấn đề trên, chúng ta chuyển đổi vai trò của LLM từ "người tính toán" sang "người viết code".

Thay vì yêu cầu LLM đưa ra kết quả cuối cùng, chúng ta yêu cầu LLM viết một đoạn mã **Python (dùng thư viện SymPy)** dựa trên công thức và các biến số đã lấy được (từ RAG và Regex/Parser). Hệ thống sau đó sẽ tự động thực thi đoạn code này trong một môi trường an toàn (Sandbox).

#### Ưu điểm:
- **Zero Arithmetic Hallucination:** Máy tính (Python) thực hiện tính toán, loại bỏ hoàn toàn sai số toán học của LLM.
- **Tận dụng thế mạnh của 8B:** Các model 8B sinh code Python logic cực kỳ chính xác.

### 3. Data Flow (Mô phỏng luồng xử lý)

Giả sử hệ thống gặp câu hỏi: *"Một tụ điện có điện dung C = 5uF, điện tích Q = 20uC. Tính năng lượng điện trường của tụ."*

1. **Input gom được trước khi gọi Fallback:**
   - **Question:** "Một tụ điện..."
   - **Formulas (từ RAG):** `["E = Q**2 / (2 * C)"]`
   - **Given:** `{"C": 5e-6, "Q": 20e-6}`
   - **Find:** `"E"`

2. **LLM Code Generation:**
   Hệ thống prompt LLM với các input trên và yêu cầu trả về code Python.
   ```python
   # Output từ LLM
   import sympy as sp

   def solve():
       C, Q, E = sp.symbols('C Q E')
       eq = sp.Eq(E, Q**2 / (2 * C))
       eq_sub = eq.subs({C: 5e-6, Q: 20e-6})
       ans = sp.solve(eq_sub, E)
       return float(ans[0])
   ```

3. **Code Execution (Sandbox):**
   - Hệ thống (Python backend) nhận chuỗi code trên.
   - Chạy hàm `solve()` thông qua `exec()` hoặc `subprocess` với cơ chế timeout an toàn (ví dụ: tối đa 5s).
   - Lấy kết quả đầu ra.

4. **Output:** 
   - Đáp án: `4.0e-05`
   - Ghi nhận `source = "llm_code_gen"` thay vì `llm_fallback`.

### 4. Các hạng mục cần cài đặt (Task Definition)

Để Agent thực thi code áp dụng chiến lược này, cần cài đặt các hàm sau:

- [ ] **`llm/llm_reasoner.py`**: Thêm hàm `generate_sympy_code(question, given, find, formulas)`. Hàm này sẽ gọi LLM với một Prompt Template chuyên biệt yêu cầu chỉ sinh ra code Python.
- [ ] **`pipeline/type2/sympy_solver.py`**: Thêm module **Sandbox Execution**. Cần viết một hàm chạy code an toàn (VD: `execute_generated_code`) bắt buộc phải có chặn Timeout để tránh Infinite Loop.
- [ ] **Wiring**: Tại nhánh fallback khi SymPy chay thất bại, hệ thống sẽ ưu tiên gọi `generate_sympy_code()` + `execute_generated_code()` trước. Nếu cách này cũng thất bại (lỗi syntax, timeout), thì mới rớt xuống đáy cùng là `solve_physics_cot()`.

## Giải quyết Weakness #5: MULTI_STEP Fuzzy Symbol Match

Dựa trên sự đồng thuận, tôi sẽ thực hiện giải pháp "Phòng thủ nhiều lớp" (Defense in Depth) bằng cách kết hợp cả 2 phương pháp: chuẩn hóa ký hiệu từ đầu bằng LLM Parser và dùng LLM làm thông dịch viên lúc kẹt trong Solver.

### Đề xuất Thay đổi

#### 1. Nâng cấp LLM Parser Prompt (Cách 1)
**Tập tin bị ảnh hưởng:** `llm/prompt_templates.py`

*   **Mục tiêu:** Bổ sung các rule ép model luôn xuất ra ký hiệu chuẩn cho một số biến hay bị nhầm lẫn (ví dụ: `Z_L` -> `X_L`, `Z_C` -> `X_C`). 
*   **Chi tiết:** Trong `PHYSICS_PARSE_PROMPT`, tôi sẽ nhấn mạnh yêu cầu: "Luôn dùng ký hiệu quốc tế `X_L` cho cảm kháng (không dùng `Z_L`), `X_C` cho dung kháng (không dùng `Z_C`), `R_total` cho điện trở tương đương". Việc này sẽ giúp LLM trả về JSON có biến `find` chuẩn ngay từ đầu.

#### 2. Thêm Fuzzy Match bằng LLM vào Solver (Cách 2)
**Tập tin bị ảnh hưởng:** `pipeline/type2/sympy_solver.py`

*   **Mục tiêu:** Xử lý các case mà Regex Pre-pass (hoặc LLM ảo giác) vẫn đưa vào hệ thống các biến có tên lệch chuẩn, khiến nhánh `_solve_multi_step` chạy vòng lặp mà không match được `find`.
*   **Chi tiết:**
    *   Bên trong hàm `_solve_multi_step`, nếu sau khi lặp hết công thức mà biến `find` vẫn không có trong `accumulated` (tức là không tìm thấy đáp án khớp y xì), hệ thống sẽ kiểm tra xem `llm_server_available()` hay không.
    *   Nếu có LLM, tạo ngay một phiên chat nhanh (nằm trong `_run_with_timeout` để tránh treo) với nội dung:
        > *"Người dùng cần tìm biến '{find}'. Danh sách các biến đã tính được là: {available_vars}. '{find}' có đồng nghĩa/là bí danh của biến nào trong danh sách trên không? Trả về JSON: {{"mapped": "tên_biến"}} hoặc {{"mapped": null}}."*
    *   Nếu LLM tìm ra được biến đồng nghĩa (ví dụ `mapped: "X_L"` khi người dùng hỏi `Z_L`), hệ thống sẽ lập tức lấy kết quả của `X_L` trả về.

### Kế hoạch Kiểm chứng (Verification Plan)
*   **Manual Verification:** Thử đưa vào hệ thống một bài toán có dùng `Z_L` (cảm kháng), ép Regex nhận diện nó là `Z_L = 50`. Khi đó, LLM ở bước solve sẽ tự động map `Z_L` thành `X_L` và tính ra kết quả.
*   **Automated Tests:** Chạy `scripts/_v.py` hoặc test suite để đảm bảo sự thay đổi không làm crash các bài `MULTI_STEP` hiện tại.

### Phê duyệt
Nếu bạn đồng ý với kế hoạch "đánh gọng kìm" bằng LLM này, hãy cho tôi biết để tôi bắt đầu viết code!

---

## Code Review — `pipeline/type2/formula_rag.py`
> Dành cho Claude Code session tiếp theo.  
> Nguồn: phân tích từ Claude Web dựa trên code + dataset context.

---

### 1. Điểm mạnh — Không cần thay đổi

#### Hybrid 2 lớp hợp lý
- Layer 1 exact match không cần GPU, nhanh, phù hợp cho các công thức phổ biến
- Layer 2 FAISS chỉ chạy khi Layer 1 fail hoặc có ≥2 candidates — đúng chỗ
- Lazy singleton cho cả FAISS index lẫn formula docs — tránh reload mỗi request, tốt cho production

#### `_inject_symbol_aliases` xử lý đúng vấn đề thực tế
Dataset Type 2 dùng notation tiếng Việt (U thay vì V cho voltage, W thay vì E cho energy) — alias injection trước khi solver substitute là cần thiết và đã được implement đúng chỗ.

#### Fallback chain rõ ràng
`Layer 1 → Layer 2 FAISS → candidates[0] → None` — không bị crash, luôn có output để pipeline tiếp tục.

---

### 2. Vấn đề cần xem xét

#### Vấn đề 1: Layer 1 quá strict khi database mở rộng

**Code hiện tại:**
```python
candidates = [
    d for d in docs
    if d.get("domain") == domain
    and find and find in d.get("variables", {})
]
```

**Vấn đề:** Phải match CẢ HAI điều kiện — `domain` chính xác VÀ `find` có trong `variables`. Với 4 domain mới sắp được thêm (`ac_circuits`, `electromagnetic_induction`, `lc_oscillation`, `measurement_errors`), Layer 1 sẽ luôn trả về 0 candidates nếu `physics_parser.py` parse domain string không khớp chính xác với string trong database.

**Hệ quả:** Toàn bộ 32 công thức mới sẽ phải đi qua FAISS — Layer 1 không có tác dụng cho đến khi parser và database đồng bộ domain string.

**Câu hỏi cần kiểm tra với Claude Code:**
- `physics_parser.py` trả về domain string dưới dạng gì? (`"ac_circuits"` hay `"AC circuits"` hay `"circuits_ac"`?)
- Có validation nào đảm bảo domain string khớp giữa parser output và database không?

---

#### Vấn đề 2: Query string cho FAISS quá ngắn và thiếu context

**Code hiện tại:**
```python
query = f"{domain} {find} {question}".strip()
# Ví dụ thực tế: "ac_circuits Z An RLC series circuit..."
```

**Vấn đề:** `all-MiniLM-L6-v2` là general purpose model — không được train trên scientific/physics text. Các ký hiệu vật lý đặc thù (`μF`, `ω`, `XL`, `XC`, `cosφ`, `ΔR/R`) tokenizer xử lý kém, embedding không phân biệt được sự khác nhau giữa các công thức có cùng domain.

**Ví dụ cụ thể:** Query `"ac_circuits X_C"` và `"ac_circuits X_L"` sẽ cho embedding rất gần nhau → FAISS có thể trả về sai công thức (capacitive reactance vs inductive reactance).

**Cải thiện đề xuất — không cần đổi model:**
```python
# Thêm keywords từ formula document vào query
# Mỗi formula doc đã có field "keywords" trong schema
formula_keywords = " ".join(doc.get("keywords", [])[:5] for doc in search_pool[:3])
query = f"{domain} {find} {question} {formula_keywords}".strip()
```

Cách này tận dụng keywords đã có trong database mà không cần rebuild index hay đổi model.

---

#### Vấn đề 3: `sympify` validation có thể reject công thức hợp lệ

**Code hiện tại:**
```python
sympify(doc["formula_sympy"].split("=")[-1].strip())
```

**Logic:** Split theo `=`, lấy phần bên phải, thử parse bằng SymPy. Nếu fail → bỏ entry.

**Công thức có thể bị reject:**

| Công thức | Lý do có thể fail |
|-----------|------------------|
| `delta_rel = (delta_x / x) * 100` | `delta_rel`, `delta_x` có thể bị sympify hiểu sai |
| `EMF = -L * (dI / dt)` | `dI`, `dt` là ký hiệu đạo hàm, không phải symbol SymPy |
| `f_0 = 1 / (2 * pi * sqrt(L * C))` | `pi` cần import, `sqrt` cần import — có thể pass hoặc fail tùy context |
| `B = mu_0 * n * I` | `mu_0` nếu không được khai báo trước → sympify trả về symbol, không fail |

**Công thức dạng điều kiện (CHLT):**
```python
# F-029: không phải phương trình giải được
"formula_sympy": "abs(f - f_0) < tolerance"
```
Dạng này sympify parse được nhưng không có `=` → `split("=")[-1]` trả về toàn bộ string → có thể pass hoặc không tùy nội dung.

**Kiến nghị:** Sau khi đồng đội thêm 32 công thức mới, chạy `load_formula_db()` và log ra danh sách những entry bị reject để verify không có công thức hợp lệ nào bị bỏ qua.

---

#### Vấn đề 4: FAISS index không tự rebuild khi database thay đổi

**Hiện trạng:** Index được build offline bởi `scripts/build_faiss_index.py`, kết quả lưu tại `data/formula_index/{index.faiss, metadata.pkl}`.

**Rủi ro:** Nếu đồng đội thêm 32 công thức vào `physics_formulas.json` nhưng quên rebuild index → `_faiss_docs` trong memory và `_faiss_index` sẽ không có các công thức mới → Layer 2 không tìm được công thức mới dù Layer 1 cũng fail.

**Kiến nghị:** Thêm version check hoặc ít nhất là log warning khi số lượng docs trong JSON khác số lượng entries trong FAISS index:

```python
def _load_faiss_index(...):
    ...
    if len(docs) != index.ntotal:
        logger.warning(
            f"[FORMULA_RAG] MISMATCH: JSON has {len(docs)} formulas "
            f"but FAISS index has {index.ntotal} entries. "
            f"Run scripts/build_faiss_index.py to rebuild."
        )
```

---

### 3. Câu hỏi cần confirm với Claude Code

Những điểm dưới đây Claude Web không thể verify vì không thấy toàn bộ codebase:

1. **Domain string contract:** `physics_parser.py` → `formula_rag.py` → `physics_formulas.json` — ba nơi này có dùng cùng domain string format không? Nên có một file constants chung (ví dụ `src/constants.py`) định nghĩa domain strings.

2. **`parsed["find"]` format:** Layer 1 check `find in d.get("variables", {})` — `find` là symbol string như `"E"`, `"Z"`, `"B"` hay có thể là string khác? Nếu parser trả về `"energy"` thay vì `"E"` thì Layer 1 luôn miss.

3. **Multi-formula problems:** Một số bài (THCB multi-answer, LD vector) cần nhiều hơn 1 công thức. `parsed_physics["formulas"]` là list nhưng `formula_rag_node` chỉ inject 1 formula — có node nào khác handle multi-formula không?

4. **CHLT routing:** 20 bài Yes/No không cần retrieve formula theo cách thông thường — chỉ cần `f_0 = 1/(2π√LC)` và compare. Có route riêng cho CHLT không hay cũng đi qua `formula_rag_node`?

---

### 4. Priority cải thiện theo timeline còn lại

```
Ngay bây giờ (quan trọng nhất):
  ☑ Verify domain string contract giữa parser và database ✅ done 2026-06-02 (canonical 5 domain; parser+prompt emit snake_case khớp; DB string đợi Member2 nhập formula)
  □ Sau khi thêm 32 công thức → rebuild FAISS index → chạy load_formula_db() check rejects

Sau khi pipeline chạy đúng cơ bản:
  □ Cải thiện query string (thêm keywords từ formula doc)
  □ Thêm FAISS/JSON mismatch warning

Cuối cùng nếu RAG accuracy vẫn kém:
  □ Đổi embedding model: all-MiniLM-L6-v2 → all-mpnet-base-v2
  □ Rebuild FAISS index với model mới
  □ Cân nhắc BM25 hybrid nếu exact keyword match quan trọng hơn semantic
```

---

### 5. Không nên làm lúc này

- **Đổi embedding model ngay** — bottleneck hiện tại là database thiếu công thức, không phải embedding quality
- **Thêm BM25 hybrid** — over-engineering với 52 formulas, chỉ cần thiết nếu dataset lớn hơn nhiều
- **Tách `_chat_llamacpp` / `_chat_vllm`** — đã confirmed là over-engineering, backend switch qua config là đủ (xem llm_reasoner.py hiện tại)
