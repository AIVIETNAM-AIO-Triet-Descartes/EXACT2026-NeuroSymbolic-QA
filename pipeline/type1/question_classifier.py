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
