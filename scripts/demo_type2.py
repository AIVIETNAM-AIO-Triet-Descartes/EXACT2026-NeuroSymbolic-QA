"""
scripts/demo_type2.py

Demo pipeline Track 2 — hỗ trợ cả chế độ có/không LLM.

Pipeline mặc định (--use-llm không bật):
    regex_extract → formula_rag → sympy_solver → cot_builder

Pipeline đầy đủ (--use-llm):
    regex_extract → [LLM augment nếu thiếu] → formula_rag
    → sympy_solver → [LLM CoT fallback nếu solver fail]
    → [LLM sinh explanation] → cot_builder

Run:
    python scripts/demo_type2.py                       # không LLM
    python scripts/demo_type2.py --limit 50            # 50 bài, không LLM
    python scripts/demo_type2.py --limit 50 --use-llm  # 50 bài, có LLM
"""

import argparse
import csv
import logging
import math
import os
import re
import sys
from typing import Optional

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.type2_classifier import PhysicsClassifier, PhysicsQuestionType
from pipeline.type2.formula_rag import formula_rag_node
from pipeline.type2.sympy_solver import sympy_solver_node
from pipeline.type2.cot_builder import cot_builder_node
from pipeline.type2.type2_validation import validate_sympy_result

CSV_PATH = "data/train/Physics_Problems_Text_Only.csv"
TOLERANCE = 0.02   # 2% relative tolerance for answer comparison

# Convert expected-answer units to SI base for fair comparison with SymPy output
_EXPECTED_UNIT_SI: dict[str, float] = {
    "pF": 1e-12, "nF": 1e-9, "uF": 1e-6, "μF": 1e-6, "mF": 1e-3, "F": 1.0,
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    "uA": 1e-6, "μA": 1e-6, "mA": 1e-3, "A": 1.0,
    "mV": 1e-3, "V": 1.0, "kV": 1e3,
    "mW": 1e-3, "W": 1.0, "kW": 1e3,
    "uJ": 1e-6, "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    "nC": 1e-9, "uC": 1e-6, "μC": 1e-6, "mC": 1e-3, "C": 1.0,
    "uH": 1e-6, "mH": 1e-3, "H": 1.0,
    "N": 1.0, "N/C": 1.0, "V/m": 1.0, "kV/m": 1e3, "MV/m": 1e6, "degree": 1.0,
}


# ══════════════════════════════════════════════════════════════
# Unit conversion table (prefix+base → SI factor)
# ══════════════════════════════════════════════════════════════

_UNIT_FACTORS: dict[str, float] = {
    # Capacitance
    "pF": 1e-12, "nF": 1e-9, "μF": 1e-6, "uF": 1e-6, "mF": 1e-3, "F": 1.0,
    # Resistance
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    # Current
    "μA": 1e-6, "uA": 1e-6, "mA": 1e-3, "A": 1.0, "kA": 1e3,
    # Voltage
    "μV": 1e-6, "mV": 1e-3, "V": 1.0, "kV": 1e3,
    # Power
    "μW": 1e-6, "mW": 1e-3, "W": 1.0, "kW": 1e3, "MW": 1e6,
    # Energy
    "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    # Charge
    "nC": 1e-9, "μC": 1e-6, "uC": 1e-6, "mC": 1e-3, "C": 1.0,
    # Inductance
    "μH": 1e-6, "mH": 1e-3, "H": 1.0,
    # Length (for distance-based formulas)
    "mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3,
    # Frequency
    "Hz": 1.0, "kHz": 1e3, "MHz": 1e6,
    # Force
    "N": 1.0,
}

# Some formulas use U for voltage, others V. Inject both so either formula works.
_SYM_VOLTAGE_ALIASES = {"U", "u"}


# ══════════════════════════════════════════════════════════════
# Regex-based given-value extractor (replaces LLM physics_parser)
# ══════════════════════════════════════════════════════════════

# Matches: SYM = MANTISSA [× 10^EXP] [UNIT]
# Examples: C = 100 μF   q1 = 6 × 10^-8 C   U = 30 V   k = 9 × 10^9 N
_ASSIGN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'              # symbol =
    r'([+-]?[\d.]+)'                         # mantissa (optional sign)
    r'(?:\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'  # × 10^exp (optional, use hex for ×)
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'   # unit prefix+base (optional)
)

# Bare power notation: SYM = MANTISSA^EXP UNIT  e.g. "q1 = 10^-8 C"
_BARE_POWER_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'
    r'([+-]?[\d.]+)\^([+-]?\d+)'            # mantissa^exp (pure power, no ×10)
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'
)

# "X cm apart" / "X m apart" / "separated by X cm" → AB distance
_APART_PAT = re.compile(
    r'([\d.]+)\s*(cm|m)\s+apart|'
    r'separated\s+by\s+([\d.]+)\s*(cm|m)',
    re.IGNORECASE,
)

# "side length X cm" / "side of X cm" / "side a = X cm" → a distance
_SIDE_PAT = re.compile(
    r'side\s+(?:length\s+|of\s+)?([\d.]+)\s*(cm|m)\b', re.IGNORECASE
)

# "X cm away from AB" / "X cm from AB" → perpendicular bisector distance
_BISECTOR_DIST_PAT = re.compile(
    r'([\d.]+)\s*(cm|m)\s+(?:away\s+from|from)\s+(?:AB|the\s+line|segment\s+AB)',
    re.IGNORECASE,
)

# Chained assignment: q1 = q2 = q3 = value unit
_CHAIN_PAT = re.compile(
    r'\b([A-Za-z_]\w*(?:\s*=\s*[A-Za-z_]\w*)+)'  # q1 = q2 = q3
    r'\s*=\s*([-]?[\d.]+)'                          # = value
    r'(?:\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?',
)

# Verb-context target detector: "calculate the energy" → "E"
_VERB_TARGET_MAP = {
    "energy": "E", "resistance": "R", "voltage": "V", "potential difference": "V",
    "current": "I", "power": "P", "charge": "Q", "capacitance": "C",
    "force": "F", "frequency": "f", "inductance": "L",
    "electric field": "E_field", "field strength": "E_field",
    "electric potential": "V", "potential energy": "E",
}
_VERB_PAT = re.compile(
    r'\b(?:calculate|find|determine|compute|what\s+is)\s+(?:the\s+)?'
    r'((?:[a-zA-Z]+\s+){0,2}[a-zA-Z]+)',
    re.IGNORECASE,
)
# Force-specific phrase patterns that the short verb window misses
_FORCE_PHRASE_PAT = re.compile(
    r'magnitude\s+of\s+(?:the\s+)?(?:net\s+)?(?:electric\s+)?force|'
    r'net\s+(?:electric\s+)?force|'
    r'resultant\s+force\s+(?:acting|on)|'
    r'force\s+exerted|'
    r'force\s+acting',
    re.IGNORECASE,
)
_E_FIELD_PHRASE_PAT = re.compile(
    r'electric\s+field\s+(?:strength|intensity|vector|magnitude|at)|'
    r'field\s+strength|'
    r'electric\s+field\s+caused|'
    r'electric\s+field\s+produced|'
    r'resultant\s+electric\s+field',
    re.IGNORECASE,
)
_ANGLE_PHRASE_PAT = re.compile(
    r'find\s+the\s+angle|'
    r'determine\s+the\s+angle|'
    r'angle\s+between\s+the\s+two\s+force',
    re.IGNORECASE,
)
# Negated chain: "q1 = -q2 = VALUE UNIT" → q1=+val, q2=-val
# Handles both "10^-7" (bare power) and "6 × 10^-7" (scientific) notation
_NEG_CHAIN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*-([A-Za-z_]\w*)\s*=\s*([+-]?[\d.]+)'
    r'(?:\^([+-]?\d+)|\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'  # bare ^exp OR ×10^exp
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'
)
# Unicode superscript digits/minus → ASCII helper
_SUP_TABLE = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺', '0123456789-+')


def _normalize_superscripts(text: str) -> str:
    return text.translate(_SUP_TABLE)


def detect_find_from_verb(question: str) -> Optional[str]:
    """Extract target variable from verb context ('calculate the force' → 'F')."""
    if _ANGLE_PHRASE_PAT.search(question):
        return "angle"
    # E-field check before force check (some E-field questions mention "force")
    if _E_FIELD_PHRASE_PAT.search(question):
        return "E_field"
    if _FORCE_PHRASE_PAT.search(question):
        return "F"
    for m in _VERB_PAT.finditer(question):
        noun = m.group(1).lower().strip()
        for kw, sym in _VERB_TARGET_MAP.items():
            if kw in noun:
                return sym
    return None


def extract_given(question: str) -> dict[str, float]:
    """
    Extract {symbol: SI_value} from question text via regex.
    Handles: C = 100 μF, q1 = 6 × 10^-8 C, k = 9 × 10^9 N m^2/C^2
    """
    given: dict[str, float] = {}
    # Normalize Unicode superscript chars (⁻⁸ → -8) before regex matching
    question = _normalize_superscripts(question)

    for m in _ASSIGN_PAT.finditer(question):
        sym = m.group(1)
        mantissa = float(m.group(2))
        exp_str = m.group(3)
        unit_str = m.group(4) or ""

        val = mantissa
        if exp_str:
            val *= 10 ** int(exp_str.replace("−", "-"))

        factor = _UNIT_FACTORS.get(unit_str, 1.0)
        val_si = val * factor

        given[sym] = val_si

        # Voltage aliases: some formulas use V, others U — inject both
        if sym in _SYM_VOLTAGE_ALIASES:
            given["V"] = val_si

    # "X cm apart" / "separated by X cm" → AB separation distance
    for m in _APART_PAT.finditer(question):
        if m.group(1):
            val, unit = float(m.group(1)), m.group(2)
        else:
            val, unit = float(m.group(3)), m.group(4)
        factor = 0.01 if unit.lower() == "cm" else 1.0
        if "AB" not in given:
            given["AB"] = val * factor

    # "side length X cm" → a (equilateral/polygon side length)
    for m in _SIDE_PAT.finditer(question):
        if "a" not in given:
            val = float(m.group(1))
            factor = 0.01 if m.group(2).lower() == "cm" else 1.0
            given["a"] = val * factor

    # Chained: q1 = q2 = q3 = value unit → assign all
    for m in _CHAIN_PAT.finditer(question):
        syms_part = m.group(1)
        mantissa = float(m.group(2))
        exp_str = m.group(3)
        unit_str = m.group(4) or ""
        val = mantissa * (10 ** int(exp_str.replace("−", "-")) if exp_str else 1)
        val_si = val * _UNIT_FACTORS.get(unit_str, 1.0)
        for sym in re.findall(r'[A-Za-z_]\w*', syms_part):
            given[sym] = val_si

    # Bare power: "q1 = 10^-8 C" → 10^(-8) = 1e-8 (overwrite incorrect ASSIGN_PAT value)
    # Sign rule: "-10^-6" means -(10^-6), not (-10)^(-6)
    for m in _BARE_POWER_PAT.finditer(question):
        sym = m.group(1)
        mantissa = float(m.group(2))
        exp = int(m.group(3))
        unit_str = m.group(4) or ""
        sign = -1.0 if mantissa < 0 else 1.0
        val_si = sign * (abs(mantissa) ** exp) * _UNIT_FACTORS.get(unit_str, 1.0)
        given[sym] = val_si

    # Negated chain: "q1 = -q2 = 10^-7 C" → q1=+1e-7, q2=-1e-7
    # Runs AFTER bare power so it takes final precedence for negated symbols.
    # Groups: (1)sym_pos (2)sym_neg (3)mantissa (4)bare_exp (5)sci_exp (6)unit
    for m in _NEG_CHAIN_PAT.finditer(question):
        sym_pos, sym_neg = m.group(1), m.group(2)
        mantissa = float(m.group(3))
        bare_exp = m.group(4)
        sci_exp = m.group(5)
        unit_str = m.group(6) or ""
        if bare_exp:
            sign = -1.0 if mantissa < 0 else 1.0
            val = sign * (abs(mantissa) ** int(bare_exp))
        elif sci_exp:
            val = mantissa * (10 ** int(sci_exp.replace("−", "-")))
        else:
            val = mantissa
        val_si = val * _UNIT_FACTORS.get(unit_str, 1.0)
        given[sym_pos] = val_si
        given[sym_neg] = -val_si

    # "X cm away from AB" → d_perp (perpendicular bisector offset)
    for m in _BISECTOR_DIST_PAT.finditer(question):
        if "d_perp" not in given:
            val = float(m.group(1))
            factor = 0.01 if m.group(2).lower() == "cm" else 1.0
            given["d_perp"] = val * factor

    return given


# ══════════════════════════════════════════════════════════════
# Expected answer parser
# ══════════════════════════════════════════════════════════════

def parse_expected(answer_str: str) -> Optional[float]:
    """
    Parse CSV answer column to float.
    Handles: "0.045", "24.45 x 10^-3", "8e-10"
    Returns None for complex LaTeX expressions (those containing backslash).
    """
    s = answer_str.strip()
    if not s:
        return None
    # Skip LaTeX / complex expressions
    if "\\" in s or "sqrt" in s.lower() or "," in s:
        return None

    # Normalize minus signs and multiply signs
    s = s.replace("−", "-").replace("×", "*")
    # "24.45 * 10^-3" → "24.45e-3"
    s = re.sub(r'\s*\*\s*10\^([-]?\d+)', r'e\1', s)
    s = s.replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════
# LLM integration helpers
# Các hàm này chỉ được gọi khi --use-llm được bật.
# Model GGUF chỉ load một lần (lazy singleton) để tiết kiệm thời gian.
# ══════════════════════════════════════════════════════════════

# Singleton LLMReasoner — None khi chưa load hoặc load thất bại
_REASONER = None
_LLM_FAILED = False   # True sau lần load đầu tiên thất bại → không retry


def _init_llm():
    """
    Khởi tạo LLMReasoner singleton (load model GGUF từ config.yaml).
    Chỉ thử load một lần; sau khi thất bại trả None ngay (không retry/log spam).
    Trả về None nếu model file không tìm thấy hoặc llama-cpp-python chưa cài.
    """
    global _REASONER, _LLM_FAILED
    if _REASONER is not None:
        return _REASONER
    if _LLM_FAILED:
        return None
    try:
        from llm import get_shared_reasoner
        # get_shared_reasoner() tạo LLMReasoner instance với vLLM server config.
        # check_server() gọi GET /v1/models để verify server đang chạy và reachable.
        print("[LLM] Connecting to vLLM server...")
        reasoner = get_shared_reasoner()
        reasoner.check_server()   # fail-fast nếu server chưa start
        _REASONER = reasoner
        print(f"[LLM] Connected OK — model: {reasoner.model_name}")
        return _REASONER
    except Exception as e:
        _LLM_FAILED = True
        print(f"[LLM] Cannot connect to vLLM server: {e}")
        print("[LLM] Running without LLM (SymPy + vector_solver only).")
        print("[LLM] Start server: vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000")
        return None


def _llm_augment_parse(question: str, given: dict, find: str):
    """
    Gọi LLM bổ sung kết quả regex extraction khi thiếu thông tin.

    Chỉ dùng khi regex không extract được 'find' hoặc 'given' rỗng.
    Regex luôn ưu tiên hơn LLM — LLM chỉ điền vào các slot còn trống.
    Trả về (merged_given, merged_find).
    """
    reasoner = _init_llm()
    if reasoner is None:
        return given, find
    try:
        llm_parsed = reasoner.parse_physics_question(question)
        llm_given = llm_parsed.get("given", {})
        llm_find = llm_parsed.get("find", "")

        # Merge: regex takes precedence, LLM fills gaps
        merged = dict(given)
        for k, v in llm_given.items():
            if k not in merged:
                merged[k] = v

        merged_find = find if find else llm_find
        return merged, merged_find
    except Exception as e:
        logger.warning(f"[LLM_AUGMENT] Failed: {e}")
        return given, find


def _llm_fallback_solve(question: str, given: dict, find: str, formulas: list) -> dict:
    """
    Gọi LLM giải bài toán vật lý khi SymPy + vector_solver đều thất bại.

    Dùng PHYSICS_COT_PROMPT với few-shot examples để guide LLM.
    Parse đáp án từ "ANSWER: <số> <đơn vị>" cuối response.
    Trả về dict tương thích sympy_result (answer, unit, steps, source).
    """
    reasoner = _init_llm()
    if reasoner is None:
        return {}
    try:
        result = reasoner.solve_physics_cot(question, given, find, formulas)
        return result
    except Exception as e:
        logger.warning(f"[LLM_FALLBACK] Failed: {e}")
        return {}


def _llm_explain(question: str, answer: str, unit: str, steps: list) -> str:
    """
    Gọi LLM sinh giải thích ngôn ngữ tự nhiên cho bài đã giải được.

    Nhận đáp án số + các bước giải từ SymPy/vector_solver/LLM CoT,
    sinh đoạn giải thích 2-3 câu về ý nghĩa vật lý và công thức áp dụng.
    Trả về "" nếu LLM thất bại (không ảnh hưởng đến accuracy evaluation).
    """
    reasoner = _init_llm()
    if reasoner is None:
        return ""
    try:
        return reasoner.explain_physics(question, answer, unit, steps)
    except Exception as e:
        logger.warning(f"[LLM_EXPLAIN] Failed: {e}")
        return ""


# ══════════════════════════════════════════════════════════════
# Demo runner
# ══════════════════════════════════════════════════════════════

def run_demo(limit: int = 20, use_llm: bool = False) -> None:
    clf = PhysicsClassifier()

    rows: list[dict] = []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            if len(rows) >= limit:
                break

    correct = wrong = fallback = skipped = 0
    detail_rows: list[tuple] = []

    for row in rows:
        qid = row["id"]
        question = row["question"]
        expected_str = row.get("answer", "")
        expected_unit_str = row.get("unit", "").strip()
        expected_val_raw = parse_expected(expected_str)
        # Convert expected to SI base using its unit column
        if expected_val_raw is not None:
            expected_val = expected_val_raw * _EXPECTED_UNIT_SI.get(expected_unit_str, 1.0)
        else:
            expected_val = None

        # 1. Classify (no LLM)
        classified = clf.classify_physics(question)

        # Verb-context detector overrides classifier (handles "charge" keyword noise)
        find = detect_find_from_verb(question) or classified.target_variable or ""

        # 2. Extract given values via regex (replaces physics_parser LLM call)
        given = extract_given(question)

        # [LLM AUGMENT] Khi regex không extract được 'find' hoặc 'given' rỗng,
        # gọi LLM parse_physics_question() để bổ sung thông tin còn thiếu.
        # Regex vẫn ưu tiên hơn (LLM chỉ điền vào slot trống).
        if use_llm and (not find or not given):
            given, find = _llm_augment_parse(question, given, find)

        parsed_physics = {
            "given": given,
            "find": find,
            "domain": classified.domain,
            "formulas": [],
            "units": {},
            "question_type": classified.question_type.value,
        }

        state: dict = {
            "question": question,
            "parsed_physics": parsed_physics,
            "confidence": 1.0,
        }

        # 3. FormulaRAG
        state = formula_rag_node(state)

        # 4. SymPy solver
        state = sympy_solver_node(state)

        # [LLM COT FALLBACK] Khi SymPy + vector_solver đều thất bại (source=llm_fallback),
        # gọi LLM giải bằng Chain-of-Thought với PHYSICS_COT_PROMPT.
        # Nếu LLM trả về số, source chuyển sang "llm_cot" và tham gia đánh giá accuracy.
        sympy_result = state.get("sympy_result", {})
        if use_llm and sympy_result.get("source") == "llm_fallback":
            llm_result = _llm_fallback_solve(
                question,
                given,
                find,
                state.get("parsed_physics", {}).get("formulas", []),
            )
            if llm_result.get("answer"):
                sympy_result = llm_result
                state["sympy_result"] = llm_result
                state["answer"] = llm_result.get("answer", "")

        # 5. Self-verifier
        got_str = sympy_result.get("answer", "")
        source = sympy_result.get("source", "?")
        confidence = state.get("confidence", 1.0)

        try:
            val = float(got_str) if got_str else None
            vr = validate_sympy_result(val, classified.target_variable)
            if not vr.is_valid:
                confidence = 0.4
        except Exception:
            pass

        # 6. CoT
        state = cot_builder_node(state)

        # [LLM EXPLAIN] Sau khi có đáp án (từ SymPy, vector_solver, hoặc LLM CoT),
        # gọi LLM sinh giải thích ngôn ngữ tự nhiên 2-3 câu về ý nghĩa vật lý.
        # explanation chỉ dùng để hiển thị, không ảnh hưởng accuracy evaluation.
        explanation = ""
        if use_llm and got_str:
            explanation = _llm_explain(
                question,
                got_str,
                sympy_result.get("unit", ""),
                sympy_result.get("steps", []),
            )

        # 7. Evaluate
        if source == "llm_fallback" or not got_str:
            tag = "FALLBACK"
            fallback += 1
        elif expected_val is None:
            tag = "SKIP"
            skipped += 1
        else:
            try:
                got_val = float(got_str)
                if abs(expected_val) > 1e-15:
                    rel_err = abs(got_val - expected_val) / abs(expected_val)
                else:
                    rel_err = abs(got_val - expected_val)
                if rel_err <= TOLERANCE:
                    tag = "CORRECT"
                    correct += 1
                else:
                    tag = f"WRONG({rel_err:.0%})"
                    wrong += 1
            except ValueError:
                tag = "PARSE_ERR"
                wrong += 1

        formula_used = ""
        if state.get("parsed_physics", {}).get("formulas"):
            formula_used = state["parsed_physics"]["formulas"][0][:25]

        expected_display = f"{expected_val:.6g}" if expected_val is not None else expected_str
        detail_rows.append((
            qid, tag, expected_display, got_str,
            find or "?",
            classified.domain[:6],
            source[:8],
            formula_used,
            explanation,   # cột cuối: chỉ có khi --use-llm
        ))

    # -- Print main table ------------------------------------------
    W = 100
    print(f"\n{'-' * W}")
    print(f"{'ID':<8} {'RESULT':<13} {'EXPECTED':<14} {'GOT':<12} {'FIND':<5} {'DOM':<7} {'SRC':<9} FORMULA")
    print(f"{'-' * W}")
    for r in detail_rows:
        print(f"{r[0]:<8} {r[1]:<13} {r[2]:<14} {r[3]:<12} {r[4]:<5} {r[5]:<7} {r[6]:<9} {r[7]}")
    print(f"{'-' * W}")

    total_eval = correct + wrong
    llm_label = " (+LLM)" if use_llm else ""
    print(f"\nSummary ({limit} questions{llm_label}):")
    print(f"  CORRECT  : {correct}")
    print(f"  WRONG    : {wrong}")
    print(f"  FALLBACK : {fallback}  (solver failed, no answer produced)")
    print(f"  SKIP     : {skipped}  (complex answer string, could not parse)")
    if total_eval > 0:
        print(f"  Accuracy : {correct}/{total_eval} = {correct / total_eval:.1%}  (numeric-evaluable subset)")
    print()

    # Print LLM explanations below table (only when --use-llm)
    if use_llm:
        has_explanations = any(r[8] for r in detail_rows)
        if has_explanations:
            print(f"\n{'=' * W}")
            print("LLM EXPLANATIONS")
            print(f"{'=' * W}")
            for r in detail_rows:
                if r[8]:  # r[8] = explanation string
                    print(f"\n[{r[0]}] {r[1]}")
                    # Print explanation safely, replacing unencodable chars
                    print(f"  {r[8].encode('ascii', errors='replace').decode('ascii')}")
            print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # ẩn INFO spam từ pipeline nodes
    parser = argparse.ArgumentParser(description="Demo pipeline Track 2 — physics solver")
    parser.add_argument("--limit", type=int, default=20,
                        help="Số bài toán cần chạy (mặc định 20)")
    parser.add_argument("--use-llm", action="store_true",
                        help="Bật LLM: augment extraction + CoT fallback + explanation")
    args = parser.parse_args()
    run_demo(args.limit, use_llm=args.use_llm)
