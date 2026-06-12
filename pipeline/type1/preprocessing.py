"""
Preprocessing — Tiền xử lý dữ liệu cho Track 1 Logic-Based QA.

Module này cung cấp các tiện ích:
    1. Text normalization: chuẩn hóa tên, casing, khoảng trắng.
    2. Premise Graph Filter: lọc premises không liên quan dựa trên
       thực thể (entity) được hỏi trong câu hỏi.
    3. Strict Verification Hints: phát hiện các mẫu nguy hiểm
       (eligibility vs actuality, conditional vs ground truth).

References:
    - Closed World Assumption (CWA): Clark, 1978
    - Entity-Aware Filtering: Russell & Norvig, AIMA 4th Ed.
"""

import re
from typing import List, Dict, Tuple, Set, Optional
from loguru import logger


# ══════════════════════════════════════════════════════════════
# Text Normalization
# ══════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    """
    Chuẩn hóa text: loại bỏ khoảng trắng thừa, chuẩn hóa dấu câu.
    
    Args:
        text: Chuỗi cần chuẩn hóa.
    Returns:
        Chuỗi đã chuẩn hóa.
    """
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    # Normalize Unicode arrows
    text = text.replace('→', '→').replace('−>', '→')
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    return text


def normalize_premises(premises: List[str]) -> List[str]:
    """Chuẩn hóa danh sách premises."""
    return [normalize_text(p) for p in premises]


# ══════════════════════════════════════════════════════════════
# Entity Extraction
# ══════════════════════════════════════════════════════════════

# Common FOL keywords / quantifiers to exclude from entity extraction
_FOL_KEYWORDS = {
    'ForAll', 'Exists', 'Not', 'And', 'Or', 'Implies',
    'BoolSort', 'IntSort', 'RealSort', 'Entity',
    'True', 'False',
}

# Common predicate prefixes that look like proper names but aren't
_PREDICATE_PREFIXES = {
    'has', 'is', 'can', 'will', 'must', 'should', 'does',
    'not', 'if', 'then', 'all', 'some', 'any', 'every',
}


def extract_entities_from_fol(fol_premises: List[str]) -> Set[str]:
    """
    Trích xuất tên thực thể (entities) từ danh sách FOL premises.
    
    Entities là các hằng số (constants) — tên riêng viết hoa đầu
    (e.g., John, Sophia, Alex, PhD, MSc, BA).
    
    Args:
        fol_premises: Danh sách premises dạng FOL.
    Returns:
        Tập hợp tên entities tìm được.
    """
    entities = set()
    
    for fol in fol_premises:
        # Match arguments inside predicate calls: pred(Arg1, Arg2, ...)
        for match in re.finditer(r'\(([^()]*)\)', fol):
            args_str = match.group(1)
            # Split by comma
            for arg in args_str.split(','):
                arg = arg.strip()
                # Entity: starts with uppercase, is not a FOL keyword
                if (arg and arg[0].isupper() and
                    arg not in _FOL_KEYWORDS and
                    not arg.startswith('∀') and
                    not arg.startswith('∃') and
                    len(arg) > 1):
                    entities.add(arg)
                # Also check for quoted string entities
                elif arg.startswith("'") or arg.startswith('"'):
                    clean = arg.strip("'\"")
                    if clean:
                        entities.add(clean)
    
    return entities


def extract_entities_from_nl(text: str) -> Set[str]:
    """
    Trích xuất tên thực thể từ text NL (câu hỏi hoặc premise).
    
    Sử dụng heuristic: tìm các tên riêng (proper nouns) viết hoa
    mà không phải đầu câu.
    
    Args:
        text: Chuỗi NL.
    Returns:
        Tập hợp tên entities tìm được.
    """
    entities = set()
    
    # Match capitalized words that aren't at the start of a sentence
    # Also match common patterns: Dr. John, Professor Smith
    for match in re.finditer(
        r'(?:(?:Dr\.|Prof\.|Professor|Mr\.|Mrs\.|Ms\.)\s+)?'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        text
    ):
        name = match.group(1)
        # Filter out common English words that start sentences
        if name.lower() not in {
            'the', 'if', 'then', 'all', 'some', 'based', 'which',
            'does', 'can', 'will', 'is', 'are', 'has', 'have',
            'according', 'students', 'faculty', 'members', 'anyone',
            'every', 'option', 'statement', 'conclusion', 'premise',
            'premises', 'question', 'answer', 'yes', 'no', 'unknown',
        }:
            entities.add(name)
    
    return entities


# ══════════════════════════════════════════════════════════════
# Premise Graph Filter
# ══════════════════════════════════════════════════════════════

def build_premise_entity_map(
    premises_fol: List[str],
    premises_nl: List[str],
) -> Dict[int, Set[str]]:
    """
    Xây dựng mapping: premise_index → {entities}.
    
    Mỗi premise được gán tập entities nó đề cập đến.
    Premises là luật phổ quát (ForAll) sẽ không bị loại bỏ
    vì chúng có thể áp dụng cho bất kỳ entity nào.
    
    Args:
        premises_fol: Danh sách premises FOL.
        premises_nl: Danh sách premises NL.
    Returns:
        Dict mapping premise index (0-based) → set of entity names.
    """
    entity_map: Dict[int, Set[str]] = {}
    
    for i, (fol, nl) in enumerate(zip(premises_fol, premises_nl)):
        fol_entities = extract_entities_from_fol([fol])
        nl_entities = extract_entities_from_nl(nl)
        combined = fol_entities | nl_entities
        entity_map[i] = combined
    
    return entity_map


def is_universal_premise(fol: str) -> bool:
    """
    Kiểm tra xem premise có phải là luật phổ quát (universal rule) không.
    
    Universal rules (chứa ForAll/∀ + implication) áp dụng cho mọi entity
    → KHÔNG được lọc bỏ.
    
    Args:
        fol: Chuỗi FOL premise.
    Returns:
        True nếu là universal rule.
    """
    has_quantifier = '∀' in fol or 'ForAll' in fol
    has_impl = '→' in fol or '->' in fol
    return has_quantifier and has_impl


def filter_premises_for_question(
    premises_fol: List[str],
    premises_nl: List[str],
    question: str,
    entity_map: Optional[Dict[int, Set[str]]] = None,
) -> Tuple[List[str], List[str], List[int]]:
    """
    Lọc premises liên quan đến câu hỏi dựa trên entity overlap.
    
    Logic:
        - Giữ TẤT CẢ premises là universal rules (ForAll + →).
        - Giữ premises có entity trùng với entity trong câu hỏi.
        - Nếu câu hỏi không đề cập entity cụ thể nào, giữ tất cả.
    
    Args:
        premises_fol: Danh sách premises FOL đầy đủ.
        premises_nl: Danh sách premises NL đầy đủ.
        question: Câu hỏi.
        entity_map: Mapping premise → entities (nếu đã có).
    Returns:
        Tuple (filtered_fol, filtered_nl, original_indices).
    """
    if entity_map is None:
        entity_map = build_premise_entity_map(premises_fol, premises_nl)
    
    # Extract entities from question
    q_entities = extract_entities_from_nl(question)
    
    # If question has no specific entities, keep all premises
    if not q_entities:
        indices = list(range(len(premises_fol)))
        return premises_fol, premises_nl, indices
    
    # Filter: keep universal rules + entity-relevant premises
    filtered_fol = []
    filtered_nl = []
    kept_indices = []
    
    for i in range(len(premises_fol)):
        # Always keep universal rules
        if is_universal_premise(premises_fol[i]):
            filtered_fol.append(premises_fol[i])
            filtered_nl.append(premises_nl[i])
            kept_indices.append(i)
            continue
        
        # Keep if premise mentions any entity from the question
        premise_entities = entity_map.get(i, set())
        if premise_entities & q_entities:  # intersection
            filtered_fol.append(premises_fol[i])
            filtered_nl.append(premises_nl[i])
            kept_indices.append(i)
            continue
        
        # Keep if premise has no entities (general facts)
        if not premise_entities:
            filtered_fol.append(premises_fol[i])
            filtered_nl.append(premises_nl[i])
            kept_indices.append(i)
    
    # Safety: if filtering removed too many premises, keep all
    if len(filtered_fol) < 2:
        logger.debug(
            f"Premise filtering too aggressive ({len(filtered_fol)} remaining), "
            f"keeping all {len(premises_fol)} premises."
        )
        return premises_fol, premises_nl, list(range(len(premises_fol)))
    
    logger.debug(
        f"Premise filter: {len(premises_fol)} → {len(filtered_fol)} "
        f"(entities: {q_entities})"
    )
    
    return filtered_fol, filtered_nl, kept_indices


# ══════════════════════════════════════════════════════════════
# Strict Verification Hints
# ══════════════════════════════════════════════════════════════

def detect_eligibility_vs_actuality(
    premises_nl: List[str],
    question: str,
) -> List[str]:
    """
    Phát hiện và sinh cảnh báo khi premises chứa mẫu
    "eligible for X" nhưng KHÔNG có premise xác nhận "has X".
    
    Đây là nguồn gốc chính của hallucination: LLM nhầm lẫn
    "eligible for a trainer" với "has a trainer".
    
    Args:
        premises_nl: Danh sách premises NL.
        question: Câu hỏi.
    Returns:
        Danh sách hints (cảnh báo) để chèn vào prompt.
    """
    hints = []
    
    # Pattern: "eligible for X" vs "has X" / "assigned X"
    eligible_patterns = re.findall(
        r'(?:eligible|qualified|entitled)\s+(?:for|to)\s+([\w\s]+?)(?:\.|,|$)',
        ' '.join(premises_nl),
        re.IGNORECASE,
    )
    
    has_patterns = re.findall(
        r'(?:has|have|assigned|received|obtained|given)\s+([\w\s]+?)(?:\.|,|$)',
        ' '.join(premises_nl),
        re.IGNORECASE,
    )
    
    for elig in eligible_patterns:
        elig_clean = elig.strip().lower()
        found_actual = False
        for has_p in has_patterns:
            if elig_clean in has_p.strip().lower():
                found_actual = True
                break
        if not found_actual:
            hints.append(
                f"⚠️ CAUTION: Premises mention eligibility for '{elig.strip()}' "
                f"but NO premise confirms actually having/receiving it. "
                f"'Eligible for X' ≠ 'Has X'."
            )
    
    return hints


def detect_strongest_vs_fewest(question: str) -> Optional[str]:
    """
    Phát hiện tiêu chí đặc biệt trong câu hỏi MCQ.
    
    Args:
        question: Câu hỏi.
    Returns:
        Hint text hoặc None.
    """
    q_lower = question.lower()
    
    if 'fewest premises' in q_lower or 'fewest premise' in q_lower:
        return (
            "🎯 QUESTION CRITERION: 'fewest premises' — "
            "You MUST count the exact number of premises each valid option needs "
            "and select the option requiring the LEAST number of premises."
        )
    elif 'strongest conclusion' in q_lower or 'strongest' in q_lower:
        return (
            "🎯 QUESTION CRITERION: 'strongest conclusion' — "
            "Derive ALL possible conclusions from the premises. "
            "The 'strongest' is the FINAL conclusion at the end of the logical chain "
            "(the one that uses the MOST premises and is the most specific)."
        )
    elif 'correct conclusion' in q_lower or 'logically follows' in q_lower:
        return (
            "🎯 QUESTION CRITERION: 'correct conclusion' / 'logically follows' — "
            "Select any option that is validly derivable from the premises."
        )
    elif 'logically valid' in q_lower:
        return (
            "🎯 QUESTION CRITERION: 'logically valid' — "
            "Select the option that can be formally derived using logical rules "
            "(Modus Ponens, Contraposition, etc.) from the given premises."
        )
    
    return None


def generate_preprocessing_hints(
    premises_nl: List[str],
    premises_fol: List[str],
    question: str,
) -> List[str]:
    """
    Tổng hợp tất cả preprocessing hints cho một câu hỏi.
    
    Args:
        premises_nl: Danh sách premises NL.
        premises_fol: Danh sách premises FOL.
        question: Câu hỏi.
    Returns:
        Danh sách hints.
    """
    hints = []
    
    # Detect eligibility vs actuality
    elig_hints = detect_eligibility_vs_actuality(premises_nl, question)
    hints.extend(elig_hints)
    
    # Detect question criterion
    criterion_hint = detect_strongest_vs_fewest(question)
    if criterion_hint:
        hints.append(criterion_hint)
    
    return hints
