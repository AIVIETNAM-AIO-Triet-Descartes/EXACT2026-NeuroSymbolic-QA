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
---

STEP-BY-STEP REASONING:
1. Identify the known facts (premises without conditions) and any given HINTS.
2. Identify the rules (if-then statements) and actively apply Contraposition (If P -> Q, then ~Q -> ~P).
3. Apply rules to facts using Modus Ponens to derive new conclusions.
4. Evaluate each answer option against your derived facts. For EACH valid option, note HOW MANY premises are needed.
5. CAREFULLY READ THE QUESTION. Apply the specific criterion it asks for:
   - "fewest premises" -> pick the valid option that uses the LEAST number of premises.
   - "strongest conclusion" -> pick the most specific/powerful valid conclusion.
   - "correct conclusion" or "logically follows" -> pick any valid option.
   - If a contrapositive uses only 1 original premise, it counts as 1 premise.
6. If multiple options are valid AND the question does NOT specify a selection criterion, choose the strongest one.

You MUST output your final answer in EXACTLY this format on the last line:
ANSWER: [single letter A, B, C, or D]"""

COT_YESNO_PROMPT = """Determine whether the following statement logically follows from the premises.

PREMISES:
{premises_nl}

PREMISES (Formal Logic):
{premises_fol}

{hints}

STATEMENT TO VERIFY:
{question}

STEP-BY-STEP REASONING:
1. Identify which premises are relevant to the statement.
2. Try to derive the statement from the premises using logical rules.
3. If derivable → "Yes". If contradicted → "No". If insufficient information → "Unknown".

You MUST output your final answer in EXACTLY this format on the last line:
ANSWER: [Yes or No or Unknown]"""

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
- For MCQ options: translate each option into a ForAll expression, then check if Not(ForAll(...)) is unsat.
- You MUST check ALL options A, B, C, D. Do NOT stop after checking only one.
- Carefully match predicates: read each option's natural language and use the CORRECT predicate names.

SKELETON FOR YES/NO:
from z3 import *
s = Solver()
Entity = DeclareSort('Entity')
x = Const('x', Entity)
# Declare predicates...
# Add premises...
# Check: s.push(); s.add(Not(ForAll([x], statement))); print("Yes" if s.check() == unsat else "No"); s.pop()

SKELETON FOR MCQ:
from z3 import *
s = Solver()
Entity = DeclareSort('Entity')
x = Const('x', Entity)
# Declare predicates...
# Add premises...
# Check ALL options:
results = []
s.push(); s.add(Not(ForAll([x], option_A_expr))); results.append(('A', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], option_B_expr))); results.append(('B', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], option_C_expr))); results.append(('C', s.check())); s.pop()
s.push(); s.add(Not(ForAll([x], option_D_expr))); results.append(('D', s.check())); s.pop()
entailed = [r[0] for r in results if r[1] == unsat]
if entailed: print(entailed[0])
"""

Z3_REFINEMENT_PROMPT = """The previous Z3 code produced an error or no output. Fix it.

PREVIOUS CODE:
{previous_code}

ERROR/ISSUE:
{error_message}

ORIGINAL PREMISES (FOL):
{premises_fol}

COMMON MISTAKES TO FIX:
1. Named entities (John, Sophia, etc.) must be declared: John = Const('John', Entity)
2. For MCQ: you MUST check ALL 4 options (A, B, C, D) with push/pop, not just one.
3. Each option check must use ForAll: s.add(Not(ForAll([x], option_expr)))
4. Ensure predicate names exactly match the FOL premises.
5. Use Not() instead of NOT() - Python z3 uses Not, And, Or, Implies.

Output ONLY the corrected Python code. No markdown, no explanations.
"""

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
