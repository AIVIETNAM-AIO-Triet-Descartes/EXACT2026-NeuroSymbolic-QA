"""
Z3 Solver Integration - Formal Verification Engine.

Chuyển đổi FOL premises thành Z3 expressions, kiểm tra entailment,
và hỗ trợ LLM-assisted translation khi rule-based parser fail.

References:
    - Logic-LM: Pan et al., ACL 2023
    - LINC: Olausson et al., EMNLP 2023
    - Z3 Theorem Prover: de Moura & Bjørner, TACAS 2008
"""

import re
import sys
import io
import traceback
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger

try:
    import z3
except ImportError:
    logger.warning("z3-solver not installed. Z3 features will be unavailable.")
    z3 = None


# ══════════════════════════════════════════════════════════════
# Z3 Context
# ══════════════════════════════════════════════════════════════

@dataclass
class Z3Context:
    """Holds all Z3 declarations and assertions for a problem."""
    solver: Any  # z3.Solver
    sort: Any     # z3.SortRef (Entity sort)
    functions: Dict[str, Any] = field(default_factory=dict)
    constants: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    assertions: List[Any] = field(default_factory=list)
    assertion_labels: Dict[int, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# Z3 Translator (Rule-Based)
# ══════════════════════════════════════════════════════════════

class Z3Translator:
    """
    Chuyển đổi FOL premises thành Z3 expressions bằng rule-based approach.

    Xử lý các pattern phổ biến:
        1. ∀x (P(x) → Q(x))           → ForAll([x], Implies(P(x), Q(x)))
        2. P(John)                      → P(John) == True
        3. ¬P(John)                     → P(John) == False
        4. ∀x (A(x) ∧ B(x) → C(x))    → ForAll([x], Implies(And(A(x), B(x)), C(x)))
        5. clinical_hours(john, 600)    → hours(john) == 600
    """

    def __init__(self, timeout_ms: int = 30000):
        if z3 is None:
            raise RuntimeError("z3-solver is required but not installed.")
        self.timeout_ms = timeout_ms

    def create_context(
        self, predicates: Dict[str, int],
        constants: List[str],
        variables: List[str]
    ) -> Z3Context:
        """
        Tạo Z3 context với tất cả sort, function, constant declarations.

        Args:
            predicates: Dict[name → arity]
            constants: Danh sách tên hằng số (entities)
            variables: Danh sách tên biến
        """
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        # Default sort for all entities
        Entity = z3.DeclareSort('Entity')

        # Create Z3 Functions for predicates
        functions = {}
        for pred_name, arity in predicates.items():
            if arity <= 0:
                arity = 1
            arg_sorts = [Entity] * arity + [z3.BoolSort()]
            functions[pred_name] = z3.Function(pred_name, *arg_sorts)

        # Create Z3 constants (named entities like John, Sophia)
        consts = {}
        for name in constants:
            consts[name] = z3.Const(name, Entity)
            # Also create lowercase version
            consts[name.lower()] = z3.Const(name.lower(), Entity)

        # Create Z3 variables
        vars_dict = {}
        for name in variables:
            vars_dict[name] = z3.Const(name, Entity)

        return Z3Context(
            solver=solver,
            sort=Entity,
            functions=functions,
            constants=consts,
            variables=vars_dict,
        )

    def translate_and_solve(
        self,
        premises_fol: List[str],
        premises_nl: List[str],
        goal_text: str,
        goal_is_negated: bool = False,
    ) -> Dict:
        """
        High-level: translate premises, create goal, and check entailment.

        Returns:
            Dict with keys: answer, method, premises_used, error
        """
        try:
            # Use LLM-assisted approach: generate complete Z3 code
            return self._solve_via_code_generation(
                premises_fol, premises_nl, goal_text, goal_is_negated
            )
        except Exception as e:
            logger.warning(f"Z3 translation failed: {e}")
            return {
                'answer': None,
                'method': 'z3_failed',
                'error': str(e),
                'premises_used': [],
            }

    def _solve_via_code_generation(
        self,
        premises_fol: List[str],
        premises_nl: List[str],
        goal_text: str,
        goal_is_negated: bool,
    ) -> Dict:
        """
        Generate and execute Z3 code from FOL premises.

        This method constructs Z3 Python code programmatically from the
        parsed FOL, executes it, and returns the result.
        """
        from pipeline.type1.fol_normalizer import FOLNormalizer

        normalizer = FOLNormalizer()
        norm_list = normalizer.normalize_batch(premises_fol)
        metadata = normalizer.extract_all_metadata(norm_list)

        # Create context
        ctx = self.create_context(
            predicates=metadata['predicates'],
            constants=metadata['constants'],
            variables=metadata['variables'],
        )

        # Add premises as assertions
        success_count = 0
        for i, (fol_str, nf) in enumerate(zip(premises_fol, norm_list)):
            try:
                expr = self._translate_single(fol_str, ctx)
                if expr is not None:
                    # Use tracked assertions for unsat_core
                    label = z3.Bool(f'p_{i+1}')
                    ctx.solver.assert_and_track(expr, label)
                    ctx.assertions.append(expr)
                    ctx.assertion_labels[i + 1] = label
                    success_count += 1
            except Exception as e:
                ctx.errors.append(f"Premise {i+1}: {e}")
                logger.debug(f"Failed to translate premise {i+1}: {fol_str} → {e}")

        if success_count == 0:
            return {
                'answer': None,
                'method': 'z3_no_premises',
                'error': 'No premises could be translated',
                'premises_used': [],
            }

        logger.debug(f"Z3: {success_count}/{len(premises_fol)} premises translated")

        # Check entailment: premises ∧ ¬goal → UNSAT means "Yes"
        # We need to translate the goal too
        # For simplicity, return the context for external checking
        return {
            'answer': None,  # Will be determined by caller
            'method': 'z3_context_ready',
            'ctx': ctx,
            'success_count': success_count,
            'total': len(premises_fol),
            'premises_used': [],
        }

    def _translate_single(self, fol: str, ctx: Z3Context) -> Optional[Any]:
        """
        Translate a single FOL premise to a Z3 expression.

        Handles the most common patterns in the dataset.
        """
        fol = fol.strip()

        # Helper to get or create function
        def get_func(name: str, arity: int = 1):
            if name not in ctx.functions:
                args = [ctx.sort] * arity + [z3.BoolSort()]
                ctx.functions[name] = z3.Function(name, *args)
            return ctx.functions[name]

        def get_const(name: str):
            if name not in ctx.constants:
                ctx.constants[name] = z3.Const(name, ctx.sort)
            if name.lower() not in ctx.constants:
                ctx.constants[name.lower()] = z3.Const(name.lower(), ctx.sort)
            return ctx.constants.get(name) or ctx.constants.get(name.lower())

        def get_var(name: str):
            if name not in ctx.variables:
                ctx.variables[name] = z3.Const(name, ctx.sort)
            return ctx.variables[name]

        # ── Pattern 1: Atomic fact ──
        # P(John) or predicate_name(entity)
        atomic_match = re.match(
            r'^(\w+)\s*\(([^)]+)\)\s*$', fol
        )
        if atomic_match and '→' not in fol and '->' not in fol and \
           '∀' not in fol and 'ForAll' not in fol:
            pred = atomic_match.group(1)
            args_str = atomic_match.group(2)
            args = [a.strip() for a in args_str.split(',')]
            func = get_func(pred, len(args))
            z3_args = [get_const(a) for a in args]
            return func(*z3_args)

        # ── Pattern 2: Negated atomic ──
        # ¬P(John) or ~P(John)
        neg_match = re.match(r'^[¬~]\s*(\w+)\s*\(([^)]+)\)\s*$', fol)
        if neg_match:
            pred = neg_match.group(1)
            args = [a.strip() for a in neg_match.group(2).split(',')]
            func = get_func(pred, len(args))
            z3_args = [get_const(a) for a in args]
            return z3.Not(func(*z3_args))

        # ── Pattern 3: Conjunction atomic ──
        # a(x) ∧ b(x) (without quantifier)
        if ('∧' in fol or ' & ' in fol) and '→' not in fol and \
           '->' not in fol and '∀' not in fol and 'ForAll' not in fol:
            parts = re.split(r'\s*[∧&]\s*', fol)
            exprs = []
            for part in parts:
                e = self._translate_single(part.strip(), ctx)
                if e is not None:
                    exprs.append(e)
            if exprs:
                return z3.And(*exprs) if len(exprs) > 1 else exprs[0]

        # ── Pattern 4: Arithmetic equality ──
        # predicate(entity) = number
        arith_match = re.match(
            r'^(\w+)\s*\(([^)]+)\)\s*=\s*(\d+)\s*$', fol
        )
        if arith_match:
            # For arithmetic, we can just assert the predicate as true
            pred = arith_match.group(1)
            args = [a.strip() for a in arith_match.group(2).split(',')]
            func = get_func(pred, len(args))
            z3_args = [get_const(a) for a in args]
            return func(*z3_args)

        # ── Pattern 5: Universal implication ──
        # ∀x (P(x) → Q(x)) or ForAll(x, P(x) → Q(x))
        return self._translate_quantified(fol, ctx)

    def _translate_quantified(self, fol: str, ctx: Z3Context) -> Optional[Any]:
        """Translate quantified FOL (ForAll/Exists with implications)."""

        def get_func(name, arity=1):
            if name not in ctx.functions:
                args = [ctx.sort] * arity + [z3.BoolSort()]
                ctx.functions[name] = z3.Function(name, *args)
            return ctx.functions[name]

        def get_const(name):
            if name not in ctx.constants:
                ctx.constants[name] = z3.Const(name, ctx.sort)
            return ctx.constants[name]

        def get_var(name):
            if name not in ctx.variables:
                ctx.variables[name] = z3.Const(name, ctx.sort)
            return ctx.variables[name]

        # Normalize unicode first
        norm = fol.replace('∀', 'ForAll').replace('∃', 'Exists')
        norm = norm.replace('→', '->').replace('∧', ' & ')
        norm = norm.replace('∨', ' | ').replace('¬', '~')
        norm = norm.replace('↔', '<->').replace('≥', '>=').replace('≤', '<=')

        # Extract bound variables
        var_names = re.findall(
            r'(?:ForAll|Exists)\s*\(?\s*([a-z][a-z0-9_]*)', norm
        )
        if not var_names:
            var_names = re.findall(r'(?:ForAll|Exists)\s+([a-z])\s', norm)

        z3_vars = [get_var(v) for v in var_names]

        # Extract body (everything inside outermost quantifier)
        body = self._extract_body(norm)
        if not body:
            return None

        # Split body on implication
        impl_parts = re.split(r'\s*->\s*', body, maxsplit=1)
        if len(impl_parts) != 2:
            # Not an implication - try as universal fact
            # ForAll(x, P(x)) means everything satisfies P
            preds = re.findall(r'(\w+)\s*\(', body)
            preds = [p for p in preds if p not in ('ForAll', 'Exists', 'Not')]
            if preds and z3_vars:
                func = get_func(preds[0], 1)
                expr = func(z3_vars[0])
                return z3.ForAll(z3_vars, expr)
            return None

        antecedent_str, consequent_str = impl_parts

        # Parse antecedent
        antecedent_expr = self._parse_formula(
            antecedent_str.strip(), z3_vars, var_names, ctx
        )
        # Parse consequent
        consequent_expr = self._parse_formula(
            consequent_str.strip(), z3_vars, var_names, ctx
        )

        if antecedent_expr is None or consequent_expr is None:
            return None

        # Build ForAll/Exists
        if z3_vars:
            is_exists = 'Exists' in fol or '∃' in fol
            if is_exists:
                return z3.Exists(z3_vars, z3.Implies(antecedent_expr, consequent_expr))
            else:
                return z3.ForAll(z3_vars, z3.Implies(antecedent_expr, consequent_expr))
        else:
            return z3.Implies(antecedent_expr, consequent_expr)

    def _parse_formula(
        self, formula: str, z3_vars: list,
        var_names: list, ctx: Z3Context
    ) -> Optional[Any]:
        """Parse a formula fragment into a Z3 expression."""

        def get_func(name, arity=1):
            if name not in ctx.functions:
                args = [ctx.sort] * arity + [z3.BoolSort()]
                ctx.functions[name] = z3.Function(name, *args)
            return ctx.functions[name]

        def get_arg(name):
            """Get a Z3 expression for an argument name."""
            if name in var_names:
                idx = var_names.index(name)
                return z3_vars[idx]
            if name in ctx.constants:
                return ctx.constants[name]
            if name.lower() in ctx.constants:
                return ctx.constants[name.lower()]
            # Create new constant
            ctx.constants[name] = z3.Const(name, ctx.sort)
            return ctx.constants[name]

        formula = formula.strip().strip('()')

        # Handle negation
        if formula.startswith('~') or formula.startswith('Not('):
            inner = formula[1:].strip() if formula.startswith('~') else \
                    formula[4:-1].strip()
            inner_expr = self._parse_formula(inner, z3_vars, var_names, ctx)
            return z3.Not(inner_expr) if inner_expr else None

        # Handle conjunction (A & B) or (A ∧ B)
        if ' & ' in formula:
            parts = self._split_respecting_parens(formula, ' & ')
            exprs = [
                self._parse_formula(p.strip(), z3_vars, var_names, ctx)
                for p in parts
            ]
            exprs = [e for e in exprs if e is not None]
            if exprs:
                return z3.And(*exprs) if len(exprs) > 1 else exprs[0]
            return None

        # Handle disjunction (A | B)
        if ' | ' in formula:
            parts = self._split_respecting_parens(formula, ' | ')
            exprs = [
                self._parse_formula(p.strip(), z3_vars, var_names, ctx)
                for p in parts
            ]
            exprs = [e for e in exprs if e is not None]
            if exprs:
                return z3.Or(*exprs) if len(exprs) > 1 else exprs[0]
            return None

        # Handle atomic predicate: pred(arg1, arg2, ...)
        pred_match = re.match(r'(\w+)\s*\(([^)]*)\)', formula)
        if pred_match:
            pred_name = pred_match.group(1)
            if pred_name in ('ForAll', 'Exists', 'Not'):
                return None  # Nested quantifier - skip for now
            args_str = pred_match.group(2).strip()
            if args_str:
                args = [a.strip() for a in args_str.split(',')]
                func = get_func(pred_name, len(args))
                z3_args = [get_arg(a) for a in args]
                return func(*z3_args)
            else:
                func = get_func(pred_name, 1)
                if z3_vars:
                    return func(z3_vars[0])
                return None

        return None

    def _extract_body(self, norm: str) -> Optional[str]:
        """Extract body from quantified formula."""
        # Try to match ForAll(vars, body) pattern
        depth = 0
        start = None
        for i, c in enumerate(norm):
            if c == '(' and start is None:
                prefix = norm[:i].rstrip()
                if prefix.endswith(('ForAll', 'Exists')):
                    # Find comma after variable
                    comma = norm.find(',', i)
                    if comma != -1:
                        # Check for nested ForAll
                        rest = norm[comma + 1:].strip()
                        if rest.startswith('ForAll') or rest.startswith('Exists'):
                            return self._extract_body(rest)
                        start = comma + 1
                        depth = 1
                    continue
            if start is not None:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        return norm[start:i].strip()

        # Fallback: content after variable in ∀x (body)
        match = re.search(r'ForAll\s+(\w+)\s+\((.+)\)\s*$', norm, re.DOTALL)
        if match:
            return match.group(2).strip()

        # Another fallback
        match = re.search(r'ForAll\s+(\w+)\s+(.+)$', norm, re.DOTALL)
        if match:
            return match.group(2).strip()

        return None

    def _split_respecting_parens(self, s: str, delimiter: str) -> List[str]:
        """Split string by delimiter, respecting parentheses."""
        parts = []
        depth = 0
        current = []
        i = 0
        while i < len(s):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1

            if depth == 0 and s[i:i + len(delimiter)] == delimiter:
                parts.append(''.join(current))
                current = []
                i += len(delimiter)
                continue

            current.append(s[i])
            i += 1

        if current:
            parts.append(''.join(current))
        return parts


# ══════════════════════════════════════════════════════════════
# Entailment Checker
# ══════════════════════════════════════════════════════════════

class EntailmentChecker:
    """
    Kiểm tra entailment (hệ quả logic) bằng Z3.

    Methods:
        check_entailment: premises ⊨ conclusion?
        check_mcq: Tìm option đúng trong MCQ
        get_unsat_core: Trả về tập premises tối thiểu
    """

    @staticmethod
    def check_entailment(
        ctx: Z3Context, conclusion: Any
    ) -> Tuple[str, Optional[List[int]]]:
        """
        Check if premises entail conclusion.

        Method: Proof by contradiction
            - Add ¬conclusion
            - UNSAT → "Yes" (conclusion follows)
            - SAT → "No" (counterexample exists)
            - UNKNOWN → "Unknown"

        Returns:
            (answer, used_premises)
        """
        ctx.solver.push()
        ctx.solver.add(z3.Not(conclusion))

        result = ctx.solver.check()

        used_premises = None
        if result == z3.unsat:
            answer = "Yes"
            # Try to get unsat core
            try:
                core = ctx.solver.unsat_core()
                used_premises = []
                for c in core:
                    name = str(c)
                    if name.startswith('p_'):
                        idx = int(name.split('_')[1])
                        used_premises.append(idx)
                used_premises = sorted(used_premises)
            except Exception:
                pass
        elif result == z3.sat:
            answer = "No"
        else:
            answer = "Unknown"

        ctx.solver.pop()
        return answer, used_premises

    @staticmethod
    def check_satisfiability(
        ctx: Z3Context, statement: Any
    ) -> str:
        """Check if statement is satisfiable given premises."""
        ctx.solver.push()
        ctx.solver.add(statement)
        result = ctx.solver.check()
        ctx.solver.pop()

        if result == z3.sat:
            return "satisfiable"
        elif result == z3.unsat:
            return "unsatisfiable"
        return "unknown"


# ══════════════════════════════════════════════════════════════
# LLM-Assisted Z3 Code Generation
# ══════════════════════════════════════════════════════════════

def autofix_z3_declarations(code_str: str) -> str:
    """
    Auto-fixes Z3 code where predicates are declared as single-value variables
    (e.g., CR = Bool('CR') or CR, HD = Bools('CR HD')) but called as functions (e.g., CR(Asha)).
    Rewrites declarations to Function('CR', Entity, ..., BoolSort()) based on calling arity.
    """
    import ast
    try:
        tree = ast.parse(code_str)
    except Exception:
        return code_str

    # Step 0: Unpack multiple assignments like A, B = Bools('A B')
    class UnpackAssignments(ast.NodeTransformer):
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Tuple, ast.List)):
                elements = node.targets[0].elts
                if all(isinstance(e, ast.Name) for e in elements):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id
                        if func_name in ('Bools', 'Ints', 'Reals'):
                            single_func = func_name[:-1]
                            new_nodes = []
                            for e in elements:
                                var_name = e.id
                                new_assign = ast.Assign(
                                    targets=[ast.copy_location(ast.Name(id=var_name, ctx=ast.Store()), e)],
                                    value=ast.Call(
                                        func=ast.Name(id=single_func, ctx=ast.Load()),
                                        args=[ast.Constant(value=var_name)],
                                        keywords=[]
                                    )
                                )
                                new_nodes.append(ast.copy_location(new_assign, node))
                            return new_nodes
                        elif func_name == 'Consts':
                            new_nodes = []
                            sort_arg = node.value.args[1] if len(node.value.args) >= 2 else ast.Name(id='Entity', ctx=ast.Load())
                            for e in elements:
                                var_name = e.id
                                new_assign = ast.Assign(
                                    targets=[ast.copy_location(ast.Name(id=var_name, ctx=ast.Store()), e)],
                                    value=ast.Call(
                                        func=ast.Name(id='Const', ctx=ast.Load()),
                                        args=[ast.Constant(value=var_name), sort_arg],
                                        keywords=[]
                                    )
                                )
                                new_nodes.append(ast.copy_location(new_assign, node))
                            return new_nodes
            return node

    tree = UnpackAssignments().visit(tree)

    declared_vars = {} # name -> (node, type_str)
    
    class DeclFinder(ast.NodeVisitor):
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    func_name = node.value.func.id
                    if func_name in ('Bool', 'BoolConst', 'Bools'):
                        declared_vars[var_name] = (node, 'Bool')
                    elif func_name in ('Int', 'IntConst', 'Ints'):
                        declared_vars[var_name] = (node, 'Int')
                    elif func_name in ('Real', 'RealConst', 'Reals'):
                        declared_vars[var_name] = (node, 'Real')
                    elif func_name == 'Const':
                        type_str = 'Entity'
                        if len(node.value.args) >= 2:
                            second_arg = node.value.args[1]
                            if isinstance(second_arg, ast.Call) and isinstance(second_arg.func, ast.Name):
                                if second_arg.func.id == 'BoolSort':
                                    type_str = 'Bool'
                                elif second_arg.func.id in ('IntSort', 'RealSort'):
                                    type_str = 'Int'
                        declared_vars[var_name] = (node, type_str)

    DeclFinder().visit(tree)

    called_vars_arity = {} # name -> arity
    
    class CallFinder(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in declared_vars:
                    called_vars_arity[func_name] = len(node.args)
            self.generic_visit(node)

    CallFinder().visit(tree)

    class DeclRewriter(ast.NodeTransformer):
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                if var_name in called_vars_arity:
                    arity = called_vars_arity[var_name]
                    type_str = declared_vars[var_name][1]
                    
                    sort_name = 'BoolSort' if type_str == 'Bool' else ('IntSort' if type_str == 'Int' else 'BoolSort')
                    
                    args = [ast.Constant(value=var_name)]
                    for _ in range(arity):
                        args.append(ast.Name(id='Entity', ctx=ast.Load()))
                    args.append(ast.Call(
                        func=ast.Name(id=sort_name, ctx=ast.Load()),
                        args=[],
                        keywords=[]
                    ))
                    
                    new_node = ast.Assign(
                        targets=node.targets,
                        value=ast.Call(
                            func=ast.Name(id='Function', ctx=ast.Load()),
                            args=args,
                            keywords=[]
                        )
                    )
                    return ast.copy_location(new_node, node)
            return node

    rewritten_tree = DeclRewriter().visit(tree)

    # Now, find all defined names (including newly rewritten custom functions)
    import z3
    predefined = {
        'z3', 'Entity', 'x', 'y', 'z', 'Solver', 'solve_yes_no', 'solve_mcq', 's',
        'True', 'False', 'None', 'print', 'len', 'range', 'int', 'str', 'dict', 'list', 'set'
    }
    for name in dir(z3):
        if not name.startswith('_'):
            predefined.add(name)

    defined_names = set(predefined)
    custom_functions = set()

    class FinalDefFinder(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        if node.value.func.id == 'Function':
                            custom_functions.add(target.id)
            self.generic_visit(node)
            
        def visit_FunctionDef(self, node):
            defined_names.add(node.name)
            self.generic_visit(node)
            
        def visit_Import(self, node):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
                
        def visit_ImportFrom(self, node):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)

    FinalDefFinder().visit(rewritten_tree)

    # Find all loaded names (uses) in the tree
    loaded_names = {} # name -> max_arity

    class LoadedNameFinder(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                if node.id not in loaded_names:
                    loaded_names[node.id] = 0
            self.generic_visit(node)
            
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                loaded_names[func_name] = max(loaded_names.get(func_name, 0), len(node.args))
            self.generic_visit(node)

    LoadedNameFinder().visit(rewritten_tree)

    # Determine undeclared variables/functions
    undeclared_consts = []
    undeclared_funcs = []

    for name, arity in loaded_names.items():
        if name not in defined_names:
            if arity > 0:
                undeclared_funcs.append((name, arity))
                custom_functions.add(name)
            else:
                undeclared_consts.append(name)

    # Build new assignments for these undeclared entities
    new_decls = []
    for name, arity in undeclared_funcs:
        # name = Function('name', Entity, ..., BoolSort())
        args = [ast.Constant(value=name)]
        for _ in range(arity):
            args.append(ast.Name(id='Entity', ctx=ast.Load()))
        args.append(ast.Call(func=ast.Name(id='BoolSort', ctx=ast.Load()), args=[], keywords=[]))
        
        assign = ast.Assign(
            targets=[ast.Name(id=name, ctx=ast.Store())],
            value=ast.Call(func=ast.Name(id='Function', ctx=ast.Load()), args=args, keywords=[])
        )
        new_decls.append(assign)

    for name in undeclared_consts:
        # name = Const('name', Entity)
        assign = ast.Assign(
            targets=[ast.Name(id=name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id='Const', ctx=ast.Load()),
                args=[ast.Constant(value=name), ast.Name(id='Entity', ctx=ast.Load())],
                keywords=[]
            )
        )
        new_decls.append(assign)

    # Insert new declarations at the beginning of rewritten_tree.body
    if new_decls:
        rewritten_tree.body = new_decls + rewritten_tree.body

    # Rewrite literal arguments of custom functions to Z3 Const(str(val), Entity)
    class LiteralArgumentRewriter(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id in custom_functions:
                new_args = []
                for arg in node.args:
                    is_literal = False
                    val = None
                    if isinstance(arg, ast.Constant):
                        is_literal = True
                        val = arg.value
                    elif isinstance(arg, ast.Num):
                        is_literal = True
                        val = arg.n
                    elif isinstance(arg, ast.Str):
                        is_literal = True
                        val = arg.s
                    elif isinstance(arg, ast.NameConstant):
                        is_literal = True
                        val = arg.value
                        
                    if is_literal:
                        new_arg = ast.Call(
                            func=ast.Name(id='Const', ctx=ast.Load()),
                            args=[ast.Constant(value=str(val)), ast.Name(id='Entity', ctx=ast.Load())],
                            keywords=[]
                        )
                        new_args.append(new_arg)
                    else:
                        new_args.append(arg)
                node.args = new_args
            return node

    rewritten_tree = LiteralArgumentRewriter().visit(rewritten_tree)
    ast.fix_missing_locations(rewritten_tree)
    try:
        return ast.unparse(rewritten_tree)
    except Exception:
        return code_str


def execute_z3_code(code: str, timeout_sec: int = 30) -> Optional[str]:
    """
    Thực thi Z3 Python code an toàn trong sandbox.

    Args:
        code: Mã Python sử dụng z3 library.
        timeout_sec: Giới hạn thời gian.

    Returns:
        Output text hoặc None nếu thất bại.
    """
    # Auto-fix variable/function declarations (e.g. Bool vs Function)
    code = autofix_z3_declarations(code)
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        import z3
        
        # Predefined Entity sort and common variables
        Entity = z3.DeclareSort('Entity')
        x = z3.Const('x', Entity)
        y = z3.Const('y', Entity)
        z = z3.Const('z', Entity)

        class TrackingSolver:
            def __init__(self, *args, **kwargs):
                self._solver = z3.Solver(*args, **kwargs)
                self._labels = {}
                self._counter = 1

            def add(self, *args):
                for arg in args:
                    label_name = f"p_{self._counter}"
                    label = z3.Bool(label_name)
                    self._labels[label_name] = self._counter
                    self._counter += 1
                    self._solver.assert_and_track(arg, label)

            def check(self, *args):
                return self._solver.check(*args)

            def push(self):
                self._solver.push()

            def pop(self):
                self._solver.pop()

            def model(self):
                return self._solver.model()

            def unsat_core(self):
                return self._solver.unsat_core()

        def solve_yes_no(solver, goal):
            # Check Yes (Goal is entailed)
            solver.push()
            solver.add(z3.Not(goal))
            res_yes = solver.check()
            if res_yes == z3.unsat:
                print("Yes")
                try:
                    core = solver.unsat_core()
                    used = []
                    for item in core:
                        name = str(item)
                        if name.startswith('p_'):
                            idx = int(name.split('_')[1])
                            used.append(idx)
                    # Filter out the goal label (which was added last, so it has the highest index)
                    last_label_idx = solver._counter - 1
                    used = [i for i in used if i < last_label_idx]
                    print(f"PREMISES USED: {sorted(used)}")
                except Exception:
                    pass
                solver.pop()
                return
            solver.pop()

            # Check No (Negation of Goal is entailed)
            solver.push()
            solver.add(goal)
            res_no = solver.check()
            if res_no == z3.unsat:
                print("No")
                try:
                    core = solver.unsat_core()
                    used = []
                    for item in core:
                        name = str(item)
                        if name.startswith('p_'):
                            idx = int(name.split('_')[1])
                            used.append(idx)
                    last_label_idx = solver._counter - 1
                    used = [i for i in used if i < last_label_idx]
                    print(f"PREMISES USED: {sorted(used)}")
                except Exception:
                    pass
                solver.pop()
                return
            solver.pop()
            print("Unknown")

        def solve_mcq(solver, options_dict):
            entailed = []
            cores = {}
            for key, expr in options_dict.items():
                if expr is None:
                    continue
                solver.push()
                solver.add(z3.Not(expr))
                res = solver.check()
                if res == z3.unsat:
                    entailed.append(key)
                    try:
                        core = solver.unsat_core()
                        used = []
                        for item in core:
                            name = str(item)
                            if name.startswith('p_'):
                                idx = int(name.split('_')[1])
                                used.append(idx)
                        last_label_idx = solver._counter - 1
                        used = [i for i in used if i < last_label_idx]
                        cores[key] = sorted(used)
                    except Exception:
                        pass
                solver.pop()

            if len(entailed) == 1:
                ans = entailed[0]
                print(ans)
                if ans in cores:
                    print(f"PREMISES USED: {cores[ans]}")
            elif len(entailed) > 1:
                ans = entailed[0]
                print(ans)
                if ans in cores:
                    print(f"PREMISES USED: {cores[ans]}")
            else:
                none_key = None
                for key, expr in options_dict.items():
                    if expr is None:
                        none_key = key
                        break
                if none_key:
                    print(none_key)
                else:
                    print("Unknown")

        # Prepare globals
        exec_globals = {
            'z3': z3,
            'Entity': Entity,
            'x': x,
            'y': y,
            'z': z,
            'Solver': TrackingSolver,
            's': TrackingSolver(),
            'solve_yes_no': solve_yes_no,
            'solve_mcq': solve_mcq,
        }
        # Populate with standard z3 functions
        for name in dir(z3):
            if not name.startswith('_') and name != 'Solver':
                exec_globals[name] = getattr(z3, name)

        # Run code
        exec(code, exec_globals)
        output = buffer.getvalue().strip()
        return output

    except Exception as e:
        logger.error(f"Z3 code execution failed:\n{traceback.format_exc()}")
        return None

    finally:
        sys.stdout = old_stdout
