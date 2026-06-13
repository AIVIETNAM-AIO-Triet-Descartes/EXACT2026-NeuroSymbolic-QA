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
FEW-SHOT EXAMPLE 1 (Contraposition — Fewest Premises):
PREMISES:
  [0] If a project is optimized, then it is fast. (Optimized(x) → Fast(x))
  [1] The project is not fast. (¬Fast(x))
QUESTION: Which conclusion follows with the fewest premises?
  A. The project is not optimized.
  B. The project is optimized.
  C. The project is slow.
STEP-BY-STEP REASONING:
  - The question asks for the option using the FEWEST premises.
  - Option A: Contrapositive of [0]: (~Fast → ~Optimized). Combined with [1] (~Fast): ~Optimized. VALID. Uses premises [0, 1].
  - Option B: Contradicts derived ~Optimized. INVALID.
  - Option C: "Slow" is never mentioned in premises. INVALID.
  - Only Option A is valid. It uses 2 premises.
PREMISES USED: [0, 1]
ANSWER: A

FEW-SHOT EXAMPLE 2 (Strongest Conclusion — Full Chain):
PREMISES:
  [0] If a student passes the exam, they are eligible for certification.
  [1] If eligible for certification and completes internship, they are certified.
  [2] If certified, they qualify for the job.
  [3] John passed the exam.
  [4] John completed the internship.
QUESTION: Based on the premises, which is the strongest conclusion?
  A. John is eligible for certification.
  B. John is certified.
  C. John qualifies for the job.
  D. John needs additional training.
STEP-BY-STEP REASONING:
  - The question asks for the STRONGEST conclusion — the final result of the complete chain.
  - From [3] (passed) + [0]: John is eligible. Uses [0, 3].
  - From eligible + [4] (internship) + [1]: John is certified. Uses [0, 1, 3, 4].
  - From certified + [2]: John qualifies for the job. Uses [0, 1, 2, 3, 4].
  - Options A, B, C are ALL valid, but C is the STRONGEST (final in chain, most premises).
  - Option D: No premise mentions training. INVALID.
PREMISES USED: [0, 1, 2, 3, 4]
ANSWER: C

FEW-SHOT EXAMPLE 3 (Eligibility ≠ Actuality — Missing Condition):
PREMISES:
  [0] If a member has valid ID and training, they can use equipment.
  [1] If a member can use equipment AND has a coach, they can book sessions.
  [2] If membership ≥ 6 months, they are eligible for a coach.
  [3] Alex has valid ID and training.
  [4] Alex has membership of 8 months.
QUESTION: Which statement is correct?
  A. Alex can use equipment but cannot book sessions without a coach.
  B. Alex can book sessions if assigned a coach.
STEP-BY-STEP REASONING:
  - From [3] + [0]: Alex can use equipment. ✓
  - From [4] + [2]: Alex is ELIGIBLE for a coach. ✓
  - ⚠️ CRITICAL: "eligible for a coach" ≠ "has a coach". No premise states Alex HAS a coach.
  - [1] requires "has a coach" (NOT "eligible for"). This condition is NOT met.
  - Option A: Correctly states Alex can use equipment but cannot book without a coach. VALID.
  - Option B: Says "if assigned a coach" — this is a conditional, not a proven fact. Weaker.
  - Option A directly reflects the provable state.
PREMISES USED: [0, 1, 3, 4]
ANSWER: A

FEW-SHOT EXAMPLE 4 (Insufficient Information → Unknown):
PREMISES:
  [0] If a student studies hard, they pass the exam.
  [1] If a student passes the exam, they graduate.
QUESTION: Which statement is correct?
  A. All students graduate.
  B. Some students study hard.
  C. If a student studies hard, they graduate.
STEP-BY-STEP REASONING:
  - Option A: No ground facts. CANNOT conclude "all students graduate". NOT derivable.
  - Option B: No premise states any student studies hard. NOT derivable.
  - Option C: By Hypothetical Syllogism: studies_hard → pass ([0]) + pass → graduate ([1]) = studies_hard → graduate. VALID.
  - NOTE: If NONE of the options were derivable, the answer would be "Unknown".
PREMISES USED: [0, 1]
ANSWER: C
---

STEP-BY-STEP REASONING:
1. Identify the known FACTS (premises without conditions) and any given HINTS.
2. Identify the RULES (if-then statements) and actively apply Contraposition (If P → Q, then ¬Q → ¬P).
3. Apply rules to facts using Modus Ponens to derive new conclusions.
   - ⚠️ CRITICAL: When applying a rule, you MUST explicitly verify that ALL conditions in the "if" part are ACTUALLY SATISFIED (not just "eligible" or "qualified").
   - ⚠️ CRITICAL: "Eligible for X" ≠ "Has X". "Qualified for X" ≠ "Received X". Do NOT confuse potential with actuality.
   - ⚠️ CRITICAL: If a condition is negated in the facts (e.g., "has NOT received X"), the rule CANNOT fire.
   - ⚠️ CRITICAL: NEVER affirm the consequent. If P → Q and Q is true, you CANNOT conclude P is true.
   - ⚠️ COREFERENCE RULE: If a premise uses a pronoun (e.g. "She", "He", "It", "They", "This project") referring to an entity in another premise, you MUST include BOTH the referring premise and the referent-defining premise in PREMISES USED.
4. For EACH answer option, write out:
   - The logical derivation path (which premises are needed).
   - The total COUNT of premises used.
   - Whether the option is VALID (derivable) or INVALID (not derivable).
   - ⚠️ NO EXTRAPOLATIONS: If an option contains claims that go BEYOND what the premises prove (e.g., "permanent base" when premises only prove "breakthrough"), it is INVALID.
5. CAREFULLY READ THE QUESTION and apply the specific criterion:
   - "fewest premises" → pick the valid option with the MINIMUM premise count.
   - "strongest conclusion" → pick the valid option at the END of the logical chain (uses the MOST premises).
   - "correct conclusion" / "logically follows" / "logically valid" → pick any valid option.
   - If a contrapositive of a single rule (¬Q → ¬P from P → Q) is applied, it counts as using only 1 premise (the rule itself).
6. DISJUNCTIVE PATH CHECK: If there are multiple rules that can derive the same goal (A∧B→G OR A∧C→G), check EACH path independently. If ANY path is fully satisfied, the goal is provable.
7. If multiple options are valid AND the question does NOT specify a selection criterion, choose the strongest one.
8. If NO option can be logically derived from the premises, answer "Unknown".

You MUST output the 0-based indices of the premises you actually used to derive the answer (first premise is index 0, second premise is index 1, etc.) and your final answer in EXACTLY this format on the last two lines:
PREMISES USED: [comma-separated 0-based indices, e.g., [0, 2] or [] if answer is Unknown]
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
FEW-SHOT EXAMPLE 1 (Complete Chain → Yes):
PREMISES:
  [0] If a student completes courses, they are eligible for graduation.
  [1] If eligible for graduation and submits thesis, they graduate.
  [2] Alice completed all courses.
  [3] Alice submitted her thesis.
STATEMENT: Does Alice graduate?
STEP-BY-STEP REASONING:
  1. From [2] (completed courses) + [0]: Alice is eligible. ✓
  2. From eligible + [3] (thesis) + [1]: Alice graduates. ✓
  All conditions are met.
PREMISES USED: [0, 1, 2, 3]
ANSWER: Yes

FEW-SHOT EXAMPLE 2 (Missing Condition → No):
PREMISES:
  [0] If a member can use equipment AND has a coach, they can book sessions.
  [1] If membership ≥ 6 months, they are eligible for a coach.
  [2] Bob can use equipment.
  [3] Bob has membership of 8 months.
STATEMENT: Does Bob meet all requirements for booking sessions?
STEP-BY-STEP REASONING:
  1. From [3] + [1]: Bob is ELIGIBLE for a coach. ✓
  2. ⚠️ CRITICAL: "eligible for a coach" ≠ "has a coach". No premise states Bob HAS a coach.
  3. [0] requires "has a coach" — this condition is NOT met.
  4. Bob can use equipment ([2]) but does NOT have a coach → cannot book sessions.
PREMISES USED: [0, 1, 2, 3]
ANSWER: No

FEW-SHOT EXAMPLE 3 (Broken Chain → No):
PREMISES:
  [0] If a student studies, they understand the material.
  [1] If a student understands the material, they pass the exam.
  [2] If a student passes the exam, they graduate.
STATEMENT: There exists a complete pathway from studying to getting a job.
STEP-BY-STEP REASONING:
  1. studies → understands ([0]) ✓
  2. understands → passes_exam ([1]) ✓
  3. passes_exam → graduates ([2]) ✓
  4. graduates → gets_a_job ← NO SUCH PREMISE EXISTS! Chain is BROKEN.
PREMISES USED: [0, 1, 2]
ANSWER: No

FEW-SHOT EXAMPLE 4 (Insufficient Information → Unknown):
PREMISES:
  [0] If it rains, the ground is wet.
  [1] If the ground is wet, flowers bloom.
STATEMENT: The flowers are blooming.
STEP-BY-STEP REASONING:
  1. Rules: rain → wet ([0]), wet → bloom ([1]).
  2. No fact states "it rains" or "the ground is wet".
  3. Without a ground fact, CANNOT determine if flowers bloom.
PREMISES USED: []
ANSWER: Unknown

FEW-SHOT EXAMPLE 5 (Disjunctive Paths — Alternative Satisfied → Yes):
PREMISES:
  [0] If a student has an honors diploma and completes community service, they qualify for a scholarship.
  [1] If a student has an honors diploma and receives a faculty recommendation, they qualify for a scholarship.
  [2] Alice has an honors diploma.
  [3] Alice completed community service.
STATEMENT: Does Alice qualify for a scholarship?
STEP-BY-STEP REASONING:
  1. Rule Path A: honors_diploma ∧ community_service → scholarship ([0]).
  2. Rule Path B: honors_diploma ∧ faculty_recommendation → scholarship ([1]).
  3. From [2]: Alice has honors diploma. ✓
  4. From [3]: Alice completed community service. ✓
  5. Path A: honors_diploma ([2]) ∧ community_service ([3]) → scholarship ([0]). ALL conditions met. ✓
  6. ⚠️ Path B requires faculty_recommendation — not stated. But Path A is FULLY SATISFIED.
  7. Since ANY one valid path is enough, Alice qualifies for a scholarship.
PREMISES USED: [0, 2, 3]
ANSWER: Yes
---

STEP-BY-STEP REASONING:
1. Identify which premises are relevant to the statement.
2. Break down the STATEMENT into its required conditions.
3. For EACH required condition, check if it is EXPLICITLY stated or logically derived.
   - ⚠️ CRITICAL: "Eligible for X" ≠ "Has X". "Qualified for X" ≠ "Received X". Never confuse potential with actuality.
   - ⚠️ CRITICAL: You CANNOT assume any missing conditions.
   - ⚠️ CRITICAL: NEVER affirm the consequent. If P → Q and Q is true, you CANNOT conclude P is true.
   - ⚠️ CRITICAL: NEVER deny the antecedent. If P → Q and P is false, you CANNOT conclude Q is false.
   - ⚠️ COREFERENCE RULE: If a premise uses a pronoun (e.g. "She", "He", "It", "They", "This project") referring to an entity in another premise, you MUST include BOTH the referring premise and the referent-defining premise in PREMISES USED.
   - ⚠️ CRITICAL: A universal rule ∀x(P(x) → Q(x)) combined with a universal fact ∀x P(x) yields ∀x Q(x) — this applies to ALL individuals.
4. Chain Completeness Check:
   - List each link: A → B (Premise N) ✓ or A → B ← MISSING ✗
   - If ANY link is missing, the answer is "No".
   - IMPORTANT: Universal rules (∀x) apply to all instances; do not require separate existence proofs.
5. DISJUNCTIVE PATH CHECK: If there are multiple rules that can derive the same goal (A∧B→G OR A∧C→G), check EACH path independently. If ANY path is fully satisfied, the statement is provable → "Yes".
6. Decision:
   - ALL conditions provably met → "Yes".
   - ANY condition missing, unstated, or contradicted → "No".
   - No ground facts and statement requires instances → "Unknown".

You MUST output the 0-based indices of the premises you actually used to derive the answer (first premise is index 0, second premise is index 1, etc.) and your final answer in EXACTLY this format on the last two lines:
PREMISES USED: [comma-separated 0-based indices, e.g., [0, 2] or [] if answer is Unknown]
ANSWER: [Yes, No, or Unknown]"""

# ══════════════════════════════════════════════════════════════
# Chain-of-Thought for Open-Ended / Numeric / Text Questions
# ══════════════════════════════════════════════════════════════

COT_OPEN_PROMPT = """Answer this question using ONLY the given premises. The answer may be a name, number, list, or short phrase.

PREMISES:
{premises_nl}

PREMISES (Formal Logic):
{premises_fol}

{hints}

QUESTION:
{question}

---
FEW-SHOT EXAMPLE 1 (Direct Fact Retrieval — Number):
PREMISES:
  [0] If a student passes the exam, they graduate.
  [1] The class has 30 students.
QUESTION: How many students are in the class?
STEP-BY-STEP REASONING:
  - [1] directly states the class has 30 students. No derivation needed.
PREMISES USED: [1]
ANSWER: 30

FEW-SHOT EXAMPLE 2 (Derivation — Name):
PREMISES:
  [0] If a researcher has a grant and publishes a paper, they are promoted.
  [1] Dr. Lee has a grant.
  [2] Dr. Lee published a paper.
QUESTION: Which researcher is promoted?
STEP-BY-STEP REASONING:
  - From [1] (grant) + [2] (paper) + [0]: Dr. Lee is promoted.
PREMISES USED: [0, 1, 2]
ANSWER: Dr. Lee

FEW-SHOT EXAMPLE 3 (No Information → Unknown):
PREMISES:
  [0] All birds can fly.
  [1] Penguins are birds.
QUESTION: How fast can a penguin fly?
STEP-BY-STEP REASONING:
  - From [1] + [0]: Penguins can fly.
  - But no premise states speed. Cannot determine.
PREMISES USED: []
ANSWER: Unknown
---

STEP-BY-STEP REASONING:
1. Identify which premises are directly relevant to the question.
2. If the answer is DIRECTLY STATED in a premise (a fact), extract it immediately.
3. If the answer requires derivation or arithmetic calculations (e.g. addition, subtraction, division, set intersection, logical math), write out each mathematical step and calculation explicitly.
4. ⚠️ COREFERENCE RULE: If a premise uses a pronoun (e.g. "She", "He", "It", "They", "This project") referring to an entity in another premise, you MUST include BOTH the referring premise and the referent-defining premise in PREMISES USED.
5. Output the specific name, number, or phrase. If not derivable, output "Unknown".

You MUST write out the 'STEP-BY-STEP REASONING:' section first, and then output the 0-based indices of the premises you used and your final answer in EXACTLY this format on the last two lines:
PREMISES USED: [comma-separated 0-based indices, e.g., [0, 2] or [] if answer is Unknown]
ANSWER: [the specific name, number, phrase, or Unknown]"""

# ══════════════════════════════════════════════════════════════
# Z3 Code Generation Prompt
# ══════════════════════════════════════════════════════════════

Z3_CODE_GENERATION_PROMPT = """Convert the following logical premises and question into Z3 Python code.

PREMISES (First-Order Logic):
{premises_fol}

PREMISES (Natural Language):
{premises_nl}

QUESTION: {question}

You are provided with a Python environment where the following are PRE-DEFINED and PRE-IMPORTED:
- 'from z3 import *' (all Z3 functions/classes are available)
- 'Entity = DeclareSort("Entity")' (default sort for all entities)
- 'x', 'y', 'z' = pre-declared Z3 Consts of sort Entity (use 'x' as default variable for ForAll/Exists)
- 'solve_yes_no(solver, goal)': checks if 'goal' is entailed (prints "Yes"), refuted (prints "No"), or undetermined (prints "Unknown")
- 'solve_mcq(solver, options_dict)': checks which option is entailed. 'options_dict' maps option keys (e.g. 'A', 'B') to Z3 expressions. For 'None of the above' options, map the option key to None. Prints the correct option letter.

Generate a complete Python script that:
1. Declares ALL predicates as Function objects returning BoolSort() or IntSort() (e.g., WT = Function('WT', Entity, BoolSort())).
   - CRITICAL: If a predicate is numeric (e.g. gpa, grade, completed_courses, hours, age), declare it returning IntSort() or RealSort(), e.g. completed_courses = Function('completed_courses', Entity, IntSort()).
   - CRITICAL: The Python variable name for each predicate MUST match the predicate name exactly. For example, if a predicate is 'mentor', you must declare it as 'mentor = Function("mentor", ...)' (NOT 'GR = Function("mentor", ...)' or any other name).
2. Declares any named entities as Const objects of sort Entity (e.g., John = Const('John', Entity)).
   - CRITICAL: The Python variable name for each constant MUST match the constant name exactly. For example, if a constant is 'Dr_John', declare 'Dr_John = Const("Dr_John", Entity)' (NOT 'John = Const("Dr_John", Entity)').
3. Creates a solver: s = Solver()
4. Asserts all FOL premises into the solver.
   - For universal implication (ForAll(x, P(x) -> Q(x))), write: s.add(ForAll([x], Implies(P(x), Q(x))))
   - For atomic facts (P(John)), write: s.add(P(John))
   - For negated facts (~P(John)), write: s.add(Not(P(John)))
   - For numeric comparisons (completed_courses(Sarah) = 4), write: s.add(completed_courses(Sarah) == 4)
   - For numeric implications (completed_courses(x) >= 5 -> eligible(x)), write: s.add(ForAll([x], Implies(completed_courses(x) >= 5, eligible(x))))
5. Calls the helper function:
   - For Yes/No questions: solve_yes_no(s, goal_expr)
   - For MCQ: solve_mcq(s, {{'A': expr_A, 'B': expr_B, 'C': expr_C, 'D': expr_D}}) (or matching choices)

IMPORTANT RULES:
- Output ONLY raw Python code. No markdown, no explanations, no backticks.
- NEVER redeclare Entity, x, y, z. Use them directly.
- NEVER use '->' for implication. You MUST use Implies(A, B).
- NEVER use print("Yes" if s.check()...) yourself. ALWAYS use solve_yes_no(s, goal_expr) or solve_mcq(s, options_dict).
- DO NOT use variable names or placeholders from the examples (such as WT, GR, completed_courses, eligible, Alice, John) unless they are explicitly present in the question. Always match your Python variable/function names exactly to the predicate and constant names from the premises.

EXAMPLE 1 (YES/NO):
PREMISES (First-Order Logic):
1. ForAll(x, WT(x) -> GR(x))
2. WT(John)
QUESTION: Yes or No: Is it true that John is GR?
CODE:
from z3 import *
s = Solver()
WT = Function('WT', Entity, BoolSort())
GR = Function('GR', Entity, BoolSort())
John = Const('John', Entity)

s.add(ForAll([x], Implies(WT(x), GR(x))))
s.add(WT(John))

solve_yes_no(s, GR(John))

EXAMPLE 2 (MCQ with Arithmetic):
PREMISES (First-Order Logic):
1. ForAll(x, completed_courses(x) >= 5 -> eligible(x))
2. completed_courses(Alice) = 4
QUESTION: Which statement is true?
A. eligible(Alice)
B. Not(eligible(Alice))
C. None of the above
CODE:
from z3 import *
s = Solver()
completed_courses = Function('completed_courses', Entity, IntSort())
eligible = Function('eligible', Entity, BoolSort())
Alice = Const('Alice', Entity)

s.add(ForAll([x], Implies(completed_courses(x) >= 5, eligible(x))))
s.add(completed_courses(Alice) == 4)

solve_mcq(s, {{
    'A': eligible(Alice),
    'B': Not(eligible(Alice)),
    'C': None
}})
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

REMEMBER PRE-DEFINED FUNCTIONS & VARIABLES:
- Entity, x, y, z are already declared. DO NOT redeclare them.
- Use solve_yes_no(solver, goal) for Yes/No questions.
- Use solve_mcq(solver, options_dict) for MCQ questions. Map 'None of the above' options to None.
- Declare numeric predicates (like GPA, grade, clinical_hours, completed_courses) returning IntSort() or RealSort().
- Use '==' for equality comparison, and z3 functions like Not(), Implies(), And(), Or().

Output ONLY the corrected raw Python code. No markdown, no explanations.
"""

# ══════════════════════════════════════════════════════════════
# Answer Extraction Patterns
# ══════════════════════════════════════════════════════════════

ANSWER_EXTRACT_PATTERNS = [
    r'(?i)\**ANSWER:\**\s*\**([A-D])\**\b',
    r'(?i)\**ANSWER:\**\s*\**(Yes|No|Unknown|Uncertain)\**',
    r'(?i)(?:answer is|correct answer is|conclusion is)\s*[:\s]*\**([A-D])\**\b',
    r'(?i)(?:answer is|correct answer is|conclusion is)\s*[:\s]*\**(Yes|No|Unknown|Uncertain)\**',
    r'(?i)\b(Yes|No|Unknown|Uncertain)\s*[,.]?\s*$',
    r'^([A-D])\s*[.\)]',
]


# ══════════════════════════════════════════════════════════════
# Track 2 — Physics prompts (used by LLMReasoner physics methods)
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_PHYSICS = (
    "You are a careful physics assistant. You extract data and reason step by "
    "step, but you NEVER guess numbers — you report exactly what the problem "
    "states. Keep symbol conventions: U = potential difference (voltage), "
    "V = electric potential, Z_L = inductive reactance, Z_C = capacitive "
    "reactance, Z = impedance."
)

# Extraction → strict JSON (parsed with json.loads, never eval).
PHYSICS_PARSE_PROMPT = """Extract the structured data from this physics problem.

Problem:
{question}

Return ONLY a JSON object (no prose, no code fences) with this exact shape:
{{"given": {{"<symbol>": <number in SI units>}}, "find": "<symbol to solve for>", "domain": "<one of: electrostatics, circuits, ac_circuits, electromagnetism, measurement>", "formulas": ["<relevant formula as 'LHS = RHS'>"]}}

Rules:
- "given" values MUST be plain numbers already converted to SI (e.g. "100 uF" -> 1e-4). If a value is an expression like sqrt(3)*1e-6, evaluate it to a float.
- Use the symbol convention: U=voltage, Z_L/Z_C/Z for reactance/impedance.
- Omit a key if unknown; never invent values not stated in the problem.

JSON:"""

# Chain-of-Thought numeric solver. Ends with a single machine-parseable line.
PHYSICS_COT_PROMPT = """Solve this physics problem step by step.

Problem:
{question}

Known values: {given}
Find: {find}
Candidate formulas: {formulas}

Work through the calculation explicitly. On the FINAL line, output exactly:
ANSWER: <number> <unit>
where <unit> is ASCII (ohm, uF, nC, V/m, A, W, J, ...) and <number> is the numeric value only.

Solution:"""

# PAL (Program-Aided) solver: the LLM WRITES Python (sympy/math) instead of doing
# arithmetic itself — the sandbox executes it, eliminating arithmetic hallucination
# (8B models pick formulas well but mis-compute floats / scientific notation).
PHYSICS_PAL_PROMPT = """Write Python code to solve this physics problem. Do NOT compute the numbers yourself — the code will be executed to obtain the result.

Problem:
{question}

Known values (already in SI units): {given}
Find: {find}
Candidate formulas: {formulas}

Requirements:
- Use ONLY the `math` and `sympy` libraries (already importable). No file, network, or OS access.
- Assign the final numeric result to a variable named `answer` (a float, in SI base units).
- Report the POSITIVE magnitude for physical quantities (voltage, current, energy, force, field, power, resistance…) — use abs() — unless the problem explicitly asks for a sign or direction.
- Assign the ASCII unit string to a variable named `unit` (e.g. "A", "ohm", "V/m", "J"; "" if dimensionless).
- Keep the symbol convention: U=voltage, Z_L/Z_C/Z for inductive/capacitive reactance/impedance.
- Output ONLY one Python code block, no prose.

For MULTI-CHARGE force or ELECTRIC-FIELD problems, ALWAYS work in 2D coordinates — do NOT guess that the answer is zero by "symmetry" unless you have verified it with the component sums:
1. Read the geometry and place EVERY charge at an explicit (x, y) (triangle: (0,0),(a,0),(a/2, a*sqrt(3)/2); square; collinear: along x-axis; bisector point: (AB/2, d_perp)).
2. For the target (charge for a force, point for a field), sum contributions as VECTORS:
   - magnitude: force k*abs(qi*qt)/r**2 ; field k*abs(qi)/r**2
   - direction along the line source→target; LIKE signs push the target AWAY (use +unit vector), OPPOSITE signs pull it TOWARD the source (−unit vector).
   - accumulate fx += sign*mag*dx/r, fy += sign*mag*dy/r
3. answer = math.hypot(fx, fy).

Example (scalar):
```python
import sympy as sp
C, Q = 5e-6, 20e-6          # capacitance (F), charge (C)
answer = float(Q**2 / (2 * C))
unit = "J"
```

Example (vector — net force on q3 at a triangle vertex):
```python
import math
k = 9e9
a = 0.1
q1, q2, q3 = 1e-6, 1e-6, -2e-6
P = {{1: (0.0, 0.0), 2: (a, 0.0), 3: (a/2, a*math.sqrt(3)/2)}}   # vertex positions
fx = fy = 0.0
for i, qi in [(1, q1), (2, q2)]:
    dx, dy = P[3][0]-P[i][0], P[3][1]-P[i][1]
    r = math.hypot(dx, dy)
    mag = k*abs(qi*q3)/r**2
    sign = 1.0 if qi*q3 > 0 else -1.0     # like→away, opposite→toward
    fx += sign*mag*dx/r
    fy += sign*mag*dy/r
answer = math.hypot(fx, fy)
unit = "N"
```

Code:"""

# Self-repair: the previous PAL code failed (syntax / runtime / no `answer`).
# Feed the error back so the model fixes it — one retry before falling to CoT.
PHYSICS_PAL_REFINE_PROMPT = """Your previous Python code for this physics problem FAILED.
Error: {error}

Previous code:
```python
{code}
```

Problem:
{question}
Known values (SI): {given}
Find: {find}

Fix the bug (check imports, variable names, the geometry/coordinate setup, and that
`answer` is assigned a finite float). Output ONLY one corrected Python code block that
sets `answer` (float, SI) and `unit` (ASCII str). No prose.

Code:"""

# Short NL explanation for an already-solved problem.
PHYSICS_EXPLAIN_PROMPT = """Write a concise 2-3 sentence explanation for this solved physics problem.

Problem: {question}
Final answer: {answer} {unit}
Computation steps:
{steps}

Explain which physical principle / formula applies and how the steps reach the answer. Do not restate the full calculation; focus on the reasoning. Explanation:"""
