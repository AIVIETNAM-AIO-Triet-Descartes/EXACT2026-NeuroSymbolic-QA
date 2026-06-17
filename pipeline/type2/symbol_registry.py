"""
pipeline/type2/symbol_registry.py

Single Source of Truth for physics symbols in the pipeline.
Resolves variable naming conflicts between DB, Regex, and Classifier.
"""

from typing import Optional

# Canonical symbol cho mỗi đại lượng
# Lưu ý: Các từ khóa gồm nhiều từ (multi-word) PHẢI nằm trước từ đơn lẻ
# (vd: "potential energy" trước "energy") vì regex extractor sẽ duyệt tuần tự
# và trả về match đầu tiên.
CANONICAL: dict[str, str] = {
    # Năng lượng / Công
    "capacitor_energy":     "W",
    "inductor_energy":      "W",
    "potential energy":     "W",
    "energy":               "W",
    "work":                 "W",

    # Điện trường & Điện thế
    "electric field":       "E_field",
    "field strength":       "E_field",
    "electric potential":   "V",
    "potential difference": "U",
    "intensity":            "E_field",
    "voltage":              "U",

    # Mạch điện xoay chiều & Từ trường
    "electromotive force":  "e",
    "induced EMF":          "e",
    "self-induced":         "e",
    "emf":                  "e",
    "inductive reactance":  "Z_L",
    "capacitive reactance": "Z_C",
    "impedance":            "Z",
    "reactance":            "Z_L", # Default fallback if unspecific
    "power factor":         "cos_phi",
    
    # Các đại lượng cơ bản khác
    "capacitor needed":     "C",
    "capacitance":          "C",
    "self-inductance":      "L",
    "inductance":           "L",
    "magnetic flux":        "Φ",
    "magnetic field":       "B",
    "flux":                 "Φ",
    "resistance":           "R",
    "current":              "I",
    "power":                "P",
    "charge":               "Q",
    "force":                "F",
    "frequency":            "f",
    "period":               "T",
}

# Alias map: canonical → tất cả ký hiệu có thể gặp trong formulas hoặc đề bài
ALIASES: dict[str, list[str]] = {
    "W":       ["W", "E", "W_C", "W_L", "U_E"],
    "e":       ["e", "EMF", "emf", "ε", "E"],
    "E_field": ["E_field", "E", "E0"],
    "Z_L":     ["Z_L", "X_L"],
    "Z_C":     ["Z_C", "X_C"],
    "U":       ["U", "V"],
    "Φ":       ["Φ", "Phi", "phi"],
}

# Bản đồ lọc Alias theo Domain để giải quyết xung đột ý nghĩa của ký hiệu
DOMAIN_ALIASES: dict[str, dict[str, str]] = {
    "electrostatics": {
        "E": "E_field", # Trong tĩnh điện, 'E' thường trỏ tới Điện trường
    },
    "ac_circuits": {
        "E": "W",       # Trong mạch xoay chiều, 'E' đôi khi trỏ tới Năng lượng
    },
    "circuits": {
        "E": "e",       # Trong mạch một chiều, 'E' đôi khi là suất điện động
    }
}

def get_aliases(symbol: str, domain: Optional[str] = None) -> list[str]:
    """Lấy danh sách các ký hiệu thay thế an toàn dựa trên Domain của bài toán.
    Hữu ích để SymPy fallback khi giải không ra biến mục tiêu.
    """
    resolved_sym = symbol
    if domain and domain in DOMAIN_ALIASES:
        resolved_sym = DOMAIN_ALIASES[domain].get(symbol, symbol)
    
    # Ký hiệu chính luôn được ưu tiên đầu tiên
    result = [resolved_sym]
    
    # Thêm các alias nếu có
    for alias in ALIASES.get(resolved_sym, []):
        if alias not in result:
            result.append(alias)
            
    # Đặc biệt, nếu resolved_sym không có trong ALIASES nhưng bản thân nó là một alias của thằng khác
    # (Ví dụ: truyền vào "E", resolved_sym = "E_field", thì ALIASES["E_field"] sẽ có "E")
    
    return result
