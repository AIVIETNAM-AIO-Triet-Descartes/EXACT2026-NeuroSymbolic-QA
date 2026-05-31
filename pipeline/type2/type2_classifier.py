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
    # Mở rộng theo docs/track2_data_info.md §5.6 — phủ đủ 8 prefix dataset.
    # sympy_solver chỉ dispatch SINGLE_FORMULA/CIRCUIT/ELECTROSTATIC/MULTI_STEP;
    # các type còn lại rơi vào fallback chain (vector_solver / LLM CoT) — hợp lý
    # vì chúng cần solver chuyên biệt, không giải bằng sympy.solve() đơn thuần.
    SINGLE_FORMULA  = "single_formula"   # TD, NL đơn giản — 1 phương trình (V=IR, E=½CU²)
    MULTI_STEP      = "multi_step"       # CH, DDT — nhiều công thức liên tiếp
    CIRCUIT         = "circuit"          # CH — mạch RLC nối tiếp/song song
    ELECTROSTATIC   = "electrostatic"    # LD/DT — Coulomb/điện trường (scalar)
    VECTOR          = "vector"           # LD/DT — cộng vector 2D (góc, tam giác)  ← MỚI
    YES_NO          = "yes_no"           # CHLT — cộng hưởng Yes/No                ← MỚI
    QUALITATIVE     = "qualitative"      # NL/DDT — định tính (cần LLM)            ← MỚI
    MULTI_ANSWER    = "multi_answer"     # THCB — nhiều đáp án (dấu ;)             ← MỚI
    ERROR_CALC      = "error_calc"       # THCB — sai số đo lường                  ← MỚI
    ELECTROMAGNETIC = "electromagnetic"  # DDT — cảm ứng điện từ / solenoid        ← MỚI


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
    domain: str                    # "circuits" | "electrostatics" | "electromagnetism" | "measurement"
    target_variable: Optional[str] # Biến cần tìm: "E", "R", "V", "F", "Z", "EMF"...
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
        """Phân loại domain — 4 nhóm phủ 8 prefix dataset (docs/track2_data_info.md §2).

        Thứ tự kiểm tra = ưu tiên (cụ thể → tổng quát):
          measurement     (THCB) — sai số đo lường, kiểm tra trước vì rất đặc thù
          electromagnetism (DDT) — solenoid / từ thông / EMF / tự cảm
          electrostatics  (LD/DT/TD/NL-tụ) — điện tích / tụ điện / điện trường
          circuits        (CH + mặc định) — mạch RLC xoay chiều

        Lưu ý: formula_rag Layer-1 match `doc["domain"]`. DB formula hiện chỉ có
        circuits/electrostatics → câu measurement/electromagnetism rơi xuống FAISS
        (không regress vì chưa có formula DDT/THCB). Khi P3 thêm formula, gán
        domain tương ứng để Layer-1 ăn khớp.
        """
        q_lower = question.lower()

        # measurement error (THCB) — đặc thù nhất
        if any(kw in q_lower for kw in (
            "absolute error", "relative error", "least count",
            "uncertainty", "measured value", "measurement error",
        )):
            return "measurement"

        # electromagnetic induction (DDT)
        if any(kw in q_lower for kw in (
            "solenoid", "magnetic flux", "induced", "self-inductance",
            "faraday", "emf", "electromotive force", "magnetic field",
        )):
            return "electromagnetism"

        # electrostatics (LD/DT/TD/NL-tụ)
        if any(kw in q_lower for kw in (
            "capacitor", "capacitance", "charge", "coulomb",
            "electric field", "dielectric", "point charge", "electric force",
        )):
            return "electrostatics"

        return "circuits"

    def _detect_physics_type(self, question: str, domain: str) -> PhysicsQuestionType:
        """Xác định dạng bài toán để chọn chiến lược giải của SymPy solver.

        CIRCUIT/ELECTROSTATIC được ưu tiên trước vì domain đã xác định rõ.
        MULTI_STEP khi câu hỏi yêu cầu nhiều bước trung gian ("then", "after").
        Mặc định SINGLE_FORMULA — SymPy giải một phương trình duy nhất.
        """
        q_lower = question.lower()

        # 1. Yes/No cộng hưởng (CHLT) — ưu tiên cao nhất, cần routing riêng (không solve)
        if any(kw in q_lower for kw in (
            "does the circuit", "is the circuit", "does it", "will it",
            "experience resonance", "is there resonance", "resonance occur",
        )):
            return PhysicsQuestionType.YES_NO

        # 2. Sai số đo lường (THCB) — multi-answer nếu hỏi nhiều đại lượng
        if domain == "measurement":
            if any(kw in q_lower for kw in ("and the", "both", "respectively", ";")):
                return PhysicsQuestionType.MULTI_ANSWER
            return PhysicsQuestionType.ERROR_CALC

        # 3. Định tính (NL/DDT khái niệm) — cần LLM reasoning, không dùng SymPy
        if any(kw in q_lower for kw in (
            "where is", "what happens", "which of", "shape of graph",
            "directly proportional", "proportional to", "characteristic of",
        )):
            return PhysicsQuestionType.QUALITATIVE

        # 4. Cảm ứng điện từ (DDT)
        if domain == "electromagnetism":
            return PhysicsQuestionType.ELECTROMAGNETIC

        # 5. Vector tĩnh điện (LD/DT có hình học) — chỉ khi tín hiệu hình học mạnh.
        #    Cặp 2 điện tích đơn vẫn để ELECTROSTATIC (scalar solve); vector_solver
        #    vẫn là fallback của sympy_solver nên không sợ bỏ sót.
        if domain == "electrostatics" and any(kw in q_lower for kw in (
            "triangle", "vertices", "vertex", "equilateral",
            "angle between", "perpendicular", "midpoint", "three charges",
        )):
            return PhysicsQuestionType.VECTOR

        # 6. Mạch RLC topology (CH)
        if domain == "circuits" and any(kw in q_lower for kw in (
            "series", "parallel", "network", "branch",
        )):
            return PhysicsQuestionType.CIRCUIT

        # 7. Tĩnh điện scalar
        if domain == "electrostatics":
            return PhysicsQuestionType.ELECTROSTATIC

        # 8. Nhiều bước
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
        # Thứ tự = ưu tiên match (first-match-wins). Cụm nhiều từ phải đặt TRƯỚC
        # từ đơn chứa nó: "electromotive force" trước "force", "power factor" trước
        # "power", "impedance" trước "resistance" (Z vs R).
        mapping = {
            "impedance": "Z",
            "energy": "E",
            "resistance": "R",
            "voltage": "V",
            "current": "I",
            "power factor": "cos_phi",
            "power": "P",
            "charge": "Q",
            "capacitance": "C",
            "electromotive force": "EMF",
            "emf": "EMF",
            "electric field": "E_field",
            "magnetic flux": "Φ",
            "magnetic field": "B",
            "force": "F",
            "frequency": "f",
            "period": "T",
            "self-inductance": "L",
            "inductance": "L",
            "flux": "Φ",
        }
        q_lower = question.lower()
        for keyword, var in mapping.items():
            if keyword in q_lower:
                return var
        return None
