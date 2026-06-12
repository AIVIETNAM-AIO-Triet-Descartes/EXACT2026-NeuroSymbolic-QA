"""
Question Classifier - Phân loại câu hỏi logic.

Phân loại câu hỏi trong dataset thành các nhóm:
    - MCQ: Multiple Choice (A/B/C/D)
    - YES_NO: Yes/No verification
    - UNKNOWN: Có thể trả lời "Unknown"
    - OPEN: Câu hỏi mở

Mỗi loại câu hỏi sẽ được xử lý bằng chiến lược suy luận riêng.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class QuestionType(Enum):
    """Loại câu hỏi."""
    MCQ = "mcq"           # Multiple choice A/B/C/D
    YES_NO = "yes_no"     # Does X hold? Can X do Y?
    OPEN = "open"         # Open-ended


@dataclass
class ClassifiedQuestion:
    """Kết quả phân loại một câu hỏi."""
    original: str
    question_type: QuestionType
    stem: str                              # Phần đề bài (không bao gồm options)
    options: Optional[Dict[str, str]]      # {'A': '...', 'B': '...', ...}
    keywords: List[str]                    # Từ khóa quan trọng


# ──────────────────────────────────────────────────────────────
# Patterns cho phân loại
# ──────────────────────────────────────────────────────────────

MCQ_OPTION_PATTERN = re.compile(
    r'\n([A-D])[\.\)]\s*(.+?)(?=\n[A-D][\.\)]|\Z)', re.DOTALL
)

YES_NO_PATTERNS = [
    r'^Does\b',
    r'^Do\b',
    r'^Can\b',
    r'^Is\b',
    r'^Are\b',
    r'^Will\b',
    r'^Should\b',
    r'^Has\b',
    r'^Have\b',
    r'according to the premises\?',
    r', according to the premises\?',
    r'based on (?:the|his|her|its) .+?\?',
    r'Does (?:the|it) (?:follow|hold|logically)',
    r'Does the logical (?:chain|sequence|progression)',
]


class QuestionClassifier:
    """
    Phân loại câu hỏi logic thành MCQ, Yes/No, hoặc Open-ended.

    Thuật toán:
        1. Kiểm tra có options A/B/C/D → MCQ
        2. Kiểm tra bắt đầu bằng Does/Can/Is... → YES_NO
        3. Mặc định → OPEN
    """

    def __init__(self):
        self.yes_no_patterns = [
            re.compile(p, re.IGNORECASE) for p in YES_NO_PATTERNS
        ]

    def classify(self, question: str) -> ClassifiedQuestion:
        """
        Phân loại một câu hỏi.

        Args:
            question: Chuỗi câu hỏi gốc từ dataset.

        Returns:
            ClassifiedQuestion chứa loại, stem, options, keywords.
        """
        # Check MCQ first
        options = self._extract_options(question)
        if options:
            stem = self._extract_stem(question)
            return ClassifiedQuestion(
                original=question,
                question_type=QuestionType.MCQ,
                stem=stem,
                options=options,
                keywords=self._extract_keywords(stem),
            )

        # Default: All non-MCQ questions are treated as Yes/No.
        # Previously, questions starting with "According to..." or "Statement:"
        # were classified as OPEN and bypassed the Logic Tree entirely.
        # This caused the pipeline to rely solely on LLM CoT, which is less
        # reliable than the formal reasoning engine for these question types.
        return ClassifiedQuestion(
            original=question,
            question_type=QuestionType.YES_NO,
            stem=question.strip(),
            options=None,
            keywords=self._extract_keywords(question),
        )

    def classify_batch(
        self, questions: List[str]
    ) -> List[ClassifiedQuestion]:
        """Phân loại nhiều câu hỏi cùng lúc."""
        return [self.classify(q) for q in questions]

    # ── Private helpers ───────────────────────────────────────

    def _extract_options(self, question: str) -> Optional[Dict[str, str]]:
        """Trích xuất options A/B/C/D nếu có."""
        matches = MCQ_OPTION_PATTERN.findall(question)
        if len(matches) >= 2:  # At least 2 options to be MCQ
            return {key: val.strip() for key, val in matches}
        return None

    def _extract_stem(self, question: str) -> str:
        """Trích xuất phần đề bài MCQ (trước options)."""
        # Find position of first option
        match = re.search(r'\n[A-D][\.\)]', question)
        if match:
            return question[:match.start()].strip()
        return question.strip()

    def _is_yes_no(self, question: str) -> bool:
        """Kiểm tra câu hỏi có phải dạng Yes/No không."""
        return any(
            pat.search(question.strip()) for pat in self.yes_no_patterns
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Trích xuất từ khóa quan trọng cho premise selection.

        Heuristic: danh từ/tính từ xuất hiện trong text liên quan
        đến các predicate trong premises.
        """
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'shall', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'that', 'which',
            'who', 'whom', 'this', 'these', 'those', 'it', 'its',
            'if', 'then', 'than', 'but', 'and', 'or', 'not', 'no',
            'all', 'each', 'every', 'any', 'both', 'such', 'as',
            'based', 'according', 'premises', 'above', 'following',
            'conclusion', 'statement', 'correct', 'follows',
        }

        words = re.findall(r'[a-zA-Z]+', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]


def detect_answer_type(answer: str) -> str:
    """
    Phát hiện loại đáp án.

    Returns:
        'mcq_option' | 'yes' | 'no' | 'unknown' | 'other'
    """
    answer = answer.strip()
    if answer in ('A', 'B', 'C', 'D'):
        return 'mcq_option'
    if answer.lower() == 'yes':
        return 'yes'
    if answer.lower() == 'no':
        return 'no'
    if answer.lower() == 'unknown':
        return 'unknown'
    return 'other'


def sanitize_and_snap_answer(
    answer: Optional[str], 
    question_type: str, 
    options: Optional[Dict[str, str]] = None,
    explanation: Optional[str] = None
) -> str:
    """
    Sanitize and snap the answer strictly to the expected submission format.
    
    If MCQ:
        - Must be 'A', 'B', 'C', or 'D'.
        - If not, check if it matches the text or keyword of any option.
        - If not, try to extract from the explanation.
        - Default fallback to 'A'.
    If Yes/No:
        - Must be 'Yes', 'No', or 'Unknown'.
        - If not, try to map from words like "true"/"false" or extract from explanation.
        - Default fallback to 'Unknown'.
    """
    if not answer:
        answer = ""
        
    answer_clean = answer.strip()
    
    # ── Case 1: Yes/No question ──
    if question_type != "mcq":
        # First check direct match
        val = answer_clean.lower()
        if val in ('yes', 'no', 'unknown'):
            return val.capitalize()
            
        # Try to clean punctuation
        val_clean = re.sub(r'[^a-zA-Z]', '', val)
        if val_clean in ('yes', 'no', 'unknown'):
            return val_clean.capitalize()
            
        # Check explanation for hints
        expl_lower = (explanation or "").lower()
        # Check last few sentences
        lines = [l.strip() for l in expl_lower.split('\n') if l.strip()]
        last_part = " ".join(lines[-2:]) if len(lines) >= 2 else expl_lower
        
        # Look for explicit conclusion sentences in explanation
        if any(w in last_part for w in ['therefore, yes', 'the answer is yes', 'does qualify', 'is valid', 'logically follows', 'is true']):
            return 'Yes'
        if any(w in last_part for w in ['therefore, no', 'the answer is no', 'does not qualify', 'is invalid', 'cannot be concluded', 'is false']):
            return 'No'
            
        # Broader search in last part
        if 'yes' in last_part or 'true' in last_part:
            return 'Yes'
        if 'no' in last_part or 'false' in last_part:
            return 'No'
            
        # Default fallback
        return 'Unknown'
        
    # ── Case 2: MCQ question ──
    # Options dict maps 'A', 'B', 'C', 'D' -> option text
    if not options:
        # If options are not provided, we can only clean the letter
        match = re.search(r'\b([A-D])\b', answer_clean, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return 'A' # fallback
        
    # Standardize options keys to uppercase
    options = {k.upper(): v for k, v in options.items()}
    
    # Check if answer matches one of the option keys directly
    ans_upper = answer_clean.upper()
    if ans_upper in options:
        return ans_upper
        
    # Check if it starts with an option key, like "A." or "A)" or "(A)"
    for key in options:
        if ans_upper == key or ans_upper.startswith(f"{key}.") or ans_upper.startswith(f"{key})") or ans_upper == f"({key})":
            return key
            
    # Check if the answer matches the text of one of the options (either exact or substring or high similarity)
    ans_lower = answer_clean.lower()
    for key, val in options.items():
        val_lower = val.strip().lower()
        if ans_lower == val_lower or val_lower in ans_lower or ans_lower in val_lower:
            return key

    # Check word overlap / Jaccard-like similarity between answer and option text
    best_key = None
    best_overlap = -1
    answer_words = set(re.findall(r'\w+', ans_lower))
    # Ignore stop words to make matching more robust
    stop_words = {'if', 'then', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'it', 'must', 'be', 'not'}
    answer_words = answer_words - stop_words
    
    for key, val in options.items():
        opt_words = set(re.findall(r'\w+', val.strip().lower())) - stop_words
        overlap = len(answer_words.intersection(opt_words))
        if overlap > best_overlap:
            best_overlap = overlap
            best_key = key
            
    if best_overlap > 0:
        return best_key
        
    # If the answer is "Yes" or "No", see if any option starts with yes/no or represents affirmation/negation
    if ans_lower in ('yes', 'no'):
        for key, val in options.items():
            if val.strip().lower().startswith(ans_lower):
                return key
                
    # If still not found, try to extract any option letter from the explanation
    if explanation:
        # Look for patterns like "ANSWER: B" or "correct option is B" or similar in the explanation
        local_patterns = [
            r'(?i)\**ANSWER:\**\s*\**([A-D])\**\b',
            r'(?i)\**ANSWER:\**\s*\**(Yes|No|Unknown)\**',
            r'(?i)(?:answer is|correct answer is|conclusion is|option is|correct option is|choice is|correct choice is)\s*[:\s]*\**([A-D])\**\b',
            r'(?i)(?:answer is|correct answer is|conclusion is|option is|correct option is|choice is|correct choice is)\s*[:\s]*\**(Yes|No|Unknown)\**',
            r'(?i)\b(Yes|No|Unknown)\s*[,.]?\s*$',
            r'^([A-D])\s*[.\)]',
        ]
            
        for pattern in local_patterns:
            match = re.search(pattern, explanation, re.IGNORECASE | re.MULTILINE)
            if match:
                ans_extracted = match.group(1).strip().upper()
                if ans_extracted in options:
                    return ans_extracted
                    
        # Check last few lines for any single letter A, B, C, D
        lines = [l.strip() for l in explanation.split('\n') if l.strip()]
        if lines:
            last_line = lines[-1].strip()
            for key in options:
                if last_line == key or last_line.startswith(f"{key}.") or last_line.startswith(f"{key})"):
                    return key

    # Default fallback: return first option key (usually 'A')
    return list(options.keys())[0] if options else 'A'

