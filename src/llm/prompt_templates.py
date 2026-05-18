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

QUESTION:
{question}

STEP-BY-STEP REASONING:
1. Identify the known facts (premises without conditions).
2. Identify the rules (if-then statements).
3. Apply rules to facts using Modus Ponens to derive new conclusions.
4. If a premise states NOT something, note which rules are blocked.
5. Evaluate each answer option against your derived facts.
6. Select the option that is logically supported.

You MUST output your final answer in EXACTLY this format on the last line:
ANSWER: [single letter A, B, C, or D]"""

COT_YESNO_PROMPT = """Determine whether the following statement logically follows from the premises.

PREMISES:
{premises_nl}

PREMISES (Formal Logic):
{premises_fol}

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
1. Declares an Entity sort
2. Declares all predicates as z3.Function objects
3. Declares all named entities as z3.Const objects
4. Asserts all premises into a z3.Solver()
5. For Yes/No questions: checks whether the question's statement is entailed (if Not(statement) is unsat, print("Yes"), else print("No") or print("Unknown"))
6. For Multiple Choice questions (A, B, C, D): evaluates each option to see which is logically entailed, and prints ONLY the correct letter (e.g., print("A"))
7. Prints EXACTLY one line of output.

IMPORTANT RULES:
- Use s = z3.Solver() to manage assertions
- Use z3.DeclareSort('Entity') for the entity sort
- Use z3.Function('name', Entity, BoolSort()) for unary predicates
- Use z3.ForAll([x], z3.Implies(...)) for universal rules
- Output ONLY the raw Python code, do not output any markdown formatting (like ```python) or explanations.

```python
from z3 import *
"""

Z3_REFINEMENT_PROMPT = """The previous Z3 code produced an error. Fix it.

PREVIOUS CODE:
{previous_code}

ERROR MESSAGE:
{error_message}

ORIGINAL PREMISES (FOL):
{premises_fol}

Fix the code and output ONLY the corrected Python code.

```python
from z3 import *
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
