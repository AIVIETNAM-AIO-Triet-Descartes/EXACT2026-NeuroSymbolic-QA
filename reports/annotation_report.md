# EXACT 2026 — Dataset Annotation Issues Report

**Tổng số issues phát hiện:** 37

## Tóm tắt theo loại

| Issue Type | Count |
|---|---|
| `DUPLICATE_PREMISE` — Có premises giống nhau hoàn toàn trong cùng 1 record | 2 |
| `DUPLICATE_RECORD` — Record trùng lặp hoàn toàn với record khác | 5 |
| `FOL_NL_COUNT_MISMATCH` — premises-NL và premises-FOL không cùng số lượng | 11 |
| `FOL_SYNTAX_SUSPECT` — FOL có thể sai cú pháp (thiếu dấu ngoặc, ký tự lạ) | 19 |

## 🔴 HIGH (16 issues)

| Record ID | Issue Type | Field | Detail |
|---|---|---|---|
| `type1_record_34` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 27 items, premises-FOL có 25 items |
| `type1_record_57` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 12 items, premises-FOL có 14 items |
| `type1_record_146` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 10 items, premises-FOL có 11 items |
| `type1_record_334` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 15 items, premises-FOL có 17 items |
| `type1_record_376` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 22 items |
| `type1_record_377` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 17 items |
| `type1_record_378` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 16 items |
| `type1_record_379` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 19 items |
| `type1_record_380` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 12 items, premises-FOL có 17 items |
| `type1_record_381` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 14 items |
| `type1_record_382` | `FOL_NL_COUNT_MISMATCH` | `premises-FOL` | premises-NL có 13 items, premises-FOL có 14 items |
| `record_9` | `DUPLICATE_RECORD` | `questions` | Trùng với record 'record_8': 'Based on the premises, what can we conclude about the curriculum?
A. I |
| `record_25` | `DUPLICATE_RECORD` | `questions` | Trùng với record 'record_24': 'Based on the learning science principles, which statement is correct? |
| `record_161` | `DUPLICATE_RECORD` | `questions` | Trùng với record 'record_160': 'Do all students understand the material? Do all students review regu |
| `record_183` | `DUPLICATE_RECORD` | `questions` | Trùng với record 'record_182': 'Based on the above premises, which statement can be inferred?
A. If  |
| `record_395` | `DUPLICATE_RECORD` | `questions` | Trùng với record 'record_394': 'Do all students receive a recommendation? Which activities do all st |

## 🟡 MEDIUM (21 issues)

| Record ID | Issue Type | Field | Detail |
|---|---|---|---|
| `type1_record_20` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[5]` | FOL: 'ForAll(s, (∃m1, ∃m2, ∃m3, m1 ≠ m2 ∧ m2 ≠ m3 ∧ m1 ≠ m3 ∧ grade(s,m1) > 8.5 ∧ grad...' — Số dấu  |
| `type1_record_20` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[8]` | FOL: 'ForAll(s, (∃m1, ∃m2, ∃m3, m1 ≠ m2 ∧ m2 ≠ m3 ∧ m1 ≠ m3 ∧ pass(s,m1) ∧ pass(s,m2) ...' — Số dấu  |
| `type1_record_26` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[7]` | FOL: 'ForAll(ABC, right_triangle(ABC) → (median(hypotenuse) = 0.5*hypotenuse)))...' — Số dấu '(' (4) |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[2]` | FOL: 'ForAll(s, ForAll(c, ¬submit_capstone(s,c) → take_exam(s,c))))...' — Số dấu '(' (4) ≠ số dấu ') |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[3]` | FOL: 'ForAll(c, require_exam(c) → (secure_system(c) ∨ external_proctor(c))))...' — Số dấu '(' (5) ≠  |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[4]` | FOL: 'ForAll(s, ForAll(c, (downtime(s,c) > 5) → ¬master_content(s,c))))...' — Số dấu '(' (5) ≠ số dấ |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[5]` | FOL: 'ForAll(s, (pass_count(s) ≥ 6) → digital_certificate(s)))...' — Số dấu '(' (4) ≠ số dấu ')' (5) |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[6]` | FOL: 'ForAll(s, ForAll(c, (live_sessions(s,c) = 100) → ¬take_exam(s,c))))...' — Số dấu '(' (5) ≠ số  |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[8]` | FOL: 'ForAll(s, ForAll(c, ((downtime(s,c) < 5) ∧ submit_capstone(s,c) ∧ high_stakes(c)...' — Số dấu  |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[9]` | FOL: 'ForAll(s, (complete_modules(s,c1) ∧ complete_modules(s,c2) ∧ complete_modules(s,...' — Số dấu  |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[10]` | FOL: 'ForAll(c, secure_system(c) ∧ crash_during_exam(c) → reschedule_exam(c)))...' — Số dấu '(' (4)  |
| `type1_record_29` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[11]` | FOL: 'ForAll(s, ForAll(c, (¬master_content(s,c) ∧ submit_capstone(s,c)) → (¬accept_cap...' — Số dấu  |
| `type1_record_129` | `DUPLICATE_PREMISE` | `premises-NL[10]` | Premise trùng lặp: 'If a Python project is easy to maintain, then it is well-tested.' |
| `type1_record_157` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[15]` | FOL: '(ForAll(x, ¬StudiesFromOfficialGuide(x) → ¬AttendsIELTSClass(x))) → (Exists(x, S...' — Số dấu  |
| `type1_record_188` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[2]` | FOL: '(∀x (E(x) → A(x))) → ∀x (¬E(x) → ¬A(x)))...' — Số dấu '(' (7) ≠ số dấu ')' (8) |
| `type1_record_188` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[4]` | FOL: '∀x (A(x) → E(x)))...' — Số dấu '(' (3) ≠ số dấu ')' (4) |
| `type1_record_208` | `DUPLICATE_PREMISE` | `premises-NL[14]` | Premise trùng lặp: 'If a student meets the requirements, then they engage in training.' |
| `type1_record_304` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[5]` | FOL: '((ForAll(x, (StudiesConsistently(x) → UnderstandsSubject(x))) → ForAll(x, Enroll...' — Số dấu  |
| `type1_record_305` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[7]` | FOL: '((ForAll(x, (ReferenceSection(x) → ¬Borrowable(x))) → Exists(x, Available(x)))...' — Số dấu '( |
| `type1_record_306` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[9]` | FOL: '((ForAll(x, (¬AttendLectures(x) → ¬UnderstandDefinitions(x))) → ForAll(x, Master...' — Số dấu  |
| `type1_record_309` | `FOL_SYNTAX_SUSPECT` | `premises-FOL[15]` | FOL: '((ForAll(x, (WellStructured(x) → Optimized(x))) → ForAll(x, (PythonScript(x) → (...' — Số dấu  |

---
*Report tạo bởi `check_dataset_issues.py`*
*Để report lên BTC: ura.hcmut@gmail.com, subject: [Dataset Issue]*
*Format: record_id, issue_type, justification ngắn gọn*