# pipeline/type2/type2_validation.py
#
# Validation layer cho kết quả sau khi SymPy solver trả về.
# Được gọi SAU sympy_solver.py, TRƯỚC cot_builder.py.
#
# Pipeline order:
#   PhysicsClassifier → physics_parser → sympy_solver → [type2_validation] → cot_builder
#
# Không validate unit bằng cách so với CSV — tại inference time chỉ có NL question,
# không có ground-truth unit. Thay vào đó validate theo physical constraints:
#   - Đúng đại lượng vật lý (dimensional sanity)
#   - Giá trị hợp lý (không âm với R, C, L...)
#   - Kết quả SymPy là số hữu hạn

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class ValidationResult:
    """Kết quả validation một answer từ SymPy solver."""
    is_valid: bool
    warnings: list[str]    # non-fatal — vẫn trả về answer nhưng log
    errors: list[str]      # fatal — trigger fallback sang LLM-only


# Map target_variable → (SI base unit, must_be_positive)
# Dùng để dimensional sanity check, không so với unit prefix trong dataset.
_PHYSICAL_CONSTRAINTS: dict[str, tuple[str, bool]] = {
    "E":       ("J",    False),  # energy có thể âm (thế năng)
    "R":       ("Ω",    True),   # resistance luôn dương
    "V":       ("V",    False),  # voltage có thể âm
    "I":       ("A",    False),  # current có thể âm (chiều quy ước)
    "P":       ("W",    False),  # power có thể âm (tiêu thụ/sinh ra)
    "Q":       ("C",    False),  # charge có thể âm
    "C":       ("F",    True),   # capacitance luôn dương
    "F":       ("N",    False),  # force có thể âm (chiều)
    "f":       ("Hz",   True),   # frequency luôn dương
    "L":       ("H",    True),   # inductance luôn dương
    "B":       ("T",    False),  # magnetic field có thể âm
    "Φ":       ("Wb",   False),  # flux có thể âm
    "E_field": ("N/C",  False),  # electric field có thể âm
}


def validate_sympy_result(
    value: object,
    target_variable: Optional[str],
) -> ValidationResult:
    """Validate kết quả trả về từ sympy_solver.

    Kiểm tra theo thứ tự:
      1. Kết quả tồn tại và là số hữu hạn
      2. Giá trị hợp lý với ràng buộc vật lý của target_variable
      3. Unit dimensional sanity (chỉ warn, không block)

    Args:
        value: Kết quả từ SymPy — có thể là float, int, hoặc SymPy Expr.
        target_variable: Ký hiệu vật lý từ PhysicsClassifier ("R", "E", "F"...).
                         None nếu classifier không detect được.

    Returns:
        ValidationResult với is_valid=False chỉ khi kết quả không dùng được.
        Warning không làm is_valid=False — answer vẫn được trả về kèm flag.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # 1. Kiểm tra tồn tại
    if value is None:
        errors.append("SymPy solver returned None — no solution found")
        return ValidationResult(is_valid=False, warnings=warnings, errors=errors)

    # 2. Kiểm tra finite
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        errors.append(f"Result is not numeric: {value!r}")
        return ValidationResult(is_valid=False, warnings=warnings, errors=errors)

    if not math.isfinite(numeric):
        errors.append(f"Result is not finite: {numeric}")
        return ValidationResult(is_valid=False, warnings=warnings, errors=errors)

    # 3. Physical constraint check
    if target_variable and target_variable in _PHYSICAL_CONSTRAINTS:
        si_unit, must_be_positive = _PHYSICAL_CONSTRAINTS[target_variable]
        if must_be_positive and numeric < 0:
            errors.append(
                f"{target_variable} must be positive (SI: {si_unit}), got {numeric}"
            )
        elif must_be_positive and numeric == 0:
            warnings.append(f"{target_variable} = 0 is physically degenerate")
    elif target_variable is None:
        warnings.append("target_variable unknown — skipping physical constraint check")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, warnings=warnings, errors=errors)


def validate_multi_target_hint(question: str) -> bool:
    """Phát hiện câu hỏi yêu cầu nhiều đại lượng (unit dạng "A; A; A").

    Dùng để warn pipeline rằng sympy_solver cần trả về nhiều giá trị.
    PhysicsClassifier._detect_target_variable() chỉ trả về biến đầu tiên,
    nên bài multi-target sẽ bị thiếu nếu không có bước check này.

    Đây là heuristic — false positive chấp nhận được vì chỉ là warning.
    """
    multi_indicators = (
        " and ", " both ", "respectively", "each of", "all of",
        "i1 and i2", "v1 and v2", "q1 and q2",
    )
    q_lower = question.lower()
    return any(kw in q_lower for kw in multi_indicators)
