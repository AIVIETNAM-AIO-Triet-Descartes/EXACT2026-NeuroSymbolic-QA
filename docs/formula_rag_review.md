# Code Review — `pipeline/type2/formula_rag.py`
> Dành cho Claude Code session tiếp theo.  
> Nguồn: phân tích từ Claude Web dựa trên code + dataset context.

---

## 1. Điểm mạnh — Không cần thay đổi

### Hybrid 2 lớp hợp lý
- Layer 1 exact match không cần GPU, nhanh, phù hợp cho các công thức phổ biến
- Layer 2 FAISS chỉ chạy khi Layer 1 fail hoặc có ≥2 candidates — đúng chỗ
- Lazy singleton cho cả FAISS index lẫn formula docs — tránh reload mỗi request, tốt cho production

### `_inject_symbol_aliases` xử lý đúng vấn đề thực tế
Dataset Type 2 dùng notation tiếng Việt (U thay vì V cho voltage, W thay vì E cho energy) — alias injection trước khi solver substitute là cần thiết và đã được implement đúng chỗ.

### Fallback chain rõ ràng
`Layer 1 → Layer 2 FAISS → candidates[0] → None` — không bị crash, luôn có output để pipeline tiếp tục.

---

## 2. Vấn đề cần xem xét

### Vấn đề 1: Layer 1 quá strict khi database mở rộng

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

### Vấn đề 2: Query string cho FAISS quá ngắn và thiếu context

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

### Vấn đề 3: `sympify` validation có thể reject công thức hợp lệ

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

### Vấn đề 4: FAISS index không tự rebuild khi database thay đổi

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

## 3. Câu hỏi cần confirm với Claude Code

Những điểm dưới đây Claude Web không thể verify vì không thấy toàn bộ codebase:

1. **Domain string contract:** `physics_parser.py` → `formula_rag.py` → `physics_formulas.json` — ba nơi này có dùng cùng domain string format không? Nên có một file constants chung (ví dụ `src/constants.py`) định nghĩa domain strings.

2. **`parsed["find"]` format:** Layer 1 check `find in d.get("variables", {})` — `find` là symbol string như `"E"`, `"Z"`, `"B"` hay có thể là string khác? Nếu parser trả về `"energy"` thay vì `"E"` thì Layer 1 luôn miss.

3. **Multi-formula problems:** Một số bài (THCB multi-answer, LD vector) cần nhiều hơn 1 công thức. `parsed_physics["formulas"]` là list nhưng `formula_rag_node` chỉ inject 1 formula — có node nào khác handle multi-formula không?

4. **CHLT routing:** 20 bài Yes/No không cần retrieve formula theo cách thông thường — chỉ cần `f_0 = 1/(2π√LC)` và compare. Có route riêng cho CHLT không hay cũng đi qua `formula_rag_node`?

---

## 4. Priority cải thiện theo timeline còn lại

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

## 5. Không nên làm lúc này

- **Đổi embedding model ngay** — bottleneck hiện tại là database thiếu công thức, không phải embedding quality
- **Thêm BM25 hybrid** — over-engineering với 52 formulas, chỉ cần thiết nếu dataset lớn hơn nhiều
- **Tách `_chat_llamacpp` / `_chat_vllm`** — đã confirmed là over-engineering, backend switch qua config là đủ (xem llm_reasoner.py hiện tại)
