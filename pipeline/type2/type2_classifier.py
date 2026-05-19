# src/preprocessor/physics_classifier.py
#
# TÁI DỤNG TỪ type1_classifier.py:
#   - ClassifiedQuestion  (dataclass, import để typing)
#   - QuestionClassifier  (base class) → kế thừa _extract_keywords()
#
# _extract_keywords() không được copy lại — gọi qua super() chain.
# Nếu type1_classifier thay đổi stop_words, type2 bị ảnh hưởng theo.

from pipeline.type1.type1_classifier import (
    ClassifiedQuestion,
    QuestionClassifier,   # kế thừa _extract_keywords()
)
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PhysicsQuestionType(Enum):
    SINGLE_FORMULA = "single_formula"   # V = IR, E = 0.5*C*U^2
    MULTI_STEP     = "multi_step"       # Cần nhiều công thức liên tiếp
    CIRCUIT        = "circuit"          # Mạch nối tiếp/song song
    ELECTROSTATIC  = "electrostatic"    # Tĩnh điện


@dataclass
class PhysicsQuestion:
    """Kết quả phân loại câu hỏi vật lý, tương tự ClassifiedQuestion (type1)
    nhưng bổ sung thêm domain và target_variable.

    Không có expected_unit: unit prefix (μ/m/n/p) phụ thuộc vào magnitude
    của kết quả — chỉ biết sau khi SymPy giải xong. Validation unit được
    xử lý tách biệt trong pipeline/type2/type2_validation.py.
    """
    original: str
    question_type: PhysicsQuestionType
    domain: str                    # "circuits" | "electrostatics"
    target_variable: Optional[str] # Biến cần tìm: "E", "R", "V", "F"...
    keywords: list[str]            # Tái dùng _extract_keywords() từ type1


class PhysicsClassifier(QuestionClassifier):
    """Phân loại câu hỏi vật lý (Type 2 pipeline).

    Kế thừa QuestionClassifier (type1) để tái dùng _extract_keywords().
    Không dùng lại classify() hay _extract_options() vì vật lý không có MCQ.
    """

    def classify_physics(self, question: str) -> PhysicsQuestion:
        """Điểm vào chính cho Type 2 — tương đương classify() của type1.

        Phối hợp 3 detector rồi đóng gói vào PhysicsQuestion.
        Thứ tự gọi quan trọng: domain phải xác định trước khi detect q_type.
        """
        domain   = self._detect_domain(question)
        q_type   = self._detect_physics_type(question, domain)
        target   = self._detect_target_variable(question)
        keywords = self._extract_keywords(question)  # ← tái dùng từ type1

        return PhysicsQuestion(
            original=question,
            question_type=q_type,
            domain=domain,
            target_variable=target,
            keywords=keywords,
        )

    def _detect_domain(self, question: str) -> str:
        """Phân loại domain: electrostatics nếu khớp keyword, còn lại circuits.

        Dùng keyword matching thô — đủ dùng vì dataset chỉ có 2 domain.
        """
        electrostatic_kw = {"capacitor", "charge", "electric field",
                             "coulomb", "dielectric", "capacitance"}
        q_lower = question.lower()
        if any(kw in q_lower for kw in electrostatic_kw):
            return "electrostatics"
        return "circuits"

    def _detect_physics_type(self, question: str, domain: str) -> PhysicsQuestionType:
        """Xác định dạng bài toán để chọn chiến lược giải của SymPy solver.

        CIRCUIT/ELECTROSTATIC được ưu tiên trước vì domain đã xác định rõ.
        MULTI_STEP khi câu hỏi yêu cầu nhiều bước trung gian ("then", "after").
        Mặc định SINGLE_FORMULA — SymPy giải một phương trình duy nhất.
        """
        q_lower = question.lower()
        if domain == "circuits":
            if any(kw in q_lower for kw in ("series", "parallel", "network", "branch")):
                return PhysicsQuestionType.CIRCUIT
        if domain == "electrostatics":
            return PhysicsQuestionType.ELECTROSTATIC
        if any(kw in q_lower for kw in ("then", "after", "subsequently", "next")):
            return PhysicsQuestionType.MULTI_STEP
        return PhysicsQuestionType.SINGLE_FORMULA

    def _detect_target_variable(self, question: str) -> Optional[str]:
        """Map từ khóa trong câu hỏi sang ký hiệu vật lý chuẩn.

        Ký hiệu trả về được dùng bởi SymPy solver để đặt tên Symbol.
        "Calculate the energy" → "E"
        "Find the resistance"  → "R"
        "Determine the force"  → "F"

        Chỉ trả về biến đầu tiên khớp — không xử lý multi-target ("find I1 and I2").
        Multi-target detection nằm trong type2_validation.py.
        """
        mapping = {
            "energy": "E", "resistance": "R", "voltage": "V",
            "current": "I", "power": "P", "charge": "Q",
            "capacitance": "C", "electric field": "E_field",
            "force": "F", "frequency": "f", "inductance": "L",
            "magnetic field": "B", "flux": "Φ",
        }
        q_lower = question.lower()
        for keyword, var in mapping.items():
            if keyword in q_lower:
                return var
        return None
