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
4. CRITICAL — Chain Completeness Check:
   - If the statement claims a "pathway", "chain", "causal chain", or "leads to" relationship, you MUST verify EVERY SINGLE LINK in the chain has an explicit premise.
   - List each link as: A -> B (Premise N) ✓ or A -> B ← MISSING ✗
   - If ANY link is missing, the chain is BROKEN and the answer is "No".
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
