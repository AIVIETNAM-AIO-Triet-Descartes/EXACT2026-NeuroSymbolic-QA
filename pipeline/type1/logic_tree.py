"""
Logic Tree - Cây Luận Lý (Directed Acyclic Graph).

Xây dựng cấu trúc DAG biểu diễn chuỗi suy luận từ premises → conclusion.
Hỗ trợ Forward Chaining, Backward Chaining, Contraposition, và Transitivity Closure.

References:
    - Tree-of-Thought: Yao et al., NeurIPS 2023
    - ProofWriter: Tafjord et al., EMNLP 2021
    - Forward/Backward Chaining: Russell & Norvig, AIMA 4th Ed.
"""

import re
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger


# ══════════════════════════════════════════════════════════════
# Node Definitions
# ══════════════════════════════════════════════════════════════

@dataclass
class FactNode:
    """
    Nút lá - mệnh đề nguyên tử đã biết đúng/sai.

    Ví dụ:
        completed_courses(John) → FactNode("completed_courses", ["John"], False, 5)
        ¬safety_endorsement(John) → FactNode("safety_endorsement", ["John"], True, 7)
    """
    predicate: str
    arguments: List[str]
    is_negated: bool
    premise_index: int   # 1-based index trong premises list
    node_id: str = ""

    def __post_init__(self):
        neg = "NOT_" if self.is_negated else ""
        args = "_".join(self.arguments) if self.arguments else "universal"
        self.node_id = f"fact_{neg}{self.predicate}_{args}_p{self.premise_index}"

    def signature(self) -> str:
        """Unique signature cho matching."""
        neg = "~" if self.is_negated else ""
        return f"{neg}{self.predicate}({','.join(self.arguments)})"


@dataclass
class RuleNode:
    """
    Nút trung gian - luật suy diễn (implication rule).

    Ví dụ:
        ∀x (P(x) ∧ Q(x) → R(x))
        → RuleNode(["P", "Q"], "R", 1, True, ["x"])
    """
    antecedents: List[str]       # Tên predicates cần thỏa mãn
    consequent: str              # Predicate được suy ra
    premise_index: int
    is_universal: bool
    bound_variables: List[str] = field(default_factory=list)
    negated_antecedents: List[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""
    node_id: str = ""

    def __post_init__(self):
        ants = "&".join(self.antecedents)
        self.node_id = f"rule_{ants}->{self.consequent}_p{self.premise_index}"


@dataclass
class DerivedNode:
    """
    Nút được suy ra qua Forward/Backward Chaining.

    Attributes:
        derived_from: Danh sách node_id đã dùng để suy ra.
        rule_used: node_id của rule đã áp dụng.
        depth: Số bước suy luận từ facts.
    """
    predicate: str
    arguments: List[str]
    is_negated: bool
    derived_from: List[str]
    rule_used: str
    depth: int
    premises_involved: List[int] = field(default_factory=list)
    node_id: str = ""

    def __post_init__(self):
        neg = "NOT_" if self.is_negated else ""
        args = "_".join(self.arguments) if self.arguments else "any"
        self.node_id = f"derived_{neg}{self.predicate}_{args}_d{self.depth}"


# ══════════════════════════════════════════════════════════════
# FOL Premise Parser (Lightweight)
# ══════════════════════════════════════════════════════════════

class FOLPremiseParser:
    """
    Lightweight parser để trích xuất cấu trúc rule/fact từ FOL string.

    Không dùng full grammar parser, mà dùng regex patterns
    cho các trường hợp phổ biến trong dataset.
    """

    # Patterns cho Unicode-style FOL
    UNICODE_IMPL = re.compile(
        r'[∀ForAll]+.*?\(.*?'
        r'([\w]+)\s*\(.*?\)'     # first predicate
        r'.*?→.*?'
        r'([\w]+)\s*\(.*?\)',    # consequent predicate
        re.DOTALL
    )

    def parse_premise(
        self, fol: str, index: int
    ) -> Optional[Any]:
        """
        Parse một FOL premise thành FactNode hoặc RuleNode.

        Args:
            fol: Chuỗi FOL gốc.
            index: 1-based index của premise.

        Returns:
            FactNode hoặc RuleNode, hoặc None nếu parse fail.
        """
        fol = fol.strip()

        # ── Case 1: Atomic fact (no quantifier, no implication) ──
        if self._is_atomic(fol):
            return self._parse_atomic(fol, index)

        # ── Case 2: Universal/Existential with simple body ──
        if self._is_universal_fact(fol):
            return self._parse_universal_fact(fol, index)

        # ── Case 3: Implication rule ──
        if '→' in fol or '->' in fol:
            return self._parse_rule(fol, index)

        # Fallback: try as atomic
        return self._parse_atomic(fol, index)

    def parse_all(
        self, premises_fol: List[str]
    ) -> Tuple[List[FactNode], List[RuleNode]]:
        """Parse tất cả premises và phân loại thành facts/rules."""
        facts = []
        rules = []

        for i, fol in enumerate(premises_fol):
            result = self.parse_premise(fol, i + 1)
            if result is None:
                logger.debug(f"Could not parse premise {i+1}: {fol}")
                continue

            if isinstance(result, FactNode):
                facts.append(result)
            elif isinstance(result, RuleNode):
                rules.append(result)
            elif isinstance(result, list):
                # Some premises parse into multiple nodes
                for node in result:
                    if isinstance(node, FactNode):
                        facts.append(node)
                    elif isinstance(node, RuleNode):
                        rules.append(node)

        return facts, rules

    # ── Private parsing methods ───────────────────────────────

    def _is_atomic(self, fol: str) -> bool:
        """Check if FOL is atomic (no quantifier, no implication)."""
        no_quant = '∀' not in fol and 'ForAll' not in fol and \
                   '∃' not in fol and 'Exists' not in fol
        no_impl = '→' not in fol and '->' not in fol
        return no_quant and no_impl

    def _is_universal_fact(self, fol: str) -> bool:
        """Check if FOL is a universally/existentially quantified simple fact (no impl)."""
        has_quant = '∀' in fol or 'ForAll' in fol or '∃' in fol or 'Exists' in fol
        no_impl = '→' not in fol and '->' not in fol
        return has_quant and no_impl

    def _parse_atomic(self, fol: str, index: int) -> Optional[FactNode]:
        """Parse an atomic fact like P(John) or ¬P(John) or bare_predicate."""
        fol = fol.strip()
        is_negated = fol.startswith('¬') or fol.startswith('~')
        if is_negated:
            fol = fol[1:].strip()

        # Handle conjunction: a(x) ∧ b(x)
        if '∧' in fol or '&' in fol:
            parts = re.split(r'\s*[∧&]\s*', fol)
            nodes = []
            for part in parts:
                node = self._parse_single_atomic(part.strip(), index, is_negated)
                if node:
                    nodes.append(node)
            return nodes if nodes else None

        return self._parse_single_atomic(fol, index, is_negated)

    def _parse_single_atomic(
        self, fol: str, index: int, is_negated: bool
    ) -> Optional[FactNode]:
        """Parse a single atomic predicate."""
        # Match: predicate(arg1, arg2, ...)
        match = re.match(r'(\w+)\s*\(([^)]*)\)', fol.strip())
        if match:
            predicate = match.group(1)
            args_str = match.group(2).strip()
            args = [a.strip() for a in args_str.split(',')] if args_str else []
            return FactNode(
                predicate=predicate,
                arguments=args,
                is_negated=is_negated,
                premise_index=index,
            )

        # Handle: predicate_name(args) = value (arithmetic)
        eq_match = re.match(r'(\w+)\s*\(([^)]*)\)\s*=\s*(\d+)', fol.strip())
        if eq_match:
            predicate = eq_match.group(1)
            args = [a.strip() for a in eq_match.group(2).split(',')]
            args.append(eq_match.group(3))
            return FactNode(
                predicate=predicate,
                arguments=args,
                is_negated=is_negated,
                premise_index=index,
            )

        # Handle: bare predicate without parentheses (e.g., "depleted_fund", "available_mentors")
        bare_match = re.match(r'^([a-zA-Z_]\w*)$', fol.strip())
        if bare_match:
            return FactNode(
                predicate=bare_match.group(1),
                arguments=[],
                is_negated=is_negated,
                premise_index=index,
            )

        # Handle: equality without function notation (e.g., "(time_diff(A, B) = 0.5)")
        eq_match2 = re.match(r'\(?\s*(\w+)\s*\(([^)]*)\)\s*=\s*([\d.]+)\s*\)?', fol.strip())
        if eq_match2:
            predicate = eq_match2.group(1)
            args = [a.strip() for a in eq_match2.group(2).split(',')]
            args.append(eq_match2.group(3))
            return FactNode(
                predicate=predicate,
                arguments=args,
                is_negated=is_negated,
                premise_index=index,
            )

        return None

    def _parse_universal_fact(
        self, fol: str, index: int
    ) -> Optional[FactNode]:
        """Parse ∀x (P(x)) or ∃x (P(x)) - quantified fact without impl.
        
        Also handles patterns without outer parens like:
            ∀x complete(x)
            ∃x enrolled(x)
            ∀x(¬engage(x))
        """
        # Extract the body inside the quantifier
        body = self._extract_body(fol)
        if body:
            return self._parse_atomic(body, index)

        # Fallback: handle ∀x pred(x) or ∃x pred(x) without outer parens
        match = re.search(
            r'(?:∀|∃|ForAll|Exists)\s*\w+\s+(¬|~)?(\w+)\s*\(([^)]*)\)',
            fol
        )
        if match:
            is_negated = match.group(1) is not None
            predicate = match.group(2)
            args_str = match.group(3).strip()
            args = [a.strip() for a in args_str.split(',')] if args_str else []
            return FactNode(
                predicate=predicate,
                arguments=args,
                is_negated=is_negated,
                premise_index=index,
            )

        # Fallback: handle bare ∀x pred (without parens at all)
        match2 = re.search(
            r'(?:∀|∃|ForAll|Exists)\s*\w+\s+(¬|~)?(\w+)\s*$',
            fol.strip()
        )
        if match2:
            is_negated = match2.group(1) is not None
            predicate = match2.group(2)
            return FactNode(
                predicate=predicate,
                arguments=[],
                is_negated=is_negated,
                premise_index=index,
            )

        return None

    def _parse_rule(
        self, fol: str, index: int
    ) -> Optional[RuleNode]:
        """Parse an implication rule: ... → ...
        
        Handles:
        - Standard rules: P(x) → Q(x)
        - Negated antecedent rules: ¬P(x) → ¬Q(x)
        - Bare predicate antecedents: depleted_fund → ¬scholarship(s)
        - Mixed rules: P(x) ∧ ¬Q(x) → R(x)
        """
        # Determine if universal
        is_universal = '∀' in fol or 'ForAll' in fol

        # Extract bound variables
        bound_vars = re.findall(
            r'(?:∀|ForAll)\s*\(?\s*([a-z][a-z0-9_]*)', fol
        )

        # Split on implication (handle both → and ->)
        body = self._extract_body(fol) or fol

        # Split antecedent → consequent
        parts = re.split(r'\s*(?:→|->)\s*', body, maxsplit=1)
        if len(parts) != 2:
            return None

        antecedent_str, consequent_str = parts

        # Extract predicates from antecedent
        antecedent_preds = self._extract_predicate_names(antecedent_str)

        # Extract negated predicates in antecedent
        negated_ants = []
        for pred in re.findall(r'[¬~](\w+)\s*\(', antecedent_str):
            negated_ants.append(pred)
            if pred in antecedent_preds:
                antecedent_preds.remove(pred)

        # Also handle bare negated predicates without parens: ¬bare_pred
        for pred in re.findall(r'[¬~](\w+)(?:\s|$|[∧&])', antecedent_str):
            if pred not in negated_ants and not re.search(re.escape(pred) + r'\s*\(', antecedent_str):
                negated_ants.append(pred)

        # Handle bare (non-negated) antecedent predicates without parens
        # e.g., "depleted_fund → ¬scholarship(s)" — "depleted_fund" has no parens
        for bare in re.findall(r'(?:^|[∧&])\s*([a-zA-Z_]\w*)(?:\s|$|[∧&→])', antecedent_str):
            if bare not in antecedent_preds and bare not in negated_ants and \
               bare not in ('ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies'):
                antecedent_preds.append(bare)

        # Extract consequent predicate
        consequent_preds = self._extract_predicate_names(consequent_str)
        consequent = consequent_preds[0] if consequent_preds else ""

        # If consequent has no pred with parens, try bare predicate
        if not consequent:
            bare_cons = re.findall(r'(?:^|[¬~])\s*([a-zA-Z_]\w*)(?:\s|$)', consequent_str.strip())
            bare_cons = [b for b in bare_cons if b not in ('ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies')]
            if bare_cons:
                consequent = bare_cons[0]

        # Check for negated consequent
        is_neg_consequent = bool(re.search(r'[¬~]\s*' + re.escape(consequent), consequent_str)) if consequent else False
        if is_neg_consequent:
            consequent = f"NOT_{consequent}"

        # For rules with ONLY negated antecedents (e.g., ¬P(x) → ¬Q(x)),
        # keep negated preds as antecedents so the rule isn't discarded
        if not consequent:
            return None
        if not antecedent_preds and negated_ants:
            # Use negated predicates as antecedents with NOT_ prefix
            antecedent_preds = [f"NOT_{p}" for p in negated_ants]
            negated_ants = []  # They are now explicitly tracked as NOT_ antecedents

        if not antecedent_preds:
            return None

        return RuleNode(
            antecedents=antecedent_preds,
            consequent=consequent,
            premise_index=index,
            is_universal=is_universal,
            bound_variables=bound_vars,
            negated_antecedents=negated_ants,
        )

    def _extract_body(self, fol: str) -> Optional[str]:
        """Extract the inner body from quantified FOL."""
        # Try ForAll(x, BODY) or ForAll(x, ForAll(y, BODY))
        # Find the outermost balanced parentheses after quantifier
        depth = 0
        start = None
        for i, c in enumerate(fol):
            if c == '(' and start is None:
                if i > 0 and fol[:i].rstrip().endswith(('ForAll', 'Exists', '∀', '∃')):
                    # This is the quantifier paren - skip the variable part
                    # Find the comma after variable
                    comma_pos = fol.find(',', i)
                    if comma_pos != -1:
                        start = comma_pos + 1
                        depth = 1
                    continue
            if start is not None:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        return fol[start:i].strip()

        # Fallback: try to find body after quantifier pattern
        match = re.search(r'(?:∀|∃)\s*\w+\s*\((.+)\)\s*$', fol, re.DOTALL)
        if match:
            return match.group(1).strip()

        return None

    def _extract_predicate_names(self, text: str) -> List[str]:
        """Extract predicate names from a formula fragment."""
        keywords = {'ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies'}
        matches = re.findall(r'(\w+)\s*\(', text)
        return [m for m in matches if m not in keywords]


# ══════════════════════════════════════════════════════════════
# Logic Tree Builder
# ══════════════════════════════════════════════════════════════

class LogicTree:
    """
    Cây Luận Lý - DAG biểu diễn chuỗi suy luận.

    Thuật toán chính:
        1. Parse premises → Facts + Rules
        2. Build adjacency graph
        3. Forward Chaining: suy ra mọi kết luận có thể
        4. Backward Chaining: chứng minh goal cụ thể
        5. Extract proof trace & used premises

    Complexity:
        Forward Chaining: O(|Rules| × |Facts| × max_depth)
        Backward Chaining: O(|Rules|^max_depth) worst case
    """

    def __init__(self, premises_fol: List[str]):
        """
        Khởi tạo Logic Tree từ danh sách premises FOL.

        Args:
            premises_fol: Danh sách các biểu thức FOL.
        """
        self.premises_fol = premises_fol
        self.parser = FOLPremiseParser()

        # Parse premises
        self.facts, self.rules = self.parser.parse_all(premises_fol)

        # Build graph
        self.graph = self._build_graph()

        # Known facts (populated by forward chaining)
        self.known: Dict[str, List[FactNode]] = defaultdict(list)
        self.derived: List[DerivedNode] = []

        # Initialize known facts
        for fact in self.facts:
            self.known[fact.predicate].append(fact)

        logger.debug(
            f"LogicTree initialized: {len(self.facts)} facts, "
            f"{len(self.rules)} rules"
        )

    def _build_graph(self) -> Dict[str, Dict[str, list]]:
        """Xây dựng đồ thị adjacency cho Logic Tree."""
        graph: Dict[str, Dict[str, list]] = defaultdict(
            lambda: {'facts': [], 'as_antecedent': [], 'as_consequent': []}
        )

        for fact in self.facts:
            graph[fact.predicate]['facts'].append(fact)

        for rule in self.rules:
            for ant in rule.antecedents:
                graph[ant]['as_antecedent'].append(rule)
            graph[rule.consequent]['as_consequent'].append(rule)

        return dict(graph)

    # ── Forward Chaining ──────────────────────────────────────

    def forward_chain(self, max_depth: int = 15) -> List[DerivedNode]:
        """
        Forward Chaining: suy ra mọi kết luận có thể từ facts đã biết.

        Algorithm:
            1. Start from known atomic facts
            2. For each rule, check if ALL antecedents are satisfied
            3. If yes → derive consequent, add to known
            4. Repeat until fixpoint or max_depth

        Args:
            max_depth: Giới hạn độ sâu suy luận.

        Returns:
            Danh sách các DerivedNode đã suy ra.
        """
        self.derived = []
        derived_set: Set[str] = set()  # Track what's already derived

        for depth in range(1, max_depth + 1):
            new_derived = []

            for rule in self.rules:
                if rule.blocked:
                    continue

                # Check if all antecedents are satisfied
                all_satisfied = True
                contributing_nodes = []
                contributing_premises = [rule.premise_index]

                for ant in rule.antecedents:
                    if ant in self.known:
                        for fact in self.known[ant]:
                            contributing_nodes.append(fact.node_id)
                            contributing_premises.append(fact.premise_index)
                        # Also check derived
                        found = False
                        for d in self.derived:
                            if d.predicate == ant and not d.is_negated:
                                found = True
                                contributing_nodes.append(d.node_id)
                                contributing_premises.extend(d.premises_involved)
                        if not self.known[ant] and not found:
                            all_satisfied = False
                            break
                    else:
                        # Check in derived
                        found = False
                        for d in self.derived:
                            if d.predicate == ant and not d.is_negated:
                                found = True
                                contributing_nodes.append(d.node_id)
                                contributing_premises.extend(d.premises_involved)
                                break
                        if not found:
                            all_satisfied = False
                            break

                # Check negated antecedents (should NOT be present)
                for neg_ant in rule.negated_antecedents:
                    if neg_ant in self.known:
                        # If there's a positive fact for the negated antecedent
                        has_positive = any(
                            not f.is_negated for f in self.known[neg_ant]
                        )
                        if has_positive:
                            all_satisfied = False
                            break

                if all_satisfied:
                    sig = f"{rule.consequent}_d{depth}"
                    if sig not in derived_set:
                        derived_set.add(sig)
                        node = DerivedNode(
                            predicate=rule.consequent,
                            arguments=[],
                            is_negated=rule.consequent.startswith("NOT_"),
                            derived_from=contributing_nodes,
                            rule_used=rule.node_id,
                            depth=depth,
                            premises_involved=list(set(contributing_premises)),
                        )
                        new_derived.append(node)
                        # Add to known for next iteration
                        pred_name = rule.consequent.replace("NOT_", "")
                        self.known[pred_name].append(
                            FactNode(
                                predicate=pred_name,
                                arguments=[],
                                is_negated=rule.consequent.startswith("NOT_"),
                                premise_index=-1,  # derived, not from premise
                            )
                        )

            if not new_derived:
                logger.debug(f"Forward chaining converged at depth {depth}")
                break

            self.derived.extend(new_derived)

        logger.debug(f"Forward chaining derived {len(self.derived)} new facts")
        return self.derived

    # ── Backward Chaining ─────────────────────────────────────

    def backward_chain(
        self, goal_predicate: str, max_depth: int = 10,
        _visited: Optional[Set[str]] = None
    ) -> Optional[List[int]]:
        """
        Backward Chaining: chứng minh goal cụ thể.

        Args:
            goal_predicate: Tên predicate cần chứng minh.
            max_depth: Giới hạn độ sâu đệ quy.

        Returns:
            Danh sách premise indices đã dùng, hoặc None nếu không chứng minh được.
        """
        if _visited is None:
            _visited = set()

        if goal_predicate in _visited or max_depth <= 0:
            return None
        _visited.add(goal_predicate)

        # Base case: goal is already a known fact
        if goal_predicate in self.known:
            facts = self.known[goal_predicate]
            positive_facts = [f for f in facts if not f.is_negated]
            if positive_facts:
                return [positive_facts[0].premise_index]

        # Check derived facts
        for d in self.derived:
            if d.predicate == goal_predicate and not d.is_negated:
                return d.premises_involved

        # Try each rule where goal is consequent
        # For negated goals (NOT_X), search for rules with NOT_X as consequent
        # (i.e., contraposition rules). Do NOT strip NOT_ and search for positive rules.
        search_keys = []
        if goal_predicate.startswith("NOT_"):
            # Negated goal: look for contraposition rules in the graph
            clean = goal_predicate.replace("NOT_", "")
            if clean in self.graph:
                search_keys.append(clean)
        else:
            if goal_predicate in self.graph:
                search_keys.append(goal_predicate)

        for graph_key in search_keys:
            for rule in self.graph[graph_key].get('as_consequent', []):
                # Only use rules whose consequent matches the goal exactly
                if rule.consequent != goal_predicate:
                    continue
                if rule.blocked:
                    continue

                # Try to prove all antecedents
                all_premises = [rule.premise_index]
                all_proved = True

                for ant in rule.antecedents:
                    sub_proof = self.backward_chain(
                        ant, max_depth - 1, _visited.copy()
                    )
                    if sub_proof is None:
                        all_proved = False
                        break
                    all_premises.extend(sub_proof)

                if all_proved:
                    return list(set(all_premises))

        return None

    # ── Negation Handling ─────────────────────────────────────

    def handle_negations(self):
        """
        Xử lý negation: block rules khi antecedent bị phủ định.

        Closed World Assumption (CWA):
            Nếu ¬P(x) là fact → block tất cả rules cần P(x)
        """
        for fact in self.facts:
            if fact.is_negated:
                pred = fact.predicate
                if pred in self.graph:
                    for rule in self.graph[pred].get('as_antecedent', []):
                        rule.blocked = True
                        rule.block_reason = (
                            f"Antecedent '{pred}' negated by "
                            f"premise {fact.premise_index}"
                        )
                        logger.debug(
                            f"Blocked rule {rule.node_id}: {rule.block_reason}"
                        )

    # ── Contraposition Generation ────────────────────────────

    def generate_contrapositions(self) -> List[RuleNode]:
        """
        Sinh luật phản đề: từ A → B, sinh ¬B → ¬A.

        Quan trọng cho câu hỏi dạng:
            "If not X, then not Y" = contraposition of "Y → X"
        """
        contras = []
        for rule in list(self.rules):
            if len(rule.antecedents) == 1:
                contra = RuleNode(
                    antecedents=[f"NOT_{rule.consequent}"],
                    consequent=f"NOT_{rule.antecedents[0]}",
                    premise_index=rule.premise_index,
                    is_universal=rule.is_universal,
                    bound_variables=rule.bound_variables,
                )
                contras.append(contra)
                self.rules.append(contra)

                # Update graph
                neg_cons = f"NOT_{rule.consequent}"
                neg_ant = f"NOT_{rule.antecedents[0]}"
                if neg_cons not in self.graph:
                    self.graph[neg_cons] = {
                        'facts': [], 'as_antecedent': [], 'as_consequent': []
                    }
                self.graph[neg_cons]['as_antecedent'].append(contra)
                if neg_ant not in self.graph:
                    self.graph[neg_ant] = {
                        'facts': [], 'as_antecedent': [], 'as_consequent': []
                    }
                self.graph[neg_ant]['as_consequent'].append(contra)

        return contras

    # ── Proof Trace ──────────────────────────────────────────

    def get_proof_trace(self, goal_predicate: str) -> Dict:
        """
        Trả về proof trace cho một goal predicate.

        Returns:
            Dict với keys: provable, premises_used, depth, trace_text
        """
        # Try forward chain first (if not done)
        if not self.derived:
            self.handle_negations()
            self.generate_contrapositions()
            self.forward_chain()

        # Check if goal is derived
        for d in self.derived:
            if d.predicate == goal_predicate and not d.is_negated:
                return {
                    'provable': True,
                    'premises_used': sorted(
                        [p for p in d.premises_involved if p > 0]
                    ),
                    'depth': d.depth,
                    'method': 'forward_chaining',
                }

        # Try backward chaining
        bc_result = self.backward_chain(goal_predicate)
        if bc_result is not None:
            return {
                'provable': True,
                'premises_used': sorted([p for p in bc_result if p > 0]),
                'depth': len(bc_result),
                'method': 'backward_chaining',
            }

        return {
            'provable': False,
            'premises_used': [],
            'depth': 0,
            'method': 'none',
        }

    def can_prove_negation(self, goal_predicate: str) -> Dict:
        """
        Kiểm tra xem phủ định của goal predicate có chứng minh được không.

        Nếu ¬P(x) đã được suy ra (hoặc là fact gốc), trả về proof trace
        cho phủ định → cho phép trả lời "No" thay vì "Unknown".

        Returns:
            Dict với keys: negated, premises_used, reason
        """
        # Ensure forward chaining has been done
        if not self.derived:
            self.handle_negations()
            self.generate_contrapositions()
            self.forward_chain()

        # Check 1: Is the negated predicate a known fact?
        if goal_predicate in self.known:
            neg_facts = [f for f in self.known[goal_predicate] if f.is_negated]
            if neg_facts:
                return {
                    'negated': True,
                    'premises_used': sorted(
                        [f.premise_index for f in neg_facts if f.premise_index > 0]
                    ),
                    'reason': f"¬{goal_predicate} is an explicit negated fact.",
                }

        # Check 2: Is NOT_{goal} derived?
        neg_goal = f"NOT_{goal_predicate}"
        for d in self.derived:
            if d.predicate == neg_goal or \
               (d.predicate == goal_predicate and d.is_negated):
                return {
                    'negated': True,
                    'premises_used': sorted(
                        [p for p in d.premises_involved if p > 0]
                    ),
                    'reason': f"¬{goal_predicate} derived via {d.rule_used}.",
                }

        # Check 3: Try backward chaining for NOT_{goal}
        bc_result = self.backward_chain(neg_goal)
        if bc_result is not None:
            return {
                'negated': True,
                'premises_used': sorted([p for p in bc_result if p > 0]),
                'reason': f"¬{goal_predicate} proved by backward chaining.",
            }

        return {
            'negated': False,
            'premises_used': [],
            'reason': 'Cannot prove negation.',
        }

    def check_missing_conditions(self, goal_predicate: str) -> List[str]:
        """
        Tìm các antecedent conditions bị thiếu để goal có thể suy ra.

        Hữu ích để phát hiện: "eligible for trainer" nhưng thiếu "has_trainer".

        DISJUNCTIVE PATH HANDLING:
            If multiple rules can derive the goal (OR paths), missing conditions
            are only reported if ALL alternative paths are blocked. If at least
            one path is fully satisfied, no missing conditions are returned.

        Returns:
            Danh sách tên predicates bị thiếu (không có fact hoặc derived).
            Empty list if at least one path to the goal is fully satisfied.
        """
        clean_goal = goal_predicate.replace("NOT_", "")

        if clean_goal not in self.graph:
            return []

        rules_for_goal = self.graph[clean_goal].get('as_consequent', [])
        if not rules_for_goal:
            return []

        # Check each alternative rule path
        all_paths_missing = []
        for rule in rules_for_goal:
            path_missing = []
            for ant in rule.antecedents:
                # Check if antecedent is satisfied
                in_known = ant in self.known and any(
                    not f.is_negated for f in self.known[ant]
                )
                in_derived = any(
                    d.predicate == ant and not d.is_negated
                    for d in self.derived
                )
                if not in_known and not in_derived:
                    path_missing.append(ant)

            if not path_missing:
                # This path is fully satisfied → goal is provable
                # No missing conditions to report
                return []

            all_paths_missing.append(path_missing)

        # All paths have missing conditions → return the union of missing conditions
        # from the path with the fewest missing conditions (the "closest" path)
        if all_paths_missing:
            best_path = min(all_paths_missing, key=len)
            return best_path

        return []

    def get_all_derived_predicates(self) -> Set[str]:
        """Trả về tập tất cả predicates đã suy ra được."""
        if not self.derived:
            self.handle_negations()
            self.forward_chain()

        result = set()
        for fact_list in self.known.values():
            for f in fact_list:
                if not f.is_negated:
                    result.add(f.predicate)
        for d in self.derived:
            if not d.is_negated:
                result.add(d.predicate)
        return result

    def get_all_used_premises(self) -> List[int]:
        """Trả về danh sách tất cả premise indices đã dùng."""
        used = set()
        for fact in self.facts:
            used.add(fact.premise_index)
        for d in self.derived:
            used.update(d.premises_involved)
        return sorted(p for p in used if p > 0)
