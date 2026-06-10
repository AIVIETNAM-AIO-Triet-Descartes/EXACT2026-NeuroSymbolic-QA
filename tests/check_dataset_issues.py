"""
EXACT 2026 — Dataset Annotation Issue Checker
==============================================
Mục đích: Phát hiện các lỗi annotation trong dataset để report lên ban tổ chức
và nhận bonus điểm (ura.hcmut@gmail.com, subject: [Dataset Issue])

Cách dùng:
    python check_dataset_issues.py --type1 data/train/type1.json --type2 data/train/type2.json
    python check_dataset_issues.py --type1 data/train/type1.json  # chỉ check Type 1
    python check_dataset_issues.py --type2 data/train/type2.json  # chỉ check Type 2

Output:
    reports/annotation_issues.json  — toàn bộ issues phát hiện được
    reports/annotation_report.md    — báo cáo dạng Markdown, sẵn sàng để gửi BTC
"""

import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Optional

# ── Cấu hình ──────────────────────────────────────────────────────────────────

VALID_MCQ_OPTIONS     = {"A", "B", "C", "D"}
VALID_YESNO_OPTIONS   = {"Yes", "No", "Uncertain", "Unknown"}
VALID_FOL_OPERATORS   = {"∀", "∃", "∧", "∨", "→", "¬", "↔", "⊕"}
VALID_PHYSICS_UNITS   = {
    "V", "A", "Ω", "W", "J", "F", "C", "H",           # SI cơ bản
    "mV", "kV", "mA", "kA", "mΩ", "kΩ", "MΩ",         # SI có prefix
    "mW", "kW", "MW", "mJ", "kJ", "MJ",
    "μF", "mF", "nF", "pF", "μC", "nC",
    "ohm", "volt", "ampere", "watt", "joule", "farad",  # tên đầy đủ
}
MIN_EXPLANATION_WORDS = 10   # explanation quá ngắn
MIN_COT_STEPS         = 2    # CoT quá ít bước

# ── Các loại issue ─────────────────────────────────────────────────────────────

ISSUE_TYPES = {
    # Format issues
    "MISSING_FIELD":        "Thiếu field bắt buộc",
    "EMPTY_FIELD":          "Field bắt buộc rỗng hoặc null",
    "INVALID_ANSWER_FORMAT":"Answer không đúng định dạng hợp lệ",

    # Logic issues (Type 1)
    "FOL_NL_COUNT_MISMATCH":"premises-NL và premises-FOL không cùng số lượng",
    "FOL_SYNTAX_SUSPECT":   "FOL có thể sai cú pháp (thiếu dấu ngoặc, ký tự lạ)",
    "ANSWER_NOT_IN_OPTIONS":"Answer không thuộc các options được liệt kê trong câu hỏi",
    "DUPLICATE_PREMISE":    "Có premises giống nhau hoàn toàn trong cùng 1 record",
    "EXPLANATION_TOO_SHORT":"Explanation quá ngắn (< 10 từ)",
    "INCONSISTENT_FOL":     "FOL không phản ánh nội dung của premise NL tương ứng",

    # Physics issues (Type 2)
    "MISSING_UNIT":         "Câu hỏi có số liệu nhưng answer thiếu unit",
    "UNIT_MISMATCH":        "Unit trong answer không khớp với unit trong câu hỏi",
    "COT_TOO_SHORT":        "CoT có ít hơn 2 bước",
    "NUMERIC_ANSWER_INVALID":"Answer không parse được thành số",
    "ANSWER_UNIT_EMBEDDED": "Answer nhúng cả unit vào (vd: '45mJ') thay vì tách riêng",

    # Ambiguity issues
    "AMBIGUOUS_QUESTION":   "Câu hỏi có thể hiểu nhiều nghĩa",
    "DUPLICATE_RECORD":     "Record trùng lặp hoàn toàn với record khác",
    "ANSWER_CONTRADICTS_PREMISES": "Answer mâu thuẫn với premises (cần verify thủ công)",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def make_issue(record_id: str, issue_type: str, field: str,
               detail: str, severity: str = "medium") -> dict:
    return {
        "record_id":  record_id,
        "issue_type": issue_type,
        "description": ISSUE_TYPES.get(issue_type, issue_type),
        "field":      field,
        "detail":     detail,
        "severity":   severity,  # high / medium / low
    }

def extract_mcq_options_from_question(question: str) -> set[str]:
    """Tìm các options A/B/C/D được liệt kê trong câu hỏi."""
    return set(re.findall(r'\b([A-D])\s*[.:\)]', question))

def is_numeric(s: str) -> bool:
    try:
        float(str(s).replace(",", "."))
        return True
    except (ValueError, TypeError):
        return False

def looks_like_physics_question(question: str) -> bool:
    keywords = {"calculate", "find", "determine", "compute", "what is",
                "how much", "voltage", "current", "resistance", "power",
                "energy", "capacitor", "circuit", "charge"}
    q_lower = question.lower()
    return any(k in q_lower for k in keywords)

def fol_syntax_check(fol: str) -> list[str]:
    """Phát hiện các dấu hiệu FOL có thể sai cú pháp."""
    warnings = []
    # Mở ngoặc không khớp đóng ngoặc
    if fol.count("(") != fol.count(")"):
        warnings.append(f"Số dấu '(' ({fol.count('(')}) ≠ số dấu ')' ({fol.count(')')})")
    # Dùng ký tự ASCII thay vì ký hiệu FOL chuẩn
    if "/\\" in fol and "∧" not in fol:
        warnings.append("Dùng '/\\' thay vì '∧'")
    if "\\/" in fol and "∨" not in fol:
        warnings.append("Dùng '\\/' thay vì '∨'")
    return warnings

# ── Checker Type 1 ─────────────────────────────────────────────────────────────

def check_type1_record(record: dict, idx: int) -> list[dict]:
    issues = []
    record_id = record.get("id", f"type1_record_{idx}")

    # 1. Kiểm tra các field bắt buộc
    required_fields = ["premises-NL", "questions", "answers"]
    for field in required_fields:
        if field not in record:
            issues.append(make_issue(record_id, "MISSING_FIELD", field,
                f"Field '{field}' không tồn tại trong record", "high"))
        elif not record[field]:
            issues.append(make_issue(record_id, "EMPTY_FIELD", field,
                f"Field '{field}' rỗng", "high"))

    if any(f not in record for f in required_fields):
        return issues  # Không check tiếp nếu thiếu field cơ bản

    premises_nl  = record.get("premises-NL", [])
    premises_fol = record.get("premises-FOL", [])
    questions    = record.get("questions", [])
    answers      = record.get("answers", [])
    explanations = record.get("explanation", [])

    # 2. premises-NL vs premises-FOL count mismatch
    if premises_fol and len(premises_nl) != len(premises_fol):
        issues.append(make_issue(record_id, "FOL_NL_COUNT_MISMATCH", "premises-FOL",
            f"premises-NL có {len(premises_nl)} items, premises-FOL có {len(premises_fol)} items",
            "high"))

    # 3. Kiểm tra FOL syntax
    for i, fol in enumerate(premises_fol):
        fol_warnings = fol_syntax_check(fol)
        for w in fol_warnings:
            issues.append(make_issue(record_id, "FOL_SYNTAX_SUSPECT",
                f"premises-FOL[{i}]", f"FOL: '{fol[:80]}...' — {w}", "medium"))

    # 4. Kiểm tra từng câu hỏi và answer tương ứng
    for q_idx, (question, answer) in enumerate(zip(questions, answers)):
        if answer == "Unknown":
            continue  # "Unknown" là answer hợp lệ cho mọi dạng câu hỏi
        q_lower = question.lower()

        # Xác định loại câu hỏi
        mcq_options = extract_mcq_options_from_question(question)
        is_mcq      = len(mcq_options) >= 2
        is_yesno    = any(k in q_lower for k in ["yes or no", "true or false",
                                                   "is it", "can we conclude"])

        if is_mcq:
            # Answer phải là A/B/C/D và phải nằm trong options được liệt kê
            if answer not in VALID_MCQ_OPTIONS:
                issues.append(make_issue(record_id, "INVALID_ANSWER_FORMAT",
                    f"answers[{q_idx}]",
                    f"Answer '{answer}' không phải A/B/C/D", "high"))
            elif mcq_options and answer not in mcq_options:
                issues.append(make_issue(record_id, "ANSWER_NOT_IN_OPTIONS",
                    f"answers[{q_idx}]",
                    f"Answer '{answer}' không nằm trong options {mcq_options} của câu hỏi",
                    "high"))
        elif is_yesno:
            if answer not in VALID_YESNO_OPTIONS:
                issues.append(make_issue(record_id, "INVALID_ANSWER_FORMAT",
                    f"answers[{q_idx}]",
                    f"Answer '{answer}' không phải Yes/No/Uncertain", "medium"))

    # 5. Kiểm tra explanation
    for e_idx, explanation in enumerate(explanations):
        if not explanation or not explanation.strip():
            issues.append(make_issue(record_id, "EMPTY_FIELD",
                f"explanation[{e_idx}]", "Explanation rỗng", "high"))
        elif len(explanation.split()) < MIN_EXPLANATION_WORDS:
            issues.append(make_issue(record_id, "EXPLANATION_TOO_SHORT",
                f"explanation[{e_idx}]",
                f"Chỉ có {len(explanation.split())} từ: '{explanation}'", "medium"))

    # 6. Duplicate premises
    seen_premises = set()
    for i, premise in enumerate(premises_nl):
        if premise.strip() in seen_premises:
            issues.append(make_issue(record_id, "DUPLICATE_PREMISE",
                f"premises-NL[{i}]",
                f"Premise trùng lặp: '{premise[:80]}'", "medium"))
        seen_premises.add(premise.strip())

    return issues

# ── Checker Type 2 ─────────────────────────────────────────────────────────────

def check_type2_record(record: dict, idx: int) -> list[dict]:
    issues = []
    record_id = record.get("id", f"type2_record_{idx}")

    # 1. Kiểm tra field bắt buộc
    required_fields = ["question", "answer"]
    for field in required_fields:
        if field not in record:
            issues.append(make_issue(record_id, "MISSING_FIELD", field,
                f"Field '{field}' không tồn tại", "high"))
        elif record[field] is None or str(record[field]).strip() == "":
            issues.append(make_issue(record_id, "EMPTY_FIELD", field,
                f"Field '{field}' rỗng", "high"))

    if "question" not in record or "answer" not in record:
        return issues

    question = record["question"]
    answer   = str(record.get("answer", ""))
    unit     = record.get("unit", "")
    cot      = record.get("cot", "")

    # 2. Answer phải là số (Type 2 là bài toán tính toán)
    if looks_like_physics_question(question):
        if not is_numeric(answer):
            # Kiểm tra xem có phải unit bị nhúng vào answer không (vd: "45mJ")
            numeric_part = re.sub(r'[a-zA-ZμΩ°]+$', '', answer).strip()
            if is_numeric(numeric_part) and len(answer) != len(numeric_part):
                issues.append(make_issue(record_id, "ANSWER_UNIT_EMBEDDED", "answer",
                    f"Answer '{answer}' có vẻ nhúng cả unit — nên tách thành "
                    f"answer='{numeric_part}' và unit='{answer[len(numeric_part):]}'",
                    "medium"))
            else:
                issues.append(make_issue(record_id, "NUMERIC_ANSWER_INVALID", "answer",
                    f"Answer '{answer}' không parse được thành số", "high"))

    # 3. Kiểm tra unit
    if looks_like_physics_question(question) and not unit:
        # Tìm xem câu hỏi hỏi đại lượng gì
        unit_hints = re.findall(
            r'\b(voltage|current|resistance|power|energy|capacitance|charge|'
            r'điện áp|dòng điện|điện trở|công suất|năng lượng)\b',
            question.lower()
        )
        if unit_hints:
            issues.append(make_issue(record_id, "MISSING_UNIT", "unit",
                f"Câu hỏi hỏi về '{unit_hints[0]}' nhưng field 'unit' rỗng", "medium"))

    # 4. Kiểm tra CoT
    if cot:
        # CoT dạng string — đếm số bước
        if isinstance(cot, str):
            steps = [s for s in re.split(r'step\s*\d+', cot, flags=re.IGNORECASE) if s.strip()]
            if len(steps) < MIN_COT_STEPS:
                issues.append(make_issue(record_id, "COT_TOO_SHORT", "cot",
                    f"CoT chỉ có {len(steps)} bước rõ ràng", "low"))
        elif isinstance(cot, list) and len(cot) < MIN_COT_STEPS:
            issues.append(make_issue(record_id, "COT_TOO_SHORT", "cot",
                f"CoT chỉ có {len(cot)} steps", "low"))

    return issues

# ── Duplicate detector ─────────────────────────────────────────────────────────

def find_duplicates(records: list[dict], question_field: str) -> list[dict]:
    """Tìm các record có nội dung câu hỏi trùng nhau."""
    issues = []
    seen   = {}   # question text → record_id đầu tiên thấy

    for idx, record in enumerate(records):
        record_id = record.get("id", f"record_{idx}")
        question  = record.get(question_field, "")
        if isinstance(question, list):
            question = " ".join(question)
        key = question.strip().lower()

        if key in seen:
            issues.append(make_issue(record_id, "DUPLICATE_RECORD", question_field,
                f"Trùng với record '{seen[key]}': '{question[:80]}'", "high"))
        else:
            seen[key] = record_id

    return issues

# ── Main ───────────────────────────────────────────────────────────────────────

def check_dataset(type1_path: Optional[str], type2_path: Optional[str]) -> dict:
    all_issues = []
    summary    = defaultdict(int)

    # ── Type 1 ──
    if type1_path and Path(type1_path).exists():
        print(f"🔍 Đang kiểm tra Type 1: {type1_path}")
        with open(type1_path, encoding="utf-8") as f:
            type1_data = json.load(f)

        records = type1_data if isinstance(type1_data, list) else type1_data.get("data", [])
        print(f"   → {len(records)} records")

        for idx, record in enumerate(records):
            issues = check_type1_record(record, idx)
            all_issues.extend(issues)

        dup_issues = find_duplicates(records, "questions")
        all_issues.extend(dup_issues)
    else:
        if type1_path:
            print(f"⚠️  File Type 1 không tồn tại: {type1_path}")

    # ── Type 2 ──
    if type2_path and Path(type2_path).exists():
        print(f"🔍 Đang kiểm tra Type 2: {type2_path}")
        with open(type2_path, encoding="utf-8") as f:
            type2_data = json.load(f)

        records = type2_data if isinstance(type2_data, list) else type2_data.get("data", [])
        print(f"   → {len(records)} records")

        for idx, record in enumerate(records):
            issues = check_type2_record(record, idx)
            all_issues.extend(issues)

        dup_issues = find_duplicates(records, "question")
        all_issues.extend(dup_issues)
    else:
        if type2_path:
            print(f"⚠️  File Type 2 không tồn tại: {type2_path}")

    # ── Tổng hợp ──
    for issue in all_issues:
        summary[issue["issue_type"]]   += 1
        summary[f"sev_{issue['severity']}"] += 1

    return {
        "total_issues": len(all_issues),
        "summary":      dict(summary),
        "issues":       all_issues,
    }

def write_reports(result: dict, output_dir: str = "reports") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # JSON đầy đủ
    json_path = Path(output_dir) / "annotation_issues.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON report: {json_path}")

    # Markdown — sẵn sàng gửi BTC
    md_path = Path(output_dir) / "annotation_report.md"
    lines   = [
        "# EXACT 2026 — Dataset Annotation Issues Report\n",
        f"**Tổng số issues phát hiện:** {result['total_issues']}\n",
        "## Tóm tắt theo loại\n",
        "| Issue Type | Count |",
        "|---|---|",
    ]
    for issue_type, count in sorted(result["summary"].items()):
        if not issue_type.startswith("sev_"):
            desc = ISSUE_TYPES.get(issue_type, issue_type)
            lines.append(f"| `{issue_type}` — {desc} | {count} |")

    # Phân nhóm theo severity
    high_issues   = [i for i in result["issues"] if i["severity"] == "high"]
    medium_issues = [i for i in result["issues"] if i["severity"] == "medium"]

    for severity, issues in [("🔴 HIGH", high_issues), ("🟡 MEDIUM", medium_issues)]:
        if not issues:
            continue
        lines.append(f"\n## {severity} ({len(issues)} issues)\n")
        lines.append("| Record ID | Issue Type | Field | Detail |")
        lines.append("|---|---|---|---|")
        for issue in issues:
            detail = issue["detail"].replace("|", "\\|")[:100]
            lines.append(
                f"| `{issue['record_id']}` | `{issue['issue_type']}` "
                f"| `{issue['field']}` | {detail} |"
            )

    lines.append("\n---")
    lines.append("*Report tạo bởi `check_dataset_issues.py`*")
    lines.append("*Để report lên BTC: ura.hcmut@gmail.com, subject: [Dataset Issue]*")
    lines.append("*Format: record_id, issue_type, justification ngắn gọn*")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown report: {md_path}")

def print_summary(result: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  Tổng issues: {result['total_issues']}")
    high   = result["summary"].get("sev_high", 0)
    medium = result["summary"].get("sev_medium", 0)
    low    = result["summary"].get("sev_low", 0)
    print(f"  🔴 High:   {high}")
    print(f"  🟡 Medium: {medium}")
    print(f"  🟢 Low:    {low}")
    print(f"{'='*50}")
    if high > 0:
        print(f"\n⚡ Có {high} HIGH severity issues — ưu tiên review trước!")
    if result["total_issues"] > 0:
        print("\n📧 Issues đủ điều kiện report lên BTC:")
        print("   ura.hcmut@gmail.com | subject: [Dataset Issue]")
        print("   Cần ghi: record_id, issue_type, justification ngắn")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EXACT 2026 Dataset Annotation Issue Checker")
    parser.add_argument("--type1", help="Path đến file JSON Type 1")
    parser.add_argument("--type2", help="Path đến file JSON Type 2")
    parser.add_argument("--output", default="reports", help="Thư mục output (default: reports/)")
    args = parser.parse_args()

    if not args.type1 and not args.type2:
        parser.error("Cần ít nhất một trong --type1 hoặc --type2")

    result = check_dataset(args.type1, args.type2)
    write_reports(result, args.output)
    print_summary(result)
