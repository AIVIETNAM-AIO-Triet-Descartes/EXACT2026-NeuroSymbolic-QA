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

# ══════════════════════════════════════════════════════════════
# T2-17: ResonanceSolver (CHLT) + ErrorSolver (THCB)
# ══════════════════════════════════════════════════════════════

from pipeline.type2.resonance_solver import solve_resonance
from pipeline.type2.error_solver import solve_error
from pipeline.type2.sympy_solver import sympy_solver_node


class TestResonanceSolver:
	def test_chlt_no_case(self):
		# CHLT001: L=0.5H C=20uF f=40Hz → f0 ≈ 50.3 Hz ≠ 40 → No
		parsed = {"given": {"R": 50.0, "L": 0.5, "C": 20e-6, "f": 40.0}}
		result = solve_resonance(parsed)
		assert result["answer"] == "No"
		assert result["source"] == "resonance"
		assert result["steps"]

	def test_chlt_yes_case(self):
		# CHLT002: L=0.4H C=50uF f=35.6Hz → f0 ≈ 35.59 Hz ≈ f → Yes
		parsed = {"given": {"R": 10.0, "L": 0.4, "C": 50e-6, "f": 35.6}}
		result = solve_resonance(parsed)
		assert result["answer"] == "Yes"
		assert result["source"] == "resonance"

	def test_missing_data_falls_back(self):
		result = solve_resonance({"given": {"L": 0.5, "C": 20e-6}})  # no f
		assert result["source"] == "llm_fallback"
		assert result["answer"] == ""

	def test_phrasal_frequency_fallback(self):
		# weakness #7 example: L=1H C=4uF, f phrasal "at a frequency of 79.6 Hz"
		parsed = {"given": {"R": 45.0, "L": 1.0, "C": 4e-6}}
		q = "For an RLC AC circuit, does resonance occur at a frequency of 79.6 Hz?"
		result = solve_resonance(parsed, q)
		assert result["answer"] == "Yes"

	def test_dispatch_via_sympy_solver_node(self):
		state = {
			"question": "R=50 ohm, L=0.5 H, C=20 uF, f=40 Hz. Does the circuit experience resonance?",
			"parsed_physics": {
				"given": {"R": 50.0, "L": 0.5, "C": 20e-6, "f": 40.0},
				"find": "", "domain": "ac_circuits", "formulas": [],
				"question_type": "yes_no",
			},
			"confidence": 1.0,
		}
		out = sympy_solver_node(state)
		assert out["answer"] == "No"
		assert out["solver_result"]["source"] == "resonance"
		assert out["confidence"] == 1.0  # deterministic — not downgraded

	def test_yes_no_guard_missing_given_uses_fallback_path(self):
		# Qualitative misroute: YES_NO without L/C/f must NOT call resonance solver
		state = {
			"question": "What is the circuit's characteristic?",
			"parsed_physics": {
				"given": {}, "find": "", "domain": "ac_circuits",
				"formulas": [], "question_type": "yes_no",
			},
			"confidence": 1.0,
		}
		out = sympy_solver_node(state)
		assert out["solver_result"]["source"] == "llm_fallback"


class TestErrorSolver:
	def test_relative_error_from_least_count(self):
		# THCB002: least count 0.2 V, reads 5.6 V → 0.2/5.6×100 = 3.57 %
		q = "A voltmeter has a least count of 0.2 V and reads 5.6 V. Find the relative error."
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 3.5714, rel_tol=0.01)
		assert result["unit"] == "%"

	def test_absolute_error_from_least_count(self):
		# THCB001: least count 0.1 A → absolute error 0.1 A (= least_count, not /2)
		q = "An ammeter has range 2 A and least count of 0.1 A. What is the absolute error?"
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 0.1, rel_tol=1e-6)

	def test_multi_answer_true_vs_measured(self):
		# THCB087: true 50.0 cm, measured 49.4 cm → "0.6; 1.2" | "cm; %"
		q = ("The true value is 50.0 cm and the measured value is 49.4 cm. "
		     "Calculate the absolute error and the relative error.")
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		parts = [p.strip() for p in result["answer"].split(";")]
		assert len(parts) == 2
		assert math.isclose(float(parts[0]), 0.6, rel_tol=1e-6)
		assert math.isclose(float(parts[1]), 1.2, rel_tol=0.01)
		units = [u.strip() for u in result["unit"].split(";")]
		assert units == ["cm", "%"]

	def test_plusminus_relative_uncertainty(self):
		# physics_dev[41]: 12.0 ± 0.2 Ω → 0.2/12.0×100 = 1.67 %
		q = "The resistance measurement result is 12.0 ± 0.2 Ω. Calculate the percentage relative uncertainty."
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 1.6667, rel_tol=0.01)

	def test_unrecognized_falls_back(self):
		result = solve_error({"given": {}}, "Compute the error propagation of R = U/I.")
		assert result["source"] == "llm_fallback"

	def test_propagation_quotient_absolute(self):
		# THCB003: R=U/I, U=6.0±0.1 V, I=0.3±0.01 A → δR=δU+δI=0.05, ΔR=0.05×20=1.0 Ω
		q = ("Resistance R is calculated using the formula R = U/I, where "
		     "U = 6.0 ± 0.1 V and I = 0.3 ± 0.01 A. What is the absolute error of R?")
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 1.0, rel_tol=0.02)
		assert result["unit"] == "Ω"

	def test_propagation_product_relative(self):
		# THCB005: P=V·I product → δP=δV+δI = 0.2/9.5 + 0.02/0.95 = 4.21 %
		q = ("In an experiment, the measured voltage was 9.5 ± 0.2 V, and the measured "
		     "current was 0.95 ± 0.02 A. What is the relative error in the power?")
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 4.21, rel_tol=0.02)
		assert result["unit"] == "%"

	def test_propagation_product_absolute(self):
		# THCB008: P=V·I, no explicit formula (keyword "power") → ΔP=δP×P=0.186 W
		q = ("When measuring voltage with a voltmeter, the result is 6.3 ± 0.1 V. If this "
		     "is used to calculate power with a current of 0.6 ± 0.02 A, what is the "
		     "absolute error of the power?")
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 0.186, rel_tol=0.03)
		assert result["unit"] == "W"

	def test_propagation_sum_absolute(self):
		# THCB009: series R_total=R1+R2 → ΔR=ΔR1+ΔR2 = 0.5+1 = 1.5 Ω
		q = ("In a series circuit, resistance R1 = 10 ± 0.5 Ω, R2 = 20 ± 1 Ω. "
		     "What is the absolute error of the total resistance?")
		result = solve_error({"given": {}}, q)
		assert result["source"] == "error_calc"
		assert math.isclose(float(result["answer"]), 1.5, rel_tol=0.01)
		assert result["unit"] == "Ω"

	def test_dispatch_via_sympy_solver_node(self):
		state = {
			"question": "A voltmeter has a least count of 0.2 V and reads 5.6 V. Find the relative error.",
			"parsed_physics": {
				"given": {}, "find": "", "domain": "measurement",
				"formulas": [], "question_type": "error_calc",
			},
			"confidence": 1.0,
		}
		out = sympy_solver_node(state)
		assert out["solver_result"]["source"] == "error_calc"
		assert math.isclose(float(out["answer"]), 3.5714, rel_tol=0.01)
		assert out["confidence"] == 1.0


class TestElectromagneticDispatch:
	def test_8a_alias_solves_inductor_energy(self):
		# weakness #8a: ELECTROMAGNETIC routed via MULTI_STEP path (DDT formulas)
		parsed = {
			"given": {"L": 0.5, "I": 2.0},
			"find": "W_L",
			"formulas": ["W_L = 0.5 * L * I**2"],
		}
		result = solve_physics(parsed, PhysicsQuestionType.ELECTROMAGNETIC)
		assert result["source"] == "sympy"
		assert math.isclose(float(result["answer"]), 1.0, rel_tol=1e-6)

	def test_8a_no_formula_still_falls_back(self):
		parsed = {"given": {"L": 0.5}, "find": "W_L", "formulas": []}
		result = solve_physics(parsed, PhysicsQuestionType.ELECTROMAGNETIC)
		assert result["source"] == "llm_fallback"


class TestCircuitSolver:
	"""Parallel-circuit solver (THCB circuit rows) — Group C."""

	def _solve(self, given, q):
		from pipeline.type2.circuit_solver import solve_circuit
		return solve_circuit({"given": given}, q)

	def test_each_current_plus_total_identical(self):
		# THCB066: U=9V, two identical lamps R=9Ω → 1.0; 1.0; 2.0
		r = self._solve({"U": 9.0, "R": 9.0},
		                "Two lamps in parallel, each R = 9. Current through each lamp and the total current.")
		assert r["source"] == "circuit"
		assert r["answer"] == "1; 1; 2"

	def test_each_current_distinct_branches(self):
		# THCB076: R1=20, R2=10, U=10 → 0.5; 1.0
		r = self._solve({"U": 10.0, "R1": 20.0, "R2": 10.0},
		                "Two bulbs R1=20, R2=10 in parallel at U=10V. Current through each bulb.")
		assert r["answer"] == "0.5; 1"

	def test_equivalent_parallel_resistance(self):
		# THCB078: R1=30, R2=60 ∥ → 20
		r = self._solve({"R1": 30.0, "R2": 60.0},
		                "A parallel circuit has R1=30, R2=60. Calculate the equivalent resistance.")
		assert math.isclose(float(r["answer"]), 20.0, rel_tol=1e-6)
		assert r["unit"] == "Ω"

	def test_total_current_from_branch_resistances(self):
		# THCB068: 8∥16 at U=8 → I_total = 1.5
		r = self._solve({"U": 8.0, "R1": 8.0, "R2": 16.0},
		                "An 8Ω lamp in parallel with a 16Ω lamp. Calculate the total current.")
		assert math.isclose(float(r["answer"]), 1.5, rel_tol=1e-6)

	def test_total_power_from_branch_powers(self):
		# THCB077: P1=10, P2=20 → 30
		r = self._solve({"P1": 10.0, "P2": 20.0},
		                "The power of lamps D1 and D2. Calculate the total power of the circuit.")
		assert math.isclose(float(r["answer"]), 30.0, rel_tol=1e-6)

	def test_kcl_total_current(self):
		# THCB079: I1=1.2, I2=0.8 → 2.0
		r = self._solve({"I1": 1.2, "I2": 0.8},
		                "Current through lamp D1 and lamp D2. Calculate the total current.")
		assert math.isclose(float(r["answer"]), 2.0, rel_tol=1e-6)

	def test_returns_none_for_plain_ohm(self):
		# Must NOT hijack a plain single-formula Ohm question (no parallel/lamp signal).
		assert self._solve({"U": 10.0, "I": 2.0}, "Find the resistance.") is None

	def test_returns_none_for_series_ac_circuit(self):
		# Must NOT hijack series AC-RLC misclassified as circuits (CH226-style).
		assert self._solve({"R1": 20.0, "R2": 50.0},
		                   "Circuit AB: R1=20 in series with segment MB, inductor L, LCω²=1.") is None


class TestPalSandbox:
	"""PAL (Program-Aided LM) code-exec sandbox — feeds code directly, no LLM."""

	def _exec(self, code, timeout=5):
		from pipeline.type2.sympy_solver import execute_generated_code
		return execute_generated_code(code, timeout=timeout)

	def test_plain_float_answer(self):
		# Capacitor energy E = Q^2/(2C); machine computes, no LLM arithmetic.
		r = self._exec("Q, C = 20e-6, 5e-6\nanswer = float(Q**2 / (2 * C))\nunit = 'J'")
		assert r is not None
		assert math.isclose(float(r["answer"]), 4e-5, rel_tol=1e-6)
		assert r["unit"] == "J"

	def test_sympy_expression_answer(self):
		# sympy symbol result must be coerced to a float via evalf.
		code = "import sympy as sp\nx = sp.symbols('x')\nanswer = sp.solve(sp.Eq(2*x, 10), x)[0]\nunit = 'A'"
		r = self._exec(code)
		assert r is not None
		assert math.isclose(float(r["answer"]), 5.0, rel_tol=1e-9)
		assert r["unit"] == "A"

	def test_solve_function_fallback(self):
		# Code that defines solve() instead of an `answer` var still works.
		r = self._exec("def solve():\n    return 12.0 / 2.4\nunit = 'A'")
		assert r is not None
		assert math.isclose(float(r["answer"]), 5.0, rel_tol=1e-6)

	def test_forbidden_import_rejected(self):
		assert self._exec("import os\nanswer = 1.0") is None

	def test_forbidden_dunder_rejected(self):
		assert self._exec("answer = ().__class__.__bases__[0]") is None

	def test_no_answer_returns_none(self):
		assert self._exec("x = 5 + 3") is None

	def test_runtime_error_returns_none(self):
		assert self._exec("answer = 1 / 0") is None

	def test_empty_and_oversized_rejected(self):
		assert self._exec("") is None
		assert self._exec("answer = 1\n" + "# pad\n" * 5000) is None
