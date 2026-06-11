# Kế hoạch Tích hợp `premises_used` cho Track 1 (Z3 Solver)

Tài liệu này ghi chú lại thiết kế hệ thống thống nhất để kết nối đầu ra của Track 1 (Logic) với API Response Builder mà không làm ảnh hưởng (backward compatibility) đến Track 2 (Vật lý) đang chạy ổn định.

## 1. Bối cảnh & Vấn đề
- Theo chuẩn API của Ban Tổ Chức (xem `CLAUDE.md`), kết quả trả về của Track 1 **bắt buộc phải có trường `premises_used`** (kiểu `list[int]`), chứa index (0-based) của các dữ kiện đã được sử dụng để chứng minh ra đáp án. (Ví dụ: `[0, 2]`).
- Hiện tại, interface trung gian `SolverResult` trong file `pipeline/state.py` chưa định nghĩa trường này. Do đó, nếu team Track 1 hoàn thiện xong code của `z3_solver.py`, họ sẽ không có chỗ để gán danh sách `premises_used` truyền dọc xuống pipeline cho `api/main.py`.

## 2. Giải pháp cốt lõi
Bổ sung một trường mang tính tùy chọn vào `SolverResult`:
**`premises_used: Optional[list[int]]`**

**Lợi ích của giải pháp này:**
1. **Đáp ứng nhu cầu của Track 1:** Z3 Solver có "đường ống" chuẩn để gắn Unsat Core indices.
2. **Bảo vệ toàn vẹn cho Track 2:** Vì khai báo là `Optional`, luồng SymPy hiện tại (vốn không trả về khóa `premises_used`) sẽ không bị lỗi. Khi gọi phương thức `.get("premises_used")`, Python sẽ trả về `None`. Hàm `build_response` đã được thiết kế để tự động bọc `None` thành mảng rỗng `[]` (chuẩn luật vật lý của BTC).

---

## 3. Các thay đổi cần thực hiện (Action Items)

### 3.1. Sửa file `pipeline/state.py`
Mở `pipeline/state.py` và tìm class `SolverResult(TypedDict)`. Bổ sung trường mới vào cuối định nghĩa:

```python
class SolverResult(TypedDict):
    # ... (các trường cũ giữ nguyên)
    
    premises_used: Optional[list[int]]
    """
    Danh sách index (0-based) của các premises được sử dụng để chứng minh.
    - Track 1 (Z3): Mảng số nguyên (ví dụ: [0, 2]). Được map từ unsat core.
    - Track 2 (SymPy): Không áp dụng, mặc định là None hoặc [].
    """
```

### 3.2. Sửa file `api/main.py` (Khi nối cáp Track 1)
Hiện tại `handle_predict()` phần `"type1"` đang trả về kết quả Mock. Khi tiến hành nối luồng Pipeline của Track 1 vào, cần trích xuất giá trị này từ state để truyền cho `build_response`:

```python
# Lấy state cuối cùng từ pipeline graph
solver_result = state.get("solver_result", {})
premises_used = solver_result.get("premises_used") or []

return build_response(
    query_id=request.query_id,
    query_type="type1",
    answer=answer,
    explanation=explanation,
    raw_unit="",
    steps=steps,
    premises_used=premises_used  # <--- Gắn mảng lấy từ state vào đây
)
```

### 3.3. Hướng dẫn dành cho Team Code Z3 (`pipeline/type1/z3_solver.py`)
Khi code node `z3_solver`, sau khi giải xong và dò được Unsat Core (những dữ kiện tham gia chứng minh), các bạn phải map nó ra các con số index tương ứng trong mảng `request.premises`. 

Khi trả về dictionary `SolverResult` ở cuối hàm, hãy nhớ nhét thêm key này:

```python
return {
    "answer": final_answer,
    "unit": None,
    "steps": proof_steps,
    "fol": fol_list,
    "source": "z3",
    "confidence": 1.0,
    "premises_used": used_indices_list  # <--- Ví dụ: [0, 1, 3]
}
```

---
**Trạng thái Kế hoạch:** Sẵn sàng thực thi. Kế hoạch này đảm bảo tuân thủ thiết kế "Single source of truth" (Rule #9) của dự án.
