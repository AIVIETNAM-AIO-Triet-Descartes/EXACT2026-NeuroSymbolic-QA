# Nguồn dữ liệu — Bộ 53 công thức (`data/rag/physics_formulas.json`)

> Báo cáo nguồn gốc cho **Data Disclosure** (EXACT 2026 Submission Guide §8 — "Datasets used").
> Knowledge base RAG gồm **53 công thức**, chia 3 nhóm theo nguồn.

| Nhóm | ID | Số | Nguồn |
|------|-----|----|-------|
| 1 | formula_001–020 | 20 | Trích từ **2 giáo trình Vật lý đại cương** (xem §1) |
| 2 | formula_021–044 | 24 | Trích công thức từ **CoT của dataset EXACT chính thức**; `example_*` sinh bằng AI (ChatGPT) (§2) |
| 3 | formula_045–053 | 9 | **Claude Code** sinh (công thức chuẩn SGK + bổ trợ coverage) (§3) |

---

## 1. formula_001–020 — Trích từ giáo trình (20 công thức)

Toàn bộ formula_001 → formula_020 được trích xuất chính xác từ hai giáo trình cốt lõi dưới đây.

### 1.1 Domain `circuits` (Mạch điện)
**Giáo trình:** *Vật lý Đại cương (Tập 2: Điện – Từ – Dao động – Sóng)* — Lương Duyên Bình (Chủ biên), NXB Giáo dục Việt Nam.

| Công thức | Nội dung | Vị trí trong giáo trình |
|-----------|----------|--------------------------|
| formula_001 | Định luật Ohm | Chương III: Dòng điện không đổi — Mục 1.2: Định luật Ohm đối với đoạn mạch chỉ có điện trở |
| formula_002, formula_003 | Mạch điện trở nối tiếp & song song | Chương III — Mục 1.3: Đoạn mạch mắc nối tiếp và mắc song song |
| formula_004, formula_005, formula_006 | Công suất điện | Chương III — Mục 2.1: Công và công suất của dòng điện; Định luật Joule–Lenz |
| formula_007, formula_008 | Định luật Kirchhoff (KVL & KCL) | Chương III — Mục 3.1 & 3.2: Các định luật Kirchhoff đối với mạch mạng phức tạp |
| formula_009, formula_010 | Bộ chia áp & chia dòng | Phần phụ lục bài tập ứng dụng mạch điện tương đương (Mạch phân áp và phân dòng cơ bản) |

### 1.2 Domain `electrostatics` (Tĩnh điện)
**Giáo trình:** *Vật lý đại cương 2 (Điện từ học)* — Nguyễn Thành Tiên, Trường Đại học Bách khoa – ĐHQG TP.HCM.

| Công thức | Nội dung | Vị trí trong giáo trình |
|-----------|----------|--------------------------|
| formula_016 | Định luật Coulomb | Chương I: Điện trường tĩnh trong chân không — Mục 1.1: Định luật Coulomb về tương tác giữa các điện tích điểm |
| formula_020, formula_015 | Cường độ điện trường điểm & đều | Chương I — Mục 1.2: Điện trường và Vector cường độ điện trường |
| formula_017, formula_019 | Thế năng tĩnh điện & Điện thế | Chương I — Mục 2.1 & 2.2: Công của lực tĩnh điện, Thế năng và Điện thế |
| formula_011, formula_012 | Điện tích & Năng lượng tụ điện | Chương II: Vật dẫn trong điện trường. Tụ điện — Mục 3.2: Điện dung của tụ điện và Năng lượng của trường tĩnh điện |
| formula_013, formula_014 | Tụ điện nối tiếp & song song | Chương II — Mục 3.3: Các cách mắc tụ điện thành bộ |
| formula_018 | Tụ điện có điện môi | Chương III: Điện trường trong chất điện môi — Mục 2.1: Điện dung của tụ điện phẳng khi có chất điện môi |

---

## 2. formula_021–044 — Trích từ dataset + AI generate example (24 công thức)

Công thức được **trích từ lời giải (Chain-of-Thought) của dataset EXACT chính thức** (`Physics_Problems_Text_Only.csv`); riêng các trường minh hoạ (`example_question`, `example_cot`, `example_answer`…) được **sinh bằng AI (ChatGPT)** để chuẩn hoá định dạng RAG. Đây đều là công thức Vật lý đại cương chuẩn (cảm ứng điện từ + mạch xoay chiều RLC + dao động LC).

| ID | Domain | Công thức |
|----|--------|-----------|
| formula_021–022 | electromagnetism | Từ trường trong lòng solenoid `B = μ₀·n·I` |
| formula_023 | electromagnetism | Độ tự cảm solenoid `L = μ₀·N²·A/l` |
| formula_024 | electromagnetism | Từ thông `Φ = B·A·cosθ` |
| formula_025 | electromagnetism | Năng lượng cuộn cảm `W_L = ½·L·I²` |
| formula_026 | electromagnetism | Mật độ năng lượng từ trường `u_B = B²/(2μ₀)` |
| formula_027 | ac_circuits | Cảm kháng `Z_L = 2πf·L` |
| formula_028 | ac_circuits | Dung kháng `Z_C = 1/(2πf·C)` |
| formula_029 | ac_circuits | Tổng trở RLC nối tiếp `Z = √(R²+(Z_L−Z_C)²)` |
| formula_030–031 | ac_circuits | Giá trị hiệu dụng `U = U_peak/√2`, `I = I_peak/√2` |
| formula_032 | ac_circuits | Hệ số công suất `cosφ = R/Z` |
| formula_033–034 | ac_circuits | Công suất tiêu thụ `P = U·I·cosφ = I²·R` |
| formula_035 | ac_circuits | Điều kiện cộng hưởng `ωL = 1/(ωC)` |
| formula_036 | ac_circuits | Hệ số phẩm chất `Q = (1/R)·√(L/C)` |
| formula_037–039 | ac_circuits | Tần số/chu kỳ riêng `ω₀=1/√(LC)`, `T=2π√(LC)`, `f₀=1/(2π√(LC))` |
| formula_040–042 | ac_circuits | Năng lượng điện từ mạch dao động `W=½CU₀²=½LI₀²=W_C+W_L` |
| formula_043 | electrostatics | Điện trường dây dẫn thẳng dài `E = 2k·λ/r` |
| formula_044 | electrostatics | Điện trường mặt phẳng tích điện `E = 2πk·σ` |

---

## 3. formula_045–053 — Claude Code sinh (9 công thức)

Được **Claude Code sinh** để mở rộng coverage (các cấu hình điện trường chuẩn SGK + sai số đo lường + bổ trợ). Đều là công thức Vật lý chuẩn, không phải dữ liệu độc quyền.

| ID | Domain | Công thức |
|----|--------|-----------|
| formula_045 | electrostatics | Điện trường giữa 2 bản dẫn `E = 4πk·σ` |
| formula_046 | electrostatics | Điện trường trên trục vòng dây tích điện `E = kqz/(R²+z²)^1.5` |
| formula_047 | electrostatics | Điện trường trên trục đĩa tích điện `E = 2πkσ·(1 − z/√(R²+z²))` |
| formula_048 | electrostatics | Cộng vector lực (hình bình hành) `R = √(F₁²+F₂²+2F₁F₂cosθ)` |
| formula_049 | electrostatics | Định luật II Newton cho điện tích `qE = ma` |
| formula_050 | measurement | Sai số tuyệt đối `ΔA = A_max − Ā` |
| formula_051 | measurement | Sai số tương đối `δ = (A_max − Ā)/Ā × 100` |
| formula_052 | electrostatics | Năng lượng tụ theo điện tích `W = Q²/(2C)` |
| formula_053 | electromagnetism | Độ tự cảm solenoid theo thể tích `L = μ₀·n²·V` |

---

## Ghi chú

- Tất cả 53 công thức là **kiến thức Vật lý đại cương phổ quát** (định luật/công thức chuẩn), không phải dữ liệu độc quyền hay crawl — dùng làm knowledge base cho module Formula RAG (retrieval, không train).
- Phần `example_*` của nhóm 2 sinh bằng ChatGPT **chỉ để minh hoạ/định dạng RAG**, không dùng để train model và không gọi inference closed-source lúc chạy (tuân thủ luật ≤8B + cấm third-party inference API).
- Phân bố domain: `electrostatics` 18 · `ac_circuits` 16 · `circuits` 10 · `electromagnetism` 7 · `measurement` 2.
