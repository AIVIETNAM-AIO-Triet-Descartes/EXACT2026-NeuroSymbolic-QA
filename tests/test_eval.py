import pytest
import math
from evaluation.answer_compare import compare_answer, parse_number, split_multi, to_si

# ==========================================
# 1. Tests for parse_number

def test_parse_number_basic():
    assert parse_number("5.00") == 5.0
    assert parse_number("5") == 5.0
    assert parse_number("0") == 0.0
    assert parse_number("-3.14") == -3.14

def test_parse_number_scientific():
    # Various multiplication signs and formats
    assert parse_number("4.5e-2") == 0.045
    assert parse_number("4.5 x 10^-2") == 0.045
    assert parse_number("4.5 × 10^-2") == 0.045
    assert parse_number("4.5 * 10^-2") == 0.045
    assert parse_number("4.5 \\times 10^{-2}") == 0.045

def test_parse_number_latex():
    # LaTeX math extraction
    assert math.isclose(parse_number("9\\sqrt{3} × 10^-27"), 9 * math.sqrt(3) * 1e-27, rel_tol=1e-5)
    assert math.isclose(parse_number("\\sqrt{2}"), math.sqrt(2), rel_tol=1e-5)
    assert math.isclose(parse_number("\\frac{1}{2}"), 0.5, rel_tol=1e-5)
    assert math.isclose(parse_number("100\\pi"), 100 * math.pi, rel_tol=1e-5)

def test_parse_number_labeled():
    # Extraction from equations (e.g. THCB problems)
    assert parse_number("I_D1=1.0") == 1.0
    assert parse_number("I_total=2.0") == 2.0
    assert parse_number("U_1 = 220.5") == 220.5

def test_parse_number_unparseable():
    # Edge cases and pure text
    assert parse_number("upward parabola") is None
    assert parse_number("all energy is stored") is None
    assert parse_number("") is None
    assert parse_number(None) is None


# ==========================================
# 2. Tests for to_si

def test_to_si_basic():
    assert to_si(100.0, "mJ") == 0.1
    assert to_si(50.0, "pF") == 50e-12
    assert to_si(3.0, "kV/m") == 3000.0
    assert to_si(2.0, "A") == 2.0
    assert to_si(10.0, "-") == 10.0
    assert to_si(10.0, "—") == 10.0
    assert to_si(10.0, "") == 10.0

def test_to_si_unrecognized():
    # Should leave value untouched if unit is not in expected SI mapping
    assert to_si(15.0, "unknown_unit") == 15.0 
    assert to_si(0.5, "degree") == 0.5 


# ==========================================
# 3. Tests for split_multi

def test_split_multi():
    assert split_multi("0.6; 1.2") == ["0.6", "1.2"]
    assert split_multi("I_D1=1.0; I_D2=1.0; I_total=2.0") == ["I_D1=1.0", "I_D2=1.0", "I_total=2.0"]
    assert split_multi("yes; no") == ["yes", "no"]
    assert split_multi("single_value") == ["single_value"]
    assert split_multi(" 1.5 ; 2.5 ") == ["1.5", "2.5"]
    assert split_multi("") == []


# ==========================================
# 4. Tests for compare_answer (Core logic)

def test_compare_answer_numeric_in_tol():
    res = compare_answer(pred="5.0", gold="5.00", gold_unit="")
    assert res["correct"] is True
    assert res["kind"] == "numeric"

    # With unit conversion: pred is always assumed to be SI base unit in numeric kind
    # gold is 100 mJ (0.1 J) and pred is 0.1
    res = compare_answer(pred="0.1", gold="100", gold_unit="mJ") 
    assert res["correct"] is True

def test_compare_answer_numeric_out_tol():
    res = compare_answer(pred="5.5", gold="5.0", gold_unit="")
    assert res["correct"] is False
    assert res["kind"] == "numeric"

def test_compare_answer_tolerance_boundary():
    # Exactly 5% error
    res = compare_answer(pred="105", gold="100", gold_unit="")
    assert res["correct"] is True

    # 4.99% error
    res = compare_answer(pred="104.99", gold="100", gold_unit="")
    assert res["correct"] is True

    # 5.01% error
    res = compare_answer(pred="105.01", gold="100", gold_unit="")
    assert res["correct"] is False

def test_compare_answer_zero_value():
    res = compare_answer(pred="0", gold="0", gold_unit="")
    assert res["correct"] is True
    assert res["kind"] == "numeric"

    # Handle tiny absolute errors near 0 without dividing by zero
    res = compare_answer(pred="1e-10", gold="0", gold_unit="")
    assert res["correct"] is True

    res = compare_answer(pred="0.051", gold="0", gold_unit="")
    assert res["correct"] is False

def test_compare_answer_scientific_and_latex():
    res = compare_answer(pred="4.5e-2", gold="4.5 × 10^-2", gold_unit="")
    assert res["correct"] is True

    res = compare_answer(pred="1.558845e-26", gold="9\\sqrt{3} × 10^-27", gold_unit="")
    assert res["correct"] is True

    # Test space separated dots
    res = compare_answer(pred="4.0e-9", gold="4 . 10^{-9}", gold_unit="")
    assert res["correct"] is True

    # Test forward slash typos
    res = compare_answer(pred="0.5", gold="/frac{1}{2}", gold_unit="")
    assert res["correct"] is True

    res = compare_answer(pred="3.14159265", gold="/pi", gold_unit="")
    assert res["correct"] is True

    res = compare_answer(pred="2.0", gold="/sqrt{4}", gold_unit="")
    assert res["correct"] is True

    # Make sure normal division is unaffected
    assert parse_number("1/2") == 0.5

    # Test Unicode superscripts
    res = compare_answer(pred="0.00023", gold="0.230 × 10⁻³", gold_unit="")
    assert res["correct"] is True

    # Test percent sign stripping
    res = compare_answer(pred="50", gold="50%", gold_unit="")
    assert res["correct"] is True

def test_compare_answer_yes_no():
    res = compare_answer(pred="Yes", gold="yes", gold_unit="")
    assert res["correct"] is True
    assert res["kind"] == "yes_no"

    res = compare_answer(pred="No", gold="Yes", gold_unit="")
    assert res["correct"] is False

    res = compare_answer(pred="YES", gold="Yes", gold_unit="")
    assert res["correct"] is True

def test_compare_answer_multi():
    # Normal multi-answer
    res = compare_answer(pred="0.6; 1.2", gold="0.6; 1.2", gold_unit="cm; %")
    assert res["correct"] is True
    assert res["kind"] == "multi"

    # Wrong order
    res = compare_answer(pred="1.2; 0.6", gold="0.6; 1.2", gold_unit="cm; %")
    assert res["correct"] is False

    # Partial incorrect
    res = compare_answer(pred="0.6; 1.5", gold="0.6; 1.2", gold_unit="cm; %")
    assert res["correct"] is False

    # Labeled multi
    res = compare_answer(pred="1.0; 1.0; 2.0", gold="I_D1=1.0; I_D2=1.0; I_total=2.0", gold_unit="A; A; A")
    assert res["correct"] is True

def test_compare_answer_qualitative():
    # Word overlap < threshold -> incorrect but needs review
    res = compare_answer(pred="downward parabola", gold="upward parabola", gold_unit="")
    assert res["correct"] is False
    assert res["kind"] == "qualitative"
    assert res["needs_review"] is True

    # High token overlap ignoring punctuation -> correct & needs review
    res = compare_answer(pred="all energy is stored in the magnetic field.", gold="all energy is stored in magnetic field", gold_unit="")
    assert res["correct"] is True
    assert res["kind"] == "qualitative"
    assert res["needs_review"] is True

def test_compare_answer_unparseable():
    # gold is numeric, pred is unparseable text
    res = compare_answer(pred="parabola", gold="5.0", gold_unit="")
    assert res["correct"] is False
    assert res["kind"] == "unparseable"
    assert res.get("detail", "") != ""


# ==========================================
# 5. Tests for metrics.py
# ==========================================

def test_evaluate_metrics():
    from evaluation.metrics import evaluate
    
    # Mock data
    truth = [
        {"id": "LD001", "answer": "0.05", "unit": "N"},
        {"id": "CHLT001", "answer": "No", "unit": "-"},
        {"id": "NL025", "answer": "all energy is entirely stored in the magnetic field", "unit": "-"},
        {"id": "THCB087", "answer": "0.6; 1.2", "unit": "cm; %"},
        {"id": "TD401", "answer": "0.045", "unit": "J"}
    ]
    
    predictions = [
        {"id": "LD001", "answer": "0.05", "source": "sympy"},
        {"id": "CHLT001", "answer": "No", "source": "resonance"},
        {"id": "NL025", "answer": "all energy is stored in magnetic field", "source": "llm_cot"},
        {"id": "THCB087", "answer": "0.6; 1.2", "source": "sympy"},
        {"id": "TD401", "answer": "wrong_ans", "source": "sympy"} # unparseable pred
    ]
    
    res = evaluate(predictions, truth)
    
    # Overall asserts
    assert res["overall"]["total"] == 5
    assert res["overall"]["evaluable"] == 3 # LD001 (numeric), CHLT001 (yes_no), THCB087 (multi)
    # TD401 is unparseable -> skipped. NL025 is qualitative -> skipped.
    assert res["overall"]["correct"] == 3 # LD001, CHLT001, THCB087 are all correct
    assert res["overall"]["accuracy"] == 1.0
    
    # Kind asserts
    assert res["by_kind"]["numeric"]["total"] == 2 # LD001, TD401
    assert res["by_kind"]["numeric"]["evaluable"] == 1 # only LD001
    assert res["by_kind"]["numeric"]["correct"] == 1
    assert res["by_kind"]["numeric"]["accuracy"] == 1.0
    
    assert res["by_kind"]["qualitative"]["total"] == 1
    assert res["by_kind"]["qualitative"]["evaluable"] == 0
    
    assert res["by_kind"]["yes_no"]["total"] == 1
    assert res["by_kind"]["yes_no"]["evaluable"] == 1
    assert res["by_kind"]["yes_no"]["correct"] == 1
    
    assert res["by_kind"]["multi"]["total"] == 1
    assert res["by_kind"]["multi"]["evaluable"] == 1
    assert res["by_kind"]["multi"]["correct"] == 1
    
    # Prefix asserts
    assert res["by_prefix"]["LD"]["total"] == 1
    assert res["by_prefix"]["LD"]["evaluable"] == 1
    assert res["by_prefix"]["LD"]["correct"] == 1
    
    # Source asserts
    assert res["by_source"]["sympy"]["total"] == 3 # LD001, THCB087, TD401
    assert res["by_source"]["sympy"]["evaluable"] == 2 # LD001, THCB087
    assert res["by_source"]["sympy"]["correct"] == 2
    assert res["by_source"]["sympy"]["accuracy"] == 1.0
    
    # Skipped and Wrong lists
    assert len(res["wrong"]) == 0
    # Skipped: NL025 (qualitative) and TD401 (unparseable)
    skipped_ids = {s["id"] for s in res["skipped"]}
    assert "NL025" in skipped_ids
    assert "TD401" in skipped_ids

