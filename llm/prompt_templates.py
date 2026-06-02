"""
Prompt Templates - Các mẫu prompt cho LLM reasoning.

Thiết kế theo nguyên tắc:
    - Step-aware Verification (SAFE, Liu et al., ACL 2025)
    - Chain-of-Thought (Wei et al., NeurIPS 2022)
    - Logic-LM Self-Refinement (Pan et al., ACL 2023)
"""

# ══════════════════════════════════════════════════════════════
# System Prompts
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_LOGIC = (
    "You are a formal logic reasoning assistant. "
    "You answer questions strictly based on the given premises using "
    "Modus Ponens, Modus Tollens, Hypothetical Syllogism, and Contraposition. "
    "Never introduce information not present in the premises. "
    "Be concise, precise, and reference premise numbers explicitly."
)

SYSTEM_PROMPT_Z3 = (
    "You are a Z3 theorem prover expert. "
    "You translate First-Order Logic (FOL) into executable Z3 Python code. "
    "Output ONLY valid Python code, no explanations."
)

# ══════════════════════════════════════════════════════════════
# Explanation Generation (Post-Z3, when answer is known)
# ══════════════════════════════════════════════════════════════

EXPLANATION_PROMPT = """Given the premises below and the verified correct answer, write a concise step-by-step logical explanation.

PREMISES:
{premises_nl}

QUESTION:
{question}

VERIFIED CORRECT ANSWER: {answer}
PREMISES USED: {premises_used}

INSTRUCTIONS:
1. Reference ONLY the premises listed in PREMISES USED (by their numbers, e.g., Premise 1, Premise 5).
2. Show the logical chain: which premise leads to what conclusion, step by step.
3. Use formal reasoning names where applicable (Modus Ponens, Contraposition, etc.).
4. End with a clear statement confirming the answer.
5. Keep it under 4 sentences.

Explanation:"""

# ══════════════════════════════════════════════════════════════
# Chain-of-Thought Reasoning (Fallback when Z3 fails)
# ══════════════════════════════════════════════════════════════

COT_MCQ_PROMPT = """Solve this logical reasoning problem step-by-step.

PREMISES:
{premises_nl}

PREMISES (Formal Logic):
{premises_fol}

{hints}

QUESTION:
{question}

---
FEW-SHOT EXAMPLE 1 (Contraposition):
PREMISES:
  1. If a project is optimized, then it is fast.
  2. The project is not fast.
QUESTION: Which of the following logically follows from the premises?
  A. The project is not optimized.
  B. The project is optimized.
  C. The project is slow.
STEP-BY-STEP REASONING:
  - Fact: "The project is not fast" (~Fast) from Premise 2.
  - Rule: "If optimized, then fast" (Optimized -> Fast) from Premise 1.
  - Contrapositive: (~Fast -> ~Optimized). Applying with our fact: ~Optimized.
  - This matches Option A. (Uses 2 premises)
ANSWER: A

FEW-SHOT EXAMPLE 2 (Fewest Premises):
PREMISES:
  1. If it rains, the ground is wet. (Rain -> Wet)
  2. If the ground is wet, plants grow. (Wet -> Grow)
  3. It is raining.
QUESTION: Which conclusion follows with the fewest premises?
  A. The ground is wet.
  B. Plants grow.
STEP-BY-STEP REASONING:
  - The question asks for the option using the FEWEST premises.
  - Option A: Rain -> Wet (Premise 1) + It rains (Premise 3) = 2 premises.
  - Option B: Rain -> Wet -> Grow (Premises 1, 2) + It rains (Premise 3) = 3 premises.
  - Both are logically valid, but A uses fewer premises.
ANSWER: A

FEW-SHOT EXAMPLE 3 (Insufficient Information → Unknown):
PREMISES:
  1. If a student studies hard, they pass the exam.
  2. If a student passes the exam, they graduate.
QUESTION: Which statement is correct?
  A. All students graduate.
  B. Some students study hard.
  C. If a student studies hard, they graduate.
STEP-BY-STEP REASONING:
  - Option A: We only know "IF studies hard THEN pass THEN graduate", but there are NO ground facts (no specific student is mentioned). We CANNOT conclude "all students graduate" without knowing who studies hard. NOT derivable.
  - Option B: No premise states any student actually studies hard. NOT derivable.
  - Option C: By Hypothetical Syllogism: studies_hard -> pass (P1) and pass -> graduate (P2), so studies_hard -> graduate. This is VALID.
  - WAIT: Option C is valid. But if the question has NO concrete ground facts and the rules are only conditional (if-then), we must check if ANY option is provably true. If none of the options can be proven true or false from the premises alone, answer Unknown.
  - Here, Option C IS derivable. So the answer is C.
  - NOTE: If NONE of the options were derivable, the answer would be "Unknown".
ANSWER: C
---

STEP-BY-STEP REASONING:
1. Identify the known facts (premises without conditions) and any given HINTS.
2. Identify the rules (if-then statements) and actively apply Contraposition (If P -> Q, then ~Q -> ~P).
3. Apply rules to facts using Modus Ponens to derive new conclusions.
   - WARNING: When applying a rule, you MUST explicitly check that ALL conditions in the "if" part are met.
   - WARNING: If a condition is negated in the facts (e.g., "John has not received X"), the rule CANNOT be applied! Do not hallucinate missing conditions.
4. Evaluate each answer option against your derived facts. For EACH valid option, note HOW MANY premises are needed.
5. CAREFULLY READ THE QUESTION. Apply the specific criterion it asks for:
   - "fewest premises" -> pick the valid option that uses the LEAST number of premises.
   - "strongest conclusion" -> pick the most specific/powerful valid conclusion.
   - "correct conclusion" or "logically follows" -> pick any valid option.
   - If a contrapositive uses only 1 original premise, it counts as 1 premise.
6. If multiple options are valid AND the question does NOT specify a selection criterion, choose the strongest one.
7. CRITICAL: If NO option can be logically derived from the premises (all are unsupported assumptions), answer "Unknown".
   - An option that only restates a conditional rule (if-then) WITHOUT a matching ground fact is NOT provable.
   - If the premises contain NO ground facts (only rules), and all options require ground facts, answer "Unknown".

You MUST output your final answer in EXACTLY this format on the last line:
ANSWER: [A, B, C, D, or Unknown]"""

COT_YESNO_PROMPT = """Determine whether the following statement logically follows from the premises.

PREMISES:
{premises_nl}

PREMISES (Formal Logic):
{premises_fol}

{hints}

STATEMENT TO VERIFY:
{question}

---
FEW-SHOT EXAMPLE (Broken Chain → No):
PREMISES:
  1. If a student studies, they understand the material.
  2. If a student understands the material, they pass the exam.
  3. If a student passes the exam, they graduate.
STATEMENT: There exists a complete pathway from studying to getting a job.
STEP-BY-STEP REASONING:
  1. studies -> understands (Premise 1) ✓
  2. understands -> passes_exam (Premise 2) ✓
  3. passes_exam -> graduates (Premise 3) ✓
  4. graduates -> gets_a_job ← NO SUCH PREMISE EXISTS! Chain is BROKEN.
  Since the chain from studying to getting a job is INCOMPLETE (missing the last link), the statement is NOT supported.
ANSWER: No

FEW-SHOT EXAMPLE (Insufficient Information → Unknown):
PREMISES:
  1. If it rains, the ground is wet.
  2. If the ground is wet, flowers bloom.
STATEMENT: The flowers are blooming.
STEP-BY-STEP REASONING:
  1. We have rules: rain -> wet (P1), wet -> bloom (P2).
  2. But there is NO fact stating "it rains" or "the ground is wet".
  3. Without a ground fact to trigger the chain, we CANNOT determine if flowers bloom.
  4. The statement is neither provably true nor provably false.
ANSWER: Unknown
---

STEP-BY-STEP REASONING:
1. Identify which premises are relevant.
2. Break down the STATEMENT TO VERIFY into its required conditions.
3. For EACH required condition, check if it is EXPLICITLY stated or logically derived from the premises.
   - WARNING: You CANNOT assume any missing conditions (e.g., if a rule requires 'field is X' but the field is not stated, the condition FAILS).
   - WARNING: You CANNOT assume common sense relations not explicitly stated in the premises.
4. CRITICAL — Chain Completeness Check & Universal Rules:
   - If the statement claims a "pathway", "chain", "causal chain", or "leads to" relationship, you MUST verify EVERY SINGLE LINK in the chain has an explicit premise.
   - List each link as: A -> B (Premise N) ✓ or A -> B ← MISSING ✗
   - If ANY link is missing, the chain is BROKEN and the answer is "No".
   - IMPORTANT: Do not overly second-guess universal rules (∀x). If a premise states a rule for "All students" or "All subjects" (e.g., ∀x P(x)), treat it as a valid ground fact for any specific instance. You do not need to explicitly prove that a specific instance exists if the premise universally applies to all of them.
5. Decision rules:
   - If ALL required conditions are provably met → "Yes".
   - If ANY condition is missing, unstated, or contradicted → "No".
   - If the premises contain NO ground facts and the statement requires specific instances (not just conditional rules), answer "Unknown".

You MUST output your final answer in EXACTLY this format on the last line:
ANSWER: [Yes, No, or Unknown]"""

# ══════════════════════════════════════════════════════════════
# Z3 Code Generation Prompt
# ══════════════════════════════════════════════════════════════

Z3_CODE_GENERATION_PROMPT = """Convert the following logical premises and question into Z3 Python code.

PREMISES (First-Order Logic):
{premises_fol}

PREMISES (Natural Language):
{premises_nl}

QUESTION: {question}

Generate a complete, executable Python script using the z3 library that:
1. Declare an Entity sort: Entity = DeclareSort('Entity')
2. Declare a variable x: x = Const('x', Entity)
3. Declare ALL predicates as Function objects (e.g., WT = Function('WT', Entity, BoolSort()))
4. If any named entities exist (e.g., John, Sophia), declare them: John = Const('John', Entity)
5. Assert all premises into a Solver()
6. For Yes/No questions: check entailment with Not(statement), if unsat print("Yes"), else print("No")
7. For MCQ (A, B, C, D): you MUST check ALL FOUR options separately using push/pop. Print the letter of the FIRST entailed option.
8. Prints EXACTLY one line of output.

IMPORTANT RULES:
- Output ONLY raw Python code. No markdown, no explanations.
- CRITICAL: NEVER use the '->' symbol for implication. You MUST use the Z3 function Implies(A, B).
- CRITICAL: You MUST declare ALL Entity constants and Boolean Functions (predicates) before using them in s.add().
- For MCQ options: translate each option into a ForAll expression, then check if Not(ForAll(...)) is unsat.
- You MUST check ALL options A, B, C, D. Do NOT stop after checking only one.
- Carefully match predicates: read each option's natural language and use the CORRECT predicate names.

EXAMPLE 1 (YES/NO):
PREMISES (First-Order Logic):
1. ForAll(x, WT(x) -> GR(x))
2. WT(John)

QUESTION: Yes or No: Is it true that John is GR?
CODE:
from z3 import *
s = Solver()
Entity = DeclareSort('Entity')
x = Const('x', Entity)
WT = Function('WT', Entity, BoolSort())
GR = Function('GR', Entity, BoolSort())
John = Const('John', Entity)

s.add(ForAll([x], Implies(WT(x), GR(x))))
s.add(WT(John))

s.push()
s.add(Not(ForAll([x], GR(John))))
print("Yes" if s.check() == unsat else "No")
s.pop()

EXAMPLE 2 (MCQ):
PREMISES (First-Order Logic):
1. ForAll(x, A(x) -> B(x))
2. ForAll(x, B(x) -> C(x))
3. A(John)

QUESTION: Based on the premises, which is true?
A. C(John)
B. Not(B(John))
C. Not(A(John))
D. None of the above

CODE:
from z3 import *
s = Solver()
Entity = DeclareSort('Entity')
x = Const('x', Entity)
A = Function('A', Entity, BoolSort())
B = Function('B', Entity, BoolSort())
C = Function('C', Entity, BoolSort())
John = Const('John', Entity)

s.add(ForAll([x], Implies(A(x), B(x))))
s.add(ForAll([x], Implies(B(x), C(x))))
s.add(A(John))

results = []
s.push(); s.add(Not(ForAll([x], C(John)))); results.append(('A', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], Not(B(John))))); results.append(('B', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], Not(A(John))))); results.append(('C', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], And(Not(C(John)), B(John), A(John))))); results.append(('D', s.check())); s.pop()

entailed = [r[0] for r in results if r[1] == unsat]
if entailed: print(entailed[0])
"""

# ══════════════════════════════════════════════════════════════
# Z3 Refinement Prompt
# ══════════════════════════════════════════════════════════════

Z3_REFINEMENT_PROMPT = """The previous Z3 code produced an error or no output. Fix it.

PREVIOUS CODE:
{previous_code}

ERROR/ISSUE:
{error_message}

ORIGINAL PREMISES (FOL):
{premises_fol}

COMMON MISTAKES TO FIX:
1. Named entities (John, Sophia, etc.) and ALL functions MUST be declared: John = Const('John', Entity)
2. NEVER use '->' for implication. Python Z3 does NOT support it. Use Implies(A, B).
3. For MCQ: you MUST check ALL 4 options (A, B, C, D) with push/pop, not just one.
4. Each option check must use ForAll: s.add(Not(ForAll([x], option_expr)))
5. Ensure predicate names exactly match the FOL premises.
6. Use Not() instead of NOT() - Python z3 uses Not, And, Or, Implies.

Output ONLY the corrected Python code. No markdown, no explanations.
"""

# ══════════════════════════════════════════════════════════════
# Track 2 — Physics Prompts
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_PHYSICS = (
    "You are a physics problem solver. "
    "Extract variables precisely from problem text. "
    "Use standard SI symbol notation (V, I, R, P, E, C, Q, F, f, L, B, Z, X_L, X_C, "
    "EMF, cos_phi, Phi, n). "
    "Return only valid JSON. No explanation outside JSON."
)

PHYSICS_PARSE_PROMPT = """Extract structured data from a physics problem as JSON.

Return ONLY a JSON object with this exact structure:
{{
    "given": {{"symbol": numeric_value}},
    "find": "symbol_to_solve",
    "domain": "one of: circuits | ac_circuits | electrostatics | electromagnetism | measurement",
    "formulas": ["formula_string"],
    "units": {{"symbol": "unit_string"}}
}}

Rules:
- Convert all values to base SI units (kΩ → multiply by 1000, mA → divide by 1000, μF → ×1e-6)
- Standard symbols: V (voltage), I (current), R (resistance), P (power), E (energy), C (capacitance), Q (charge), F (force), f (frequency), L (inductance), Z (impedance), X_L (inductive reactance), X_C (capacitive reactance), EMF (electromotive force), cos_phi (power factor), B (magnetic field), Phi (magnetic flux)
- "find" must be a single symbol string
- "formulas" are SymPy-compatible hints only (e.g. "V = I * R")
- Pick "domain" by the dominant topic:
  - "circuits": DC resistor networks — Ohm's law, series/parallel R, KVL/KCL (no AC)
  - "ac_circuits": AC RLC — impedance Z, reactance X_L/X_C, power factor cosφ, resonance
  - "electrostatics": point charges, Coulomb force, electric field, capacitor charge/energy
  - "electromagnetism": solenoid magnetic field, magnetic flux, induced EMF, self-inductance
  - "measurement": measurement error analysis — absolute/relative error, error propagation

Examples:

Problem: Calculate the energy stored in capacitor C when C = 100 μF and U = 30 V.
{{"given": {{"C": 0.0001, "U": 30}}, "find": "E", "domain": "electrostatics", "formulas": ["E = 0.5 * C * U**2"], "units": {{"C": "F", "U": "V"}}}}

Problem: An RLC series circuit has R = 100 Ω, L = 0.5 H, C = 50 μF at f = 50 Hz. Find the impedance Z.
{{"given": {{"R": 100, "L": 0.5, "C": 5e-05, "f": 50}}, "find": "Z", "domain": "ac_circuits", "formulas": ["Z = sqrt(R**2 + (X_L - X_C)**2)"], "units": {{"R": "Ω", "L": "H", "C": "F", "f": "Hz"}}}}

Problem: A solenoid with N = 1000 turns over length l = 0.5 m carries current I = 2 A. Calculate the magnetic field B inside.
{{"given": {{"N": 1000, "l": 0.5, "I": 2}}, "find": "B", "domain": "electromagnetism", "formulas": ["B = mu_0 * (N / l) * I"], "units": {{"l": "m", "I": "A"}}}}

Problem: A voltmeter with least count 0.2 V reads 5.6 V. Find the relative error.
{{"given": {{"least_count": 0.2, "x": 5.6}}, "find": "delta_rel", "domain": "measurement", "formulas": ["delta_rel = (least_count / 2) / x * 100"], "units": {{"x": "V"}}}}

Problem: Two point charges q1 = 6 × 10^-8 C and q2 = -6 × 10^-8 C are placed 8 cm apart. Find the force between them.
{{"given": {{"q1": 6e-08, "q2": -6e-08, "r": 0.08}}, "find": "F", "domain": "electrostatics", "formulas": ["F = k * q1 * q2 / r**2"], "units": {{"q1": "C", "q2": "C", "r": "m"}}}}

Now extract for this problem:
Problem: {question}
JSON:"""

PHYSICS_PARSE_SIMPLE_PROMPT = """From this physics problem extract only 3 fields.

Problem: {question}

Return ONLY JSON: {{"given": {{}}, "find": "", "domain": "circuits | ac_circuits | electrostatics | electromagnetism | measurement"}}

JSON:"""

PHYSICS_EXPLANATION_PROMPT = """You are a physics tutor. Write a clear explanation for a student.

Question: {question}
Answer: {answer} {unit}
Solution steps:
{steps}

Write 2-3 sentences. Explain the physical meaning and which law/formula applies.
End with: "Therefore, the answer is {answer} {unit}."

Explanation:"""

# ══════════════════════════════════════════════════════════════
# Track 2 — Physics Chain-of-Thought Solver Prompt
# Dùng khi SymPy + vector_solver thất bại.
# LLM nhận bài toán, giá trị đã biết, và sinh lời giải từng bước.
# Cuối cùng phải xuất "ANSWER: <số> <đơn vị>" để dễ parse.
# ══════════════════════════════════════════════════════════════

PHYSICS_COT_PROMPT = """Solve this physics problem step by step. Show all calculations clearly.

Problem: {question}

Known values (SI units): {given_str}
Quantity to find: {find_str}
{formula_hint}

INSTRUCTIONS:
- Apply the relevant physics law or formula.
- Substitute known values and calculate.
- For numeric results: end your solution with exactly: ANSWER: <number> <unit>
  Example: ANSWER: 0.045 J   or   ANSWER: 2.4e-3 N
- For Yes/No results: end with: ANSWER: Yes  or  ANSWER: No
- For qualitative/text results: end with: ANSWER: <short text>

--- EXAMPLE 1 (numeric) ---
Problem: Capacitor C=100μF charged to U=30V. Calculate stored energy.
Known values (SI units): C=1e-4 F, U=30 V
Quantity to find: W (energy)
Step 1: Formula: W = (1/2) × C × U²
Step 2: W = 0.5 × 1e-4 × (30)² = 0.5 × 1e-4 × 900
Step 3: W = 0.045 J
ANSWER: 0.045 J

--- EXAMPLE 2 (Yes/No) ---
Problem: RLC circuit R=50Ω, L=0.5H, C=20μF, f=40Hz. Does resonance occur?
Known values (SI units): R=50 Ω, L=0.5 H, C=2e-5 F, f=40 Hz
Quantity to find: resonance condition
Step 1: Resonant frequency f₀ = 1 / (2π√(LC)) = 1 / (2π√(0.5 × 2e-5)) ≈ 50.3 Hz
Step 2: Given f=40 Hz ≠ f₀=50.3 Hz → no resonance
ANSWER: No

--- EXAMPLE 3 (Coulomb force) ---
Problem: Two charges q1=6×10⁻⁸C and q2=3×10⁻⁸C separated by r=3cm. Find force.
Known values (SI units): q1=6e-8 C, q2=3e-8 C, r=0.03 m, k=9e9
Quantity to find: F (Coulomb force)
Step 1: Formula: F = k × |q1| × |q2| / r²
Step 2: F = 9e9 × 6e-8 × 3e-8 / (0.03)²
Step 3: F = 9e9 × 1.8e-15 / 9e-4 = 1.62e-5 / 9e-4 = 0.018 N
ANSWER: 0.018 N
---

SOLUTION:"""


# ══════════════════════════════════════════════════════════════
# Answer Extraction Patterns
# ══════════════════════════════════════════════════════════════

ANSWER_EXTRACT_PATTERNS = [
    r'(?i)\**ANSWER:\**\s*\**([A-D])\**\b',
    r'(?i)\**ANSWER:\**\s*\**(Yes|No|Unknown)\**',
    r'(?i)(?:answer is|correct answer is|conclusion is)\s*[:\s]*\**([A-D])\**\b',
    r'(?i)(?:answer is|correct answer is)\s*[:\s]*\**(Yes|No|Unknown)\**',
    r'(?i)\b(Yes|No|Unknown)\s*[,.]?\s*$',
    r'^([A-D])\s*[.\)]',
]
