# 🔄 FOL Normalizer - Chuẩn Hóa Notation Logic

> **Mục đích:** Chuyển đổi mọi FOL notation trong dataset về một format chuẩn thống nhất phù hợp Z3 Solver  
> **Nghiên cứu tham khảo:** LINC (Olausson et al., 2023), LogicLLaMA (2024)

---

## 1. Vấn Đề Cần Giải Quyết

Dataset sử dụng **nhiều hệ notation FOL khác nhau:**

### 1.1 Unicode Style (2053 occurrences)
```
∀x (WT(x) → O(x))
∀x (¬PEP8(x) → ¬WT(x))
∃x (BP(x))
∀x (EM(x) → WT(x))
```

### 1.2 Text/Functional Style (1629 occurrences)
```
ForAll(x, completed_core_curriculum(x) → eligible_for_graduation(x))
ForAll(x, (eligible_for_graduation(x) ∧ gpa_above_3_5(x)) → graduates_with_honors(x))
```

### 1.3 Hybrid Style
```
ForAll(x, ForAll(h, (clinical_hours(x, h) ∧ h ≥ 500) → advanced_practice(x)))
ForAll(a, ForAll(b, ForAll(c, (higher(a, b) ∧ higher(b, c)) → higher(a, c))))
```

### 1.4 Atomic Facts (không có quantifier)
```
completed_core_curriculum(Sophia)
passed_science_assessment(Sophia)
clinical_hours(john, 600)
membership_duration(Alex) = 8
¬received_safety_endorsement(John)
```

---

## 2. Thiết Kế Bộ Normalizer

### 2.1 Pipeline Chuẩn Hóa

```
Raw FOL String
    │
    ▼
┌──────────────┐
│ Step 1:      │  Nhận diện style (Unicode/Text/Hybrid/Atomic)
│ Detect Style │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Step 2:      │  Thay thế ký tự Unicode → ASCII keywords
│ Unicode→Text │  ∀→ForAll, ∃→Exists, →→Implies, ∧→And, ∨→Or, ¬→Not
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Step 3:      │  Parse thành AST (Abstract Syntax Tree)
│ Parse to AST │  Dùng lark/pyparsing grammar
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Step 4:      │  Chuyển AST → Z3 Python code
│ AST → Z3     │  z3.ForAll, z3.Implies, z3.And, ...
└──────┬───────┘
       │
       ▼
Z3 Expression (ready for solver)
```

### 2.2 Bảng Mapping Unicode → Text

| Unicode | Text Keyword | Z3 Python |
|:---|:---|:---|
| `∀` | `ForAll` | `z3.ForAll(x, ...)` |
| `∃` | `Exists` | `z3.Exists(x, ...)` |
| `→` | `Implies` | `z3.Implies(a, b)` |
| `∧` | `And` | `z3.And(a, b)` |
| `∨` | `Or` | `z3.Or(a, b)` |
| `¬` | `Not` | `z3.Not(a)` |
| `↔` | `Iff` | `a == b` |
| `≥` | `>=` | `a >= b` |
| `≤` | `<=` | `a <= b` |

---

## 3. Grammar Definition (Lark EBNF)

```python
FOL_GRAMMAR = r"""
    ?start: formula

    ?formula: quantified
            | binary
            | unary
            | atom
            | "(" formula ")"

    quantified: quantifier var_list "(" formula ")"
              | quantifier "(" var_list "," formula ")"

    quantifier: "ForAll" -> forall
              | "Exists" -> exists
              | "∀"      -> forall
              | "∃"      -> exists

    var_list: VARIABLE ("," VARIABLE)*

    binary: formula BINARY_OP formula
    
    BINARY_OP: "→" | "Implies" | "∧" | "And" | "∨" | "Or" 
             | "↔" | "Iff" | "≥" | ">=" | "≤" | "<=" | "=" | "≠"

    unary: "¬" formula -> negation
         | "Not" "(" formula ")" -> negation

    atom: predicate "(" term_list ")"
        | VARIABLE

    predicate: IDENTIFIER

    term_list: term ("," term)*
    term: IDENTIFIER | VARIABLE | NUMBER

    VARIABLE: /[a-z][a-z0-9_]*/
    IDENTIFIER: /[A-Z_][A-Za-z0-9_]*/i
    NUMBER: /\d+(\.\d+)?/

    %import common.WS
    %ignore WS
"""
```

---

## 4. Implementation Code

### 4.1 Core Normalizer Class

```python
# src/fol_normalizer.py

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

class FOLStyle(Enum):
    UNICODE = "unicode"      # ∀x (P(x) → Q(x))
    TEXT = "text"            # ForAll(x, P(x) → Q(x))
    HYBRID = "hybrid"       # Mix of both
    ATOMIC = "atomic"       # P(x) or ¬P(x)
    ARITHMETIC = "arithmetic" # x ≥ 500

@dataclass
class NormalizedFOL:
    original: str
    style: FOLStyle
    normalized: str      # Unified text format
    z3_code: str         # Z3 Python expression
    predicates: List[str]
    variables: List[str]
    constants: List[str]

class FOLNormalizer:
    """Normalizes diverse FOL notations to unified Z3-compatible format."""
    
    UNICODE_MAP = {
        '∀': 'ForAll',
        '∃': 'Exists',
        '→': ' Implies ',
        '∧': ' And ',
        '∨': ' Or ',
        '¬': 'Not ',
        '↔': ' Iff ',
        '≥': ' >= ',
        '≤': ' <= ',
        '≠': ' != ',
    }
    
    def detect_style(self, fol: str) -> FOLStyle:
        has_unicode = any(c in fol for c in '∀∃→∧∨¬↔')
        has_text = 'ForAll' in fol or 'Exists' in fol
        has_arith = any(op in fol for op in ['≥', '≤', '>=', '<=', '= '])
        
        if has_unicode and has_text:
            return FOLStyle.HYBRID
        elif has_unicode:
            return FOLStyle.UNICODE
        elif has_text:
            return FOLStyle.TEXT
        elif has_arith:
            return FOLStyle.ARITHMETIC
        else:
            return FOLStyle.ATOMIC
    
    def normalize_unicode(self, fol: str) -> str:
        """Replace all Unicode symbols with text equivalents."""
        result = fol
        for unicode_char, text in self.UNICODE_MAP.items():
            result = result.replace(unicode_char, text)
        return result
    
    def extract_predicates(self, fol: str) -> List[str]:
        """Extract all predicate names from FOL string."""
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, fol)
        keywords = {'ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies'}
        return [m for m in matches if m not in keywords]
    
    def extract_variables(self, fol: str) -> Tuple[List[str], List[str]]:
        """Return (bound_variables, constants)."""
        # Find quantified variables
        quant_pattern = r'(?:ForAll|Exists|∀|∃)\s*[\(]?\s*([a-z][a-z0-9_]*)'
        bound_vars = list(set(re.findall(quant_pattern, fol)))
        
        # Find all identifiers used as arguments
        arg_pattern = r'(?<=[\(,])\s*([A-Z][a-zA-Z0-9_]*)\s*(?=[,\)])'
        constants = list(set(re.findall(arg_pattern, fol)))
        
        return bound_vars, constants
    
    def normalize(self, fol: str) -> NormalizedFOL:
        """Full normalization pipeline."""
        style = self.detect_style(fol)
        predicates = self.extract_predicates(fol)
        variables, constants = self.extract_variables(fol)
        
        # Step 1: Unicode normalization
        normalized = self.normalize_unicode(fol)
        
        # Step 2: Standardize spacing
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Step 3: Generate Z3 code (done by Z3Translator)
        z3_code = ""  # Will be filled by Stage 3
        
        return NormalizedFOL(
            original=fol,
            style=style,
            normalized=normalized,
            z3_code=z3_code,
            predicates=predicates,
            variables=variables,
            constants=constants
        )
```

### 4.2 Batch Processing

```python
def normalize_sample(sample: dict) -> dict:
    """Normalize all FOL premises in a sample."""
    normalizer = FOLNormalizer()
    normalized_premises = []
    
    for fol in sample['premises-FOL']:
        result = normalizer.normalize(fol)
        normalized_premises.append(result)
    
    return {
        **sample,
        'normalized-FOL': [n.normalized for n in normalized_premises],
        'fol-metadata': [{
            'style': n.style.value,
            'predicates': n.predicates,
            'variables': n.variables,
            'constants': n.constants
        } for n in normalized_premises]
    }
```

---

## 5. Xử Lý Edge Cases

### 5.1 Predicate Name Conflicts

```python
# Problem: Some predicates use same name but different arity
# "has_degree(x, PhD)" vs "has_degree(John)"
# Solution: Track arity and create distinct Z3 functions

def resolve_predicate_arity(predicates_usage: dict) -> dict:
    """
    predicates_usage = {'has_degree': [2, 1]}
    → {'has_degree_2': Function(..., 2 args), 
       'has_degree_1': Function(..., 1 arg)}
    """
    pass
```

### 5.2 Mixed Notation in Same Premise

```python
# Problem: "ForAll(x, P(x) ∧ Q(x) → R(x))"
# Has both "ForAll" (text) and "∧", "→" (unicode)
# Solution: Always run unicode normalization first
```

### 5.3 Implicit Conjunction

```python
# Problem: "pedagogical_training(faculty) ∧ curriculum_development(faculty)"
# This is an atomic conjunction without quantifier
# Solution: Detect and wrap appropriately for Z3
```

---

## 6. Testing Strategy

```python
# tests/test_fol_normalizer.py

test_cases = [
    # Unicode style
    ("∀x (WT(x) → O(x))", 
     "ForAll x (WT(x)  Implies  O(x))"),
    
    # Text style (should pass through)
    ("ForAll(x, P(x) → Q(x))", 
     "ForAll(x, P(x)  Implies  Q(x))"),
    
    # Atomic with negation
    ("¬received_safety_endorsement(John)", 
     "Not received_safety_endorsement(John)"),
    
    # Arithmetic
    ("membership_duration(Alex) = 8", 
     "membership_duration(Alex) = 8"),
    
    # Nested quantifiers
    ("ForAll(a, ForAll(b, ForAll(c, (higher(a, b) ∧ higher(b, c)) → higher(a, c))))",
     "ForAll(a, ForAll(b, ForAll(c, (higher(a, b)  And  higher(b, c))  Implies  higher(a, c))))"),
]
```
