"""
FOL Normalizer - Chuẩn hóa các ký hiệu First-Order Logic.

Chuyển đổi các FOL notation đa dạng trong dataset (Unicode, Text, Hybrid)
về một format chuẩn thống nhất, phục vụ cho việc parse và dịch sang Z3.

References:
    - LINC: Olausson et al., 2023 (NL → FOL Translation)
    - LogicLLaMA: Fine-tuned NL-FOL translation, 2024
"""

import re
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class FOLStyle(Enum):
    """Phân loại style ký hiệu FOL."""
    UNICODE = "unicode"          # ∀x (P(x) → Q(x))
    TEXT = "text"                # ForAll(x, P(x) → Q(x))
    HYBRID = "hybrid"            # ForAll(x, P(x) ∧ Q(x) → R(x))
    ATOMIC = "atomic"            # P(John)
    NEGATED_ATOMIC = "neg_atom"  # ¬P(John)
    ARITHMETIC = "arithmetic"    # membership_duration(Alex) = 8


@dataclass
class NormalizedFOL:
    """Kết quả chuẩn hóa một biểu thức FOL."""
    original: str
    style: FOLStyle
    normalized: str
    predicates: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    is_rule: bool = False        # True nếu là implication rule (A → B)
    is_fact: bool = False        # True nếu là atomic fact
    is_negated: bool = False     # True nếu bắt đầu bằng ¬
    has_arithmetic: bool = False # True nếu có ≥, ≤, =


# ──────────────────────────────────────────────────────────────
# Unicode → Text mapping
# ──────────────────────────────────────────────────────────────
UNICODE_TO_TEXT: Dict[str, str] = {
    '∀': 'ForAll',
    '∃': 'Exists',
    '→': '->',
    '∧': '&',
    '∨': '|',
    '¬': '~',
    '↔': '<->',
    '≥': '>=',
    '≤': '<=',
    '≠': '!=',
}

# Các keyword của FOL (không phải tên predicate)
FOL_KEYWORDS: Set[str] = {
    'ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies', 'Iff',
    'True', 'False', 'forall', 'exists',
}


class FOLNormalizer:
    """
    Chuẩn hóa các biểu thức FOL từ dataset về format thống nhất.

    Pipeline chuẩn hóa:
        Raw FOL → Detect Style → Unicode→Text → Normalize Spacing → Output

    Attributes:
        unicode_map: Bảng ánh xạ Unicode → ASCII/Text.
    """

    def __init__(self):
        self.unicode_map = UNICODE_TO_TEXT.copy()

    # ── Style Detection ───────────────────────────────────────

    def detect_style(self, fol: str) -> FOLStyle:
        """Nhận diện style notation của biểu thức FOL."""
        has_unicode_quant = bool(re.search(r'[∀∃]', fol))
        has_unicode_op = bool(re.search(r'[→∧∨¬↔]', fol))
        has_text_quant = bool(re.search(r'\bForAll\b|\bExists\b', fol))
        has_arith = bool(re.search(r'[≥≤]|>=|<=', fol))
        has_eq = bool(re.search(r'(?<!=)=(?!=)', fol))  # single = not ==
        has_impl = '->' in fol or '→' in fol

        # Negated atomic: starts with ¬ or ~ and no quantifier
        stripped = fol.strip()
        if (stripped.startswith('¬') or stripped.startswith('~')) and \
           not has_unicode_quant and not has_text_quant and not has_impl:
            return FOLStyle.NEGATED_ATOMIC

        # Hybrid: both unicode and text styles
        if (has_unicode_quant or has_unicode_op) and has_text_quant:
            return FOLStyle.HYBRID
        if has_unicode_quant:
            return FOLStyle.UNICODE
        if has_text_quant:
            if has_unicode_op:
                return FOLStyle.HYBRID
            return FOLStyle.TEXT

        # Arithmetic: has numeric comparison
        if has_arith or (has_eq and re.search(r'=\s*\d+', fol)):
            return FOLStyle.ARITHMETIC

        # Atomic: no quantifiers, no implications
        if not has_impl:
            return FOLStyle.ATOMIC

        # Default to UNICODE if it has unicode operators
        if has_unicode_op:
            return FOLStyle.UNICODE

        return FOLStyle.ATOMIC

    # ── Unicode Normalization ────────────────────────────────

    def normalize_unicode(self, fol: str) -> str:
        """Thay thế tất cả ký tự Unicode bằng text equivalent."""
        result = fol
        for uc, txt in self.unicode_map.items():
            result = result.replace(uc, txt)
        return result

    # ── Predicate & Variable Extraction ──────────────────────

    def extract_predicates(self, fol: str) -> List[str]:
        """Trích xuất tất cả tên predicate từ biểu thức FOL."""
        # Match identifier followed by (
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, fol)
        # Filter out FOL keywords
        return list(dict.fromkeys(
            m for m in matches if m not in FOL_KEYWORDS
        ))

    def extract_variables_and_constants(
        self, fol: str
    ) -> Tuple[List[str], List[str]]:
        """
        Tách biến bị ràng buộc (bound variables) và hằng số (constants).

        Returns:
            (bound_variables, constants)
        """
        # Bound variables: appear after ForAll/Exists
        quant_pat = r'(?:ForAll|Exists)\s*\(?\s*([a-z][a-z0-9_]*)'
        bound_vars = list(set(re.findall(quant_pat, fol)))

        # Constants: capitalized identifiers used as arguments
        # Match args inside predicate calls
        arg_pat = r'(?:[\(,])\s*([A-Z][a-zA-Z0-9_]*)\s*(?=[,\)])'
        constants = list(set(re.findall(arg_pat, fol)))

        return bound_vars, constants

    # ── Classification ───────────────────────────────────────

    def is_implication(self, fol: str) -> bool:
        """Check if FOL contains an implication (→ or ->)."""
        return '->' in fol or '→' in fol

    def is_atomic_fact(self, fol: str) -> bool:
        """Check if FOL is an atomic ground fact like P(John)."""
        style = self.detect_style(fol)
        return style in (FOLStyle.ATOMIC, FOLStyle.NEGATED_ATOMIC,
                         FOLStyle.ARITHMETIC)

    # ── Main Normalization ───────────────────────────────────

    def normalize(self, fol: str) -> NormalizedFOL:
        """
        Thực hiện chuẩn hóa đầy đủ một biểu thức FOL.

        Args:
            fol: Chuỗi FOL gốc từ dataset.

        Returns:
            NormalizedFOL với thông tin đầy đủ.
        """
        style = self.detect_style(fol)
        predicates = self.extract_predicates(fol)
        variables, constants = self.extract_variables_and_constants(fol)

        # Step 1: Unicode normalization
        normalized = self.normalize_unicode(fol)

        # Step 2: Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Step 3: Classify
        has_impl = self.is_implication(fol)
        is_neg = fol.strip().startswith('¬') or fol.strip().startswith('~')
        has_arith = bool(re.search(r'[≥≤]|>=|<=', fol)) or \
                    bool(re.search(r'(?<!=)=\s*\d+', fol))

        return NormalizedFOL(
            original=fol,
            style=style,
            normalized=normalized,
            predicates=predicates,
            variables=variables,
            constants=constants,
            is_rule=has_impl,
            is_fact=not has_impl and style in (
                FOLStyle.ATOMIC, FOLStyle.NEGATED_ATOMIC,
                FOLStyle.ARITHMETIC
            ),
            is_negated=is_neg,
            has_arithmetic=has_arith,
        )

    def normalize_batch(
        self, premises_fol: List[str]
    ) -> List[NormalizedFOL]:
        """Chuẩn hóa toàn bộ danh sách premises."""
        results = []
        for fol in premises_fol:
            try:
                results.append(self.normalize(fol))
            except Exception as e:
                logger.warning(f"FOL normalization failed for: {fol} | {e}")
                results.append(NormalizedFOL(
                    original=fol,
                    style=FOLStyle.ATOMIC,
                    normalized=fol,
                    predicates=[],
                    variables=[],
                    constants=[],
                ))
        return results

    # ── Aggregate Metadata ───────────────────────────────────

    def extract_all_metadata(
        self, normalized_list: List[NormalizedFOL]
    ) -> Dict:
        """
        Trích xuất metadata tổng hợp từ tất cả premises đã chuẩn hóa.

        Returns:
            Dict chứa predicates, variables, constants, facts, rules.
        """
        all_predicates: Dict[str, Set[int]] = {}  # name → set of arities
        all_constants: Set[str] = set()
        all_variables: Set[str] = set()
        facts = []
        rules = []

        for i, nf in enumerate(normalized_list):
            for pred in nf.predicates:
                if pred not in all_predicates:
                    all_predicates[pred] = set()
                # Count arity from original
                arity = self._count_arity(nf.original, pred)
                all_predicates[pred].add(arity)

            all_constants.update(nf.constants)
            all_variables.update(nf.variables)

            if nf.is_fact:
                facts.append(i)
            if nf.is_rule:
                rules.append(i)

        return {
            'predicates': {k: max(v) for k, v in all_predicates.items()},
            'constants': list(all_constants),
            'variables': list(all_variables),
            'fact_indices': facts,
            'rule_indices': rules,
            'total': len(normalized_list),
        }

    def _count_arity(self, fol: str, predicate: str) -> int:
        """Đếm số argument (arity) của một predicate trong FOL string."""
        # Find predicate(...) and count commas + 1
        pattern = re.escape(predicate) + r'\s*\(([^)]*)\)'
        match = re.search(pattern, fol)
        if match:
            args = match.group(1).strip()
            if not args:
                return 0
            return args.count(',') + 1
        return 1  # default
