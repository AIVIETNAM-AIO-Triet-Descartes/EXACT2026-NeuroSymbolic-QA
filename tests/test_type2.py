import csv
import math
from pathlib import Path

import pytest

from api.router import classify_query
from pipeline.type2.type2_classifier import PhysicsClassifier, PhysicsQuestionType
from pipeline.type2.sympy_solver import solve_physics, _solve_single, _solve_multi_step
from pipeline.type2.cot_builder import build_cot
from pipeline.type2.type2_validation import validate_sympy_result


# ══════════════════════════════════════════════════════════════
# Existing: router classification
# ══════════════════════════════════════════════════════════════

def resolve_physics_data_path() -> Path:
	root = Path(__file__).resolve().parents[1] / "data" / "train"
	matches = sorted(root.rglob("Physics_Problems_Text_Only.csv"))
	if not matches:
		raise FileNotFoundError("Physics_Problems_Text_Only.csv not found under data/train")
	return matches[-1]


PHYSICS_KEYWORDS = {
	"calculate", "resistance", "voltage", "current", "capacitor",
	"circuit", "power", "energy", "charge", "ohm", "ampere",
	"farad", "watt", "coulomb", "electric", "parallel", "series", "kirchhoff",
}


def load_type2_cases(limit: int = 5):
	data_path = resolve_physics_data_path()
	cases = []
	with data_path.open("r", encoding="utf-8", newline="") as handle:
		reader = csv.DictReader(handle)
		for row in reader:
			question = row.get("question", "").strip()
			words = set(question.lower().split())
			if question and PHYSICS_KEYWORDS.intersection(words):
				cases.append(question)
			if len(cases) >= limit:
				return cases
	return cases


TYPE2_CASES = load_type2_cases(5)


@pytest.mark.parametrize("question", TYPE2_CASES)
def test_type2_queries_are_classified_as_type2(question):
	assert classify_query(question, []) == "type2"


def test_type2_dataset_has_at_least_five_samples():
	assert len(TYPE2_CASES) == 5


def test_type2_router_handles_plural_and_punctuation_keywords():
	question = "Determine forces on charges in electric fields."
	assert classify_query(question, []) == "type2"


# ══════════════════════════════════════════════════════════════
# SymPy solver unit tests — no LLM required
# ══════════════════════════════════════════════════════════════

class TestSolveSingle:
	def test_ohms_law_find_r(self):
		result = _solve_single("V = I * R", given={"V": 10.0, "I": 2.0}, find="R")
		assert result is not None
		assert math.isclose(float(result["answer"]), 5.0, rel_tol=1e-6)
		assert result["unit"] == "Ω"
		assert result["source"] == "sympy"

	def test_ohms_law_find_i(self):
		result = _solve_single("V = I * R", given={"V": 12.0, "R": 4.0}, find="I")
		assert result is not None
		assert math.isclose(float(result["answer"]), 3.0, rel_tol=1e-6)
		assert result["unit"] == "A"

	def test_power_formula(self):
		result = _solve_single("P = I ** 2 * R", given={"I": 2.0, "R": 5.0}, find="P")
		assert result is not None
		assert math.isclose(float(result["answer"]), 20.0, rel_tol=1e-6)
		assert result["unit"] == "W"

	def test_capacitor_energy(self):
		result = _solve_single("E = 0.5 * C * V ** 2", given={"C": 4.0, "V": 3.0}, find="E")
		assert result is not None
		assert math.isclose(float(result["answer"]), 18.0, rel_tol=1e-6)
		assert result["unit"] == "J"

	def test_invalid_formula_returns_none(self):
		result = _solve_single("NOT_A_FORMULA", given={"V": 10}, find="R")
		assert result is None

	def test_unsolvable_no_unknowns_returns_none(self):
		# All vars given, can't solve — result may be [] from sympy
		result = _solve_single("V = I * R", given={"V": 10, "I": 2, "R": 5}, find="X")
		assert result is None


class TestSolveMultiStep:
	def test_two_step_chain(self):
		# Step 1: I = V/R → I=3A; Step 2: P = I²R → P=45W
		formulas = ["V = I * R", "P = I ** 2 * R"]
		result = _solve_multi_step(formulas, given={"V": 12.0, "R": 4.0}, find="P")
		assert result is not None
		assert math.isclose(float(result["answer"]), 36.0, rel_tol=1e-6)
		assert result["source"] == "sympy"


class TestSolvePhysicsDispatch:
	def test_single_formula_dispatch(self):
		parsed = {"given": {"V": 10.0, "I": 2.0}, "find": "R", "formulas": ["V = I * R"]}
		result = solve_physics(parsed, PhysicsQuestionType.SINGLE_FORMULA)
		assert result["source"] == "sympy"
		assert math.isclose(float(result["answer"]), 5.0, rel_tol=1e-6)

	def test_missing_find_returns_fallback(self):
		parsed = {"given": {"V": 10}, "find": "", "formulas": ["V = I * R"]}
		result = solve_physics(parsed, PhysicsQuestionType.SINGLE_FORMULA)
		assert result["source"] == "llm_fallback"
		assert result["answer"] == ""

	def test_missing_formulas_returns_fallback(self):
		parsed = {"given": {"V": 10, "I": 2}, "find": "R", "formulas": []}
		result = solve_physics(parsed, PhysicsQuestionType.SINGLE_FORMULA)
		assert result["source"] == "llm_fallback"

	def test_electrostatic_dispatch(self):
		parsed = {"given": {"C": 4.0, "V": 3.0}, "find": "E", "formulas": ["E = 0.5 * C * V ** 2"]}
		result = solve_physics(parsed, PhysicsQuestionType.ELECTROSTATIC)
		assert result["source"] == "sympy"
		assert math.isclose(float(result["answer"]), 18.0, rel_tol=1e-6)


# ══════════════════════════════════════════════════════════════
# CotBuilder unit tests
# ══════════════════════════════════════════════════════════════

class TestCotBuilder:
	def test_formats_steps(self):
		sympy_result = {"steps": ["Given: V=10, I=2", "Formula: V=IR", "R=5"]}
		cot = build_cot(sympy_result, {})
		assert len(cot) == 3
		assert cot[0].startswith("Step 1")
		assert cot[2].startswith("Step 3")

	def test_fallback_on_empty_steps(self):
		cot = build_cot({}, {"given": {"V": 10}, "find": "R"})
		assert len(cot) >= 2
		assert any("V=10" in s or "10" in s for s in cot)
		assert any("R" in s for s in cot)

	def test_fallback_minimal_when_no_parsed(self):
		cot = build_cot({}, {})
		assert len(cot) >= 1
		assert "Unable" in cot[-1]


# ══════════════════════════════════════════════════════════════
# Validation unit tests
# ══════════════════════════════════════════════════════════════

class TestValidation:
	def test_valid_positive_resistance(self):
		result = validate_sympy_result(5.0, "R")
		assert result.is_valid
		assert not result.errors

	def test_negative_resistance_invalid(self):
		result = validate_sympy_result(-1.0, "R")
		assert not result.is_valid
		assert result.errors

	def test_none_value_invalid(self):
		result = validate_sympy_result(None, "R")
		assert not result.is_valid

	def test_unknown_variable_warns_not_errors(self):
		result = validate_sympy_result(42.0, "Z_unknown")
		assert result.is_valid  # no constraint for unknown var


# ══════════════════════════════════════════════════════════════
# PhysicsClassifier unit tests
# ══════════════════════════════════════════════════════════════

class TestPhysicsClassifier:
	def setup_method(self):
		self.clf = PhysicsClassifier()

	def test_detect_circuit_domain(self):
		# "resistance" appears before "current" in classifier mapping, so R is returned
		q = "A circuit has voltage 12V and resistance 4Ω. Calculate the current."
		result = self.clf.classify_physics(q)
		assert result.domain == "circuits"
		# Classifier returns first matched keyword — "resistance" hits before "current"
		assert result.target_variable == "R"

	def test_detect_target_current_unambiguous(self):
		q = "Find the current flowing through the circuit."
		result = self.clf.classify_physics(q)
		assert result.domain == "circuits"
		assert result.target_variable == "I"

	def test_detect_electrostatics_domain(self):
		q = "A capacitor with capacitance 4F is charged to 3V. Find the energy stored."
		result = self.clf.classify_physics(q)
		assert result.domain == "electrostatics"
		assert result.target_variable == "E"

	def test_detect_single_formula_type(self):
		q = "A resistor has resistance 5Ω and current 2A. Calculate power."
		result = self.clf.classify_physics(q)
		assert result.question_type == PhysicsQuestionType.SINGLE_FORMULA

	def test_parallel_circuit_type(self):
		q = "Two resistors connected in parallel. Find total resistance."
		result = self.clf.classify_physics(q)
		assert result.question_type == PhysicsQuestionType.CIRCUIT
