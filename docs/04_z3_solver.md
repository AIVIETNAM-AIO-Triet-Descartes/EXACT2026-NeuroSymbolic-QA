# ⚡ Z3 Solver Integration - Formal Verification Engine

> **Công cụ:** Z3 Theorem Prover (Microsoft Research)  
> **Nghiên cứu:** Logic-LM (Pan et al., 2023), LINC (Olausson et al., 2023)  
> **Mục đích:** Chứng minh/bác bỏ formal logic từ FOL premises

---

## 1. Tổng Quan Z3 Trong Pipeline

### 1.1 Vai Trò

```
Logic Tree (Stage 2) ──→ Z3 Solver (Stage 3) ──→ Answer + Proof
                              │
                         ┌────┴────┐
                         │         │
                    SAT/UNSAT   Error/Timeout
                         │         │
                    Use result  Fallback to LLM
```

Z3 đảm nhận **formal verification** - đảm bảo đáp án đúng logic 100%, không hallucinate.

### 1.2 Khi Nào Dùng Z3

| Trường hợp | Dùng Z3? | Lý do |
|:---|:---|:---|
| Yes/No question + FOL rõ ràng | ✅ Luôn dùng | Entailment check chính xác |
| MCQ + có thể formalize options | ✅ Ưu tiên | Check từng option |
| Arithmetic constraints (≥, ≤) | ✅ Cần thiết | Z3 ArithRef |
| Unknown detection | ✅ Quan trọng | Check cả prove & disprove |
| FOL quá phức tạp / ambiguous | ⚠️ Thử + fallback | Có thể parse fail |
| Open-ended questions | ❌ Dùng LLM | Z3 không generate NL |

---

## 2. FOL → Z3 Translation

### 2.1 Translation Rules

```python
# Mapping FOL constructs → Z3 Python API

# 1. Sort/Type declarations
Person = z3.DeclareSort('Person')
x = z3.Const('x', Person)

# 2. Predicate → Function returning Bool
completed_courses = z3.Function('completed_courses', Person, z3.BoolSort())
gpa_above_3_5 = z3.Function('gpa_above_3_5', Person, z3.BoolSort())

# 3. Constants (named entities)
John = z3.Const('John', Person)
Sophia = z3.Const('Sophia', Person)

# 4. ∀x (P(x) → Q(x))
z3.ForAll([x], z3.Implies(P(x), Q(x)))

# 5. ∃x (P(x))
z3.Exists([x], P(x))

# 6. ∀x (A(x) ∧ B(x) → C(x))
z3.ForAll([x], z3.Implies(z3.And(A(x), B(x)), C(x)))

# 7. ¬P(x)
z3.Not(P(x))

# 8. P(x) ∨ Q(x)
z3.Or(P(x), Q(x))

# 9. Arithmetic: clinical_hours(john, 600), h ≥ 500
hours = z3.Function('clinical_hours', Person, z3.IntSort())
# assert hours(John) == 600
# ForAll([x, h], Implies(And(hours(x) == h, h >= 500), advanced(x)))
```

### 2.2 Complete Translation Function

```python
# src/z3_translator.py

import z3
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Z3Context:
    """Holds all Z3 declarations for a problem."""
    solver: z3.Solver
    sorts: Dict[str, z3.SortRef]
    functions: Dict[str, z3.FuncDeclRef]
    constants: Dict[str, z3.ExprRef]
    variables: Dict[str, z3.ExprRef]
    assertions: List[z3.ExprRef]

class Z3Translator:
    """Translates normalized FOL to Z3 expressions."""
    
    def __init__(self):
        self.ctx = None
    
    def create_context(self, metadata: dict) -> Z3Context:
        """
        Từ metadata (predicates, variables, constants),
        tạo Z3 context với tất cả declarations.
        """
        solver = z3.Solver()
        solver.set("timeout", 30000)  # 30s timeout
        
        # Default sort
        Entity = z3.DeclareSort('Entity')
        sorts = {'Entity': Entity}
        
        # Create functions for each predicate
        functions = {}
        for pred_name, arity in metadata['predicates'].items():
            if arity == 1:
                functions[pred_name] = z3.Function(
                    pred_name, Entity, z3.BoolSort()
                )
            elif arity == 2:
                functions[pred_name] = z3.Function(
                    pred_name, Entity, Entity, z3.BoolSort()
                )
        
        # Create constants
        constants = {}
        for name in metadata['constants']:
            constants[name] = z3.Const(name, Entity)
        
        # Create variables
        variables = {}
        for name in metadata['variables']:
            variables[name] = z3.Const(name, Entity)
        
        return Z3Context(
            solver=solver,
            sorts=sorts,
            functions=functions,
            constants=constants,
            variables=variables,
            assertions=[]
        )
    
    def translate_premise(self, fol: str, ctx: Z3Context) -> z3.ExprRef:
        """
        Translate single FOL premise to Z3 expression.
        
        Strategy:
        1. Parse FOL string to AST
        2. Walk AST and build Z3 expression
        3. Handle special cases (arithmetic, nested quantifiers)
        """
        # This is the core translation - see patterns below
        pass
    
    def translate_all(self, premises_fol: List[str]) -> Z3Context:
        """Translate all premises and create solver context."""
        # Step 1: Analyze all premises for metadata
        metadata = self.analyze_premises(premises_fol)
        
        # Step 2: Create Z3 context
        ctx = self.create_context(metadata)
        
        # Step 3: Translate each premise
        for fol in premises_fol:
            try:
                expr = self.translate_premise(fol, ctx)
                ctx.solver.add(expr)
                ctx.assertions.append(expr)
            except Exception as e:
                # Log translation failure for LLM fallback
                ctx.translation_errors.append((fol, str(e)))
        
        return ctx
```

---

## 3. Entailment Checking Patterns

### 3.1 Pattern: Yes/No (Does X follow?)

```python
def check_entailment(ctx: Z3Context, conclusion: z3.ExprRef) -> str:
    """
    Check if premises entail conclusion.
    
    Method: Proof by contradiction
    - Add ¬conclusion to premises
    - If UNSAT → premises ∧ ¬conclusion is impossible → conclusion follows → "Yes"
    - If SAT → there exists a model where premises hold but conclusion doesn't → "No"
    - If UNKNOWN → Z3 can't decide → "Unknown"
    """
    ctx.solver.push()  # Save state
    ctx.solver.add(z3.Not(conclusion))
    
    result = ctx.solver.check()
    
    if result == z3.unsat:
        answer = "Yes"
        # Extract proof if available
        proof = ctx.solver.proof() if ctx.solver.proof() else None
    elif result == z3.sat:
        answer = "No"
        # Get counterexample
        model = ctx.solver.model()
    else:
        answer = "Unknown"
    
    ctx.solver.pop()  # Restore state
    return answer
```

### 3.2 Pattern: MCQ (Which option is correct?)

```python
def check_mcq(ctx: Z3Context, options: Dict[str, z3.ExprRef]) -> str:
    """
    Check which MCQ option is entailed by premises.
    
    Strategy:
    1. For each option, check entailment
    2. Exactly one should be entailed (normally)
    3. If multiple entailed → choose "strongest" (most specific)
    4. If none entailed → check for "Unknown" type question
    """
    results = {}
    
    for key, option_expr in options.items():
        ctx.solver.push()
        ctx.solver.add(z3.Not(option_expr))
        check = ctx.solver.check()
        ctx.solver.pop()
        
        results[key] = {
            'entailed': check == z3.unsat,
            'consistent': check == z3.sat,
            'unknown': check == z3.unknown
        }
    
    # Find entailed options
    entailed = [k for k, v in results.items() if v['entailed']]
    
    if len(entailed) == 1:
        return entailed[0]
    elif len(entailed) > 1:
        # Multiple valid → need premise counting (fewest premises)
        return select_by_premise_count(entailed, ctx)
    else:
        # None entailed → check for negative options or Unknown
        return handle_no_entailment(results, options)
```

### 3.3 Pattern: Unknown Detection

```python
def check_unknown(ctx: Z3Context, statement: z3.ExprRef) -> bool:
    """
    Detect if a statement is undetermined (neither provable nor disprovable).
    
    Logic:
    - Check: premises ⊢ statement? (entailment)
    - Check: premises ⊢ ¬statement? (refutation)
    - If neither → statement is "Unknown"
    """
    # Check if statement is entailed
    ctx.solver.push()
    ctx.solver.add(z3.Not(statement))
    entailed = ctx.solver.check() == z3.unsat
    ctx.solver.pop()
    
    # Check if negation is entailed
    ctx.solver.push()
    ctx.solver.add(statement)
    refuted = ctx.solver.check() == z3.unsat
    ctx.solver.pop()
    
    return not entailed and not refuted  # True = Unknown
```

---

## 4. Xử Lý Arithmetic Constraints

### 4.1 Numeric Predicates

```python
def handle_arithmetic_premise(fol: str, ctx: Z3Context):
    """
    Xử lý premises có so sánh số học.
    
    Ví dụ:
    - "clinical_hours(john, 600)" → IntFunction
    - "membership_duration(Alex) = 8" → IntConstraint
    - "ForAll(x, ForAll(h, (clinical_hours(x,h) ∧ h ≥ 500) → ...))"
    """
    # Detect numeric predicates
    if '≥' in fol or '>=' in fol or '≤' in fol or '<=' in fol:
        # Use IntSort instead of BoolSort
        # e.g., clinical_hours: Entity → Int
        pass
    
    # Detect numeric constants
    if re.search(r'\b\d+\b', fol):
        # Create Int constants
        pass
```

### 4.2 Comparison Operations

```python
# Z3 arithmetic examples for dataset patterns

# Pattern: "completed_courses(sarah) = 4"
completed_courses = z3.Function('completed_courses', Entity, z3.IntSort())
sarah = z3.Const('sarah', Entity)
solver.add(completed_courses(sarah) == 4)

# Pattern: "ForAll(x, (completed_courses(x) >= 5) → eligible(x))"
x = z3.Const('x', Entity)
eligible = z3.Function('eligible', Entity, z3.BoolSort())
solver.add(z3.ForAll([x], 
    z3.Implies(completed_courses(x) >= 5, eligible(x))
))

# Check: Is sarah eligible?
# → completed_courses(sarah) = 4 < 5 → NOT eligible → "No"
```

---

## 5. LLM-Assisted Z3 Translation

### 5.1 Khi Nào Cần LLM Hỗ Trợ

| Trường hợp | Giải pháp |
|:---|:---|
| FOL parser thất bại | LLM sinh Z3 Python code trực tiếp |
| Ambiguous predicate names | LLM resolve semantics |
| Complex nested quantifiers | LLM decompose |
| MCQ options (NL, chưa có FOL) | LLM translate NL → FOL |

### 5.2 LLM → Z3 Code Generation Prompt

```python
Z3_GENERATION_PROMPT = """
You are a formal logic expert. Convert the following FOL premises to Z3 Python code.

PREMISES (FOL):
{premises_fol}

PREMISES (Natural Language):
{premises_nl}

Generate complete Z3 Python code that:
1. Declares all sorts, functions, and constants
2. Asserts all premises
3. Checks if the following statement is entailed:
   {goal_statement}

Output ONLY valid Python code using z3 library. Example format:
```python
from z3 import *
Entity = DeclareSort('Entity')
...
solver = Solver()
solver.add(...)
# Check entailment
solver.add(Not(goal))
result = solver.check()
print("Yes" if result == unsat else "No" if result == sat else "Unknown")
```
"""
```

### 5.3 Self-Refinement Loop (Logic-LM Style)

```python
def z3_with_refinement(premises_fol, premises_nl, goal, 
                       llm, max_retries=3) -> dict:
    """
    Logic-LM Self-Refinement:
    1. LLM generates Z3 code
    2. Execute Z3 code
    3. If error → send error message back to LLM
    4. LLM corrects and regenerates
    5. Repeat until success or max_retries
    """
    for attempt in range(max_retries):
        # Step 1: Generate Z3 code
        if attempt == 0:
            z3_code = llm.generate(Z3_GENERATION_PROMPT.format(
                premises_fol=premises_fol,
                premises_nl=premises_nl,
                goal_statement=goal
            ))
        else:
            z3_code = llm.generate(REFINEMENT_PROMPT.format(
                previous_code=z3_code,
                error_message=error_msg,
                premises_fol=premises_fol
            ))
        
        # Step 2: Execute
        try:
            result = execute_z3_code(z3_code)
            return {
                'answer': result,
                'z3_code': z3_code,
                'attempts': attempt + 1,
                'method': 'z3_verified'
            }
        except Exception as e:
            error_msg = str(e)
            continue
    
    # Fallback to LLM-only reasoning
    return {'answer': None, 'method': 'z3_failed'}
```

---

## 6. Optimizations

### 6.1 Caching Z3 Contexts

```python
class Z3Cache:
    """Cache Z3 contexts cho premises giống nhau."""
    
    def __init__(self):
        self._cache = {}
    
    def get_or_create(self, premises_hash: str, 
                      premises_fol: List[str]) -> Z3Context:
        if premises_hash not in self._cache:
            self._cache[premises_hash] = self.translate_all(premises_fol)
        return self._cache[premises_hash]
```

### 6.2 Timeout Strategy

```python
def z3_with_timeout(solver, timeout_ms=30000):
    """
    Z3 timeout strategy:
    - Try 30s first
    - If timeout → simplify premises and retry
    - If still timeout → fallback to LLM
    """
    solver.set("timeout", timeout_ms)
    result = solver.check()
    
    if result == z3.unknown:
        # Try with simplified tactics
        goal = z3.Goal()
        goal.add(*solver.assertions())
        tactic = z3.Then('simplify', 'solve-eqs', 'smt')
        simplified = tactic(goal)
        # ... retry
    
    return result
```

### 6.3 Incremental Solving

```python
def incremental_check(ctx: Z3Context, questions: List[str]):
    """
    Cho 2 câu hỏi cùng premises, dùng incremental solving:
    - Push/Pop thay vì tạo solver mới
    - Tiết kiệm thời gian parse premises
    """
    for question in questions:
        ctx.solver.push()
        goal = translate_question(question)
        ctx.solver.add(z3.Not(goal))
        result = ctx.solver.check()
        ctx.solver.pop()
        yield result
```

---

## 7. SymPy Fallback

```python
def sympy_fallback(premises_fol: List[str], goal: str) -> Optional[str]:
    """
    Khi Z3 fail, dùng SymPy cho:
    - Pure propositional logic (no quantifiers)
    - Simple arithmetic
    
    SymPy advantages:
    - Simpler API
    - Better for propositional simplification
    - Can handle boolean algebra
    """
    from sympy.logic.boolalg import And, Or, Not, Implies
    from sympy import symbols, satisfiable
    
    # Create symbols for each predicate
    # Evaluate satisfiability
    pass
```
