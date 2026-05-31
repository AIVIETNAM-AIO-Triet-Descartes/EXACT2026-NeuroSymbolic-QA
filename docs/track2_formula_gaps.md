# Track 2 — Formula Gap Analysis
> So sánh `physics_formulas.json` hiện tại (20 công thức) với toàn bộ dataset 1,352 bài toán.  
> Mục đích: xác định chính xác những công thức cần bổ sung để đạt coverage tối đa.

---

## 1. Tình trạng hiện tại

**File hiện có: 20 công thức — 2 domain:**

| Domain | Số công thức | Topics |
|--------|-------------|--------|
| `circuits` | 10 | ohms_law, series/parallel_resistance, power (×3), kvl, kcl, voltage_divider, current_divider |
| `electrostatics` | 10 | capacitor_charge/energy/dielectric, series/parallel_capacitance, electric_field_uniform, coulombs_law, electric_potential_energy/point, electric_field_point |

**Coverage ước tính với 20 công thức hiện tại:**

| Nhóm | Bài | Đã cover | Còn thiếu |
|------|-----|----------|-----------|
| TD (tụ điện cơ bản) | 177 | ~80% | ~35 bài |
| LD (Coulomb + E-field) | 397 | ~50% | ~199 bài |
| DT (điện trường điểm) | 68 | ~50% | ~34 bài |
| NL (năng lượng EM) | 190 | ~50% | ~95 bài |
| CH (RLC xoay chiều) | 290 | **0%** | 290 bài |
| CHLT (cộng hưởng) | 20 | **0%** | 20 bài |
| DDT (điện từ cảm ứng) | 130 | **0%** | 130 bài |
| THCB (sai số) | 80 | **0%** | 80 bài |
| **Tổng** | **1,352** | **~34.7%** | **~883 bài** |

> ⚠️ Với database hiện tại, pipeline chỉ giải được ~35% dataset. Cần bổ sung **28 công thức** mới chia thành 4 domain mới.

---

## 2. Danh sách công thức cần bổ sung

### DOMAIN MỚI: `ac_circuits` — Mạch RLC xoay chiều (cho CH + CHLT)

#### F-021 | `inductive_reactance`
```
formula_sympy: X_L = omega * L
formula_latex:  X_L = \omega L = 2\pi f L
variables:      X_L (Ω), omega (rad/s), L (H), f (Hz)
unit_conversions: mH → 1e-3 H, μH → 1e-6 H, Hz → rad/s (×2π)
```
*Dùng cho:* CH bài tính X_L khi biết L và f. Là thành phần trong Z.

---

#### F-022 | `capacitive_reactance`
```
formula_sympy: X_C = 1 / (omega * C)
formula_latex:  X_C = \frac{1}{\omega C} = \frac{1}{2\pi f C}
variables:      X_C (Ω), omega (rad/s), C (F)
unit_conversions: μF → 1e-6 F, nF → 1e-9 F, pF → 1e-12 F
```
*Dùng cho:* CH tính X_C, tiền đề tính Z.

---

#### F-023 | `rlc_impedance`
```
formula_sympy: Z = sqrt(R**2 + (X_L - X_C)**2)
formula_latex:  Z = \sqrt{R^2 + (X_L - X_C)^2}
variables:      Z (Ω), R (Ω), X_L (Ω), X_C (Ω)
```
*Dùng cho:* CH tính tổng trở mạch RLC nối tiếp. **Công thức trung tâm của nhóm CH.**  
*Lưu ý:* Khi cộng hưởng X_L = X_C → Z = R.

---

#### F-024 | `ac_current_rms`
```
formula_sympy: I = U / Z
formula_latex:  I = \frac{U}{Z}
variables:      I (A), U (V), Z (Ω)
```
*Dùng cho:* CH tính dòng điện hiệu dụng từ U và Z.

---

#### F-025 | `ac_power_factor`
```
formula_sympy: cos_phi = R / Z
formula_latex:  \cos\varphi = \frac{R}{Z}
variables:      cos_phi (dimensionless), R (Ω), Z (Ω)
```
*Dùng cho:* CH tính hệ số công suất. Khi cộng hưởng cos_phi = 1.

---

#### F-026 | `ac_active_power`
```
formula_sympy: P = U * I * cos_phi
formula_latex:  P = UI\cos\varphi = I^2 R
variables:      P (W), U (V), I (A), cos_phi (dimensionless), R (Ω)
alternative:    P = I**2 * R
```
*Dùng cho:* CH tính công suất tiêu thụ mạch AC. Hai dạng tương đương.

---

#### F-027 | `rlc_voltage_components`
```
formula_sympy: U_R = I * R;  U_L = I * X_L;  U_C = I * X_C
formula_latex:  U_R = IR,\; U_L = IX_L,\; U_C = IX_C
variables:      U_R, U_L, U_C (V), I (A), R, X_L, X_C (Ω)
```
*Dùng cho:* CH tính điện áp thành phần trên từng phần tử.  
*Lưu ý:* U ≠ U_R + U_L + U_C (cộng vector, không cộng đại số).

---

#### F-028 | `rlc_resonance_frequency`
```
formula_sympy: f_0 = 1 / (2 * pi * sqrt(L * C))
formula_latex:  f_0 = \frac{1}{2\pi\sqrt{LC}}
alternative:    omega_0 = 1 / sqrt(L * C)
variables:      f_0 (Hz), L (H), C (F), omega_0 (rad/s)
```
*Dùng cho:* **CH** tính tần số cộng hưởng khi biết L và C.  
*Dùng cho:* **CHLT** — so sánh f_0 với f đề bài → Yes/No.  
*Logic CHLT:* `abs(f - f_0) < tolerance` → "Yes", else "No".

---

#### F-029 | `ac_resonance_condition`
```
formula_sympy: X_L == X_C  →  resonance (Z = R, cos_phi = 1, I_max)
logic:         f_resonance = 1 / (2 * pi * sqrt(L * C))
               is_resonance = abs(f - f_resonance) < 0.5
```
*Dùng cho:* **CHLT** (toàn bộ 20 bài Yes/No). Đây là "formula" dạng điều kiện, không phải phương trình giải.

---

#### F-030 | `capacitance_from_resonance`
```
formula_sympy: C = 1 / (omega**2 * L)
formula_latex:  C = \frac{1}{\omega_0^2 L}
variables:      C (F), omega (rad/s), L (H)
```
*Dùng cho:* CH bài tính C cần thiết để đạt cộng hưởng tại f cho trước (CH063, CH092).

---

### DOMAIN MỚI: `electromagnetic_induction` — Điện từ cảm ứng (cho DDT)

#### F-031 | `solenoid_magnetic_field`
```
formula_sympy: B = mu_0 * n * I
formula_latex:  B = \mu_0 n I,\; n = N/l
variables:      B (T), mu_0 = 4π×10⁻⁷ (H/m), n (turns/m), I (A)
derived:        n = N / l  (turn density từ N turns, length l)
unit_conversions: cm → 1e-2 m, mT → 1e-3 T
```
*Dùng cho:* DDT tính từ trường trong lòng solenoid — **38 bài DDT**.

---

#### F-032 | `solenoid_turn_density`
```
formula_sympy: n = N / l
formula_latex:  n = \frac{N}{l}
variables:      n (turns/m), N (số vòng), l (m)
```
*Dùng cho:* DDT135 và các bài tính mật độ vòng dây trước khi dùng F-031.

---

#### F-033 | `magnetic_flux`
```
formula_sympy: Phi = B * A * cos(theta)
formula_latex:  \Phi = BA\cos\theta
variables:      Phi (Wb), B (T), A (m²), theta (rad) — thường theta=0 → cos=1
unit_conversions: cm² → 1e-4 m², μWb → 1e-6 Wb
```
*Dùng cho:* DDT tính từ thông qua 1 vòng dây hoặc toàn solenoid (DDT141, DDT213, DDT383).

---

#### F-034 | `induced_emf_self_induction`
```
formula_sympy: EMF = -L * (dI / dt)
formula_sympy_approx: EMF = L * delta_I / delta_t   (khi ΔI/Δt đều)
formula_latex:  \mathcal{E} = -L \frac{dI}{dt}
variables:      EMF (V), L (H), delta_I (A), delta_t (s)
```
*Dùng cho:* DDT tính suất điện động tự cảm khi biết L và tốc độ biến thiên dòng — **DDT142, 144, 148, 154** và nhiều bài tương tự.  
*Lưu ý:* Dấu âm chỉ chiều, bài toán thường hỏi magnitude → dùng `abs()`.

---

#### F-035 | `induced_emf_faraday`
```
formula_sympy: EMF = -N * delta_Phi / delta_t
formula_sympy_approx: EMF = delta_Phi / delta_t   (N=1 vòng)
formula_latex:  \mathcal{E} = -N\frac{\Delta\Phi}{\Delta t}
variables:      EMF (V), N (vòng), delta_Phi (Wb), delta_t (s)
```
*Dùng cho:* DDT150 tính EMF từ biến thiên từ thông.

---

#### F-036 | `solenoid_inductance`
```
formula_sympy: L = mu_0 * (N**2 / l) * A
formula_latex:  L = \mu_0 \frac{N^2}{l} A = \mu_0 n^2 V
variables:      L (H), mu_0 = 4π×10⁻⁷, N (vòng), l (m), A (m²)
unit_conversions: cm² → 1e-4 m², mH → 1e-3 H
```
*Dùng cho:* DDT133 tính độ tự cảm solenoid từ kích thước hình học.

---

#### F-037 | `inductor_energy`
```
formula_sympy: W_L = 0.5 * L * I**2
formula_latex:  W_L = \frac{1}{2}LI^2
variables:      W_L (J), L (H), I (A)
unit_conversions: mJ → 1e-3 J, μJ → 1e-6 J
```
*Dùng cho:* DDT134, DDT147, DDT151 và toàn bộ nhóm **NL (inductor energy) — ~95 bài**.  
> ⚡ Đây là công thức thiếu có impact lớn nhất: cover cả DDT lẫn NL.

---

#### F-038 | `magnetic_energy_density`
```
formula_sympy: w = B**2 / (2 * mu_0)
formula_latex:  w = \frac{B^2}{2\mu_0}
variables:      w (J/m³), B (T), mu_0 = 4π×10⁻⁷
```
*Dùng cho:* DDT139, DDT379 tính mật độ năng lượng từ trường trong solenoid.

---

### DOMAIN MỚI: `lc_oscillation` — Mạch dao động LC (cho NL + DDT)

#### F-039 | `lc_total_energy`
```
formula_sympy: W_total = 0.5 * C * U_max**2
formula_sympy_alt: W_total = 0.5 * L * I_max**2
formula_latex:  W = \frac{1}{2}CU_{max}^2 = \frac{1}{2}LI_{max}^2
variables:      W_total (J), C (F), U_max (V), L (H), I_max (A)
```
*Dùng cho:* NL024 và các bài tính tổng năng lượng dao động LC.

---

#### F-040 | `lc_oscillation_frequency`
```
formula_sympy: f = 1 / (2 * pi * sqrt(L * C))
formula_sympy_alt: omega = 1 / sqrt(L * C)
formula_latex:  f = \frac{1}{2\pi\sqrt{LC}},\; \omega = \frac{1}{\sqrt{LC}}
variables:      f (Hz), omega (rad/s), L (H), C (F)
```
*Dùng cho:* NL tính tần số dao động LC (nếu hỏi). Dùng chung công thức với F-028.

---

#### F-041 | `lc_energy_partition`
```
formula_sympy: W_C = 0.5 * C * u**2;  W_L = 0.5 * L * i**2;  W_C + W_L = W_total
formula_latex:  W_C + W_L = const
logic:          khi i=0 → W_L=0 → W_C=W_total (tất cả ở tụ)
                khi u=0 → W_C=0 → W_L=W_total (tất cả ở cuộn)
```
*Dùng cho:* NL định tính — câu hỏi "khi I=0 năng lượng ở đâu?" → W_L = 0, W_C = W_total.  
*Lưu ý:* Đây là "formula" kết hợp với logic, không phải phương trình giải thông thường.

---

#### F-042 | `lc_current_at_equal_energy`
```
formula_sympy: i = I_max / sqrt(2)  (khi W_C = W_L = W_total/2)
formula_latex:  i = \frac{I_{max}}{\sqrt{2}} \approx 0.707 I_{max}
```
*Dùng cho:* NL030 — tính i khi W_C = W_L (70.7% dòng cực đại).

---

### DOMAIN MỚI: `measurement_errors` — Sai số đo lường (cho THCB)

#### F-043 | `absolute_error_instrument`
```
formula_sympy: delta_x = least_count / 2   (hoặc = least_count nếu đề cho trực tiếp)
formula_natural: Sai số dụng cụ = ½ độ chia nhỏ nhất
variables:      delta_x, least_count (cùng đơn vị đo)
```
*Dùng cho:* THCB001, THCB002 — sai số tuyệt đối từ độ chia nhỏ nhất dụng cụ.

---

#### F-044 | `relative_error`
```
formula_sympy: delta_rel = (delta_x / x) * 100
formula_latex:  \delta = \frac{\Delta x}{x} \times 100\%
variables:      delta_rel (%), delta_x (sai số tuyệt đối), x (giá trị đo)
```
*Dùng cho:* THCB002, THCB010, THCB122, THCB124, THCB132 — tính sai số tương đối.

---

#### F-045 | `error_propagation_product`
```
formula_sympy: delta_rel_Z = delta_rel_A + delta_rel_B   (Z = A * B hoặc Z = A / B)
formula_latex:  \frac{\Delta Z}{Z} = \frac{\Delta A}{A} + \frac{\Delta B}{B}
variables:      delta_rel_Z, delta_rel_A, delta_rel_B (%)
example:        R = U/I → ΔR/R = ΔU/U + ΔI/I
```
*Dùng cho:* THCB003, THCB005, THCB008 — truyền sai số qua nhân/chia.

---

#### F-046 | `error_propagation_sum`
```
formula_sympy: delta_Z = delta_A + delta_B   (Z = A + B hoặc Z = A - B)
formula_latex:  \Delta Z = \Delta A + \Delta B
variables:      delta_Z, delta_A, delta_B (cùng đơn vị)
example:        R_total = R1 + R2 → ΔR_total = ΔR1 + ΔR2
```
*Dùng cho:* THCB009 — sai số tổng điện trở nối tiếp.

---

#### F-047 | `mean_absolute_error`
```
formula_sympy: x_mean = sum(x_i) / n
               delta_mean = sum(abs(x_i - x_mean)) / n
formula_latex:  \bar{x} = \frac{\sum x_i}{n},\; \overline{\Delta x} = \frac{\sum|x_i - \bar{x}|}{n}
```
*Dùng cho:* THCB007, THCB023, THCB118, THCB123 — tính trung bình và sai số ngẫu nhiên từ nhiều lần đo.

---

#### F-048 | `absolute_error_from_true`
```
formula_sympy: delta_x = abs(x_measured - x_true)
formula_latex:  \Delta x = |x_{measured} - x_{true}|
```
*Dùng cho:* THCB006, THCB087 — sai số tuyệt đối khi biết giá trị thực.

---

### BỔ SUNG VÀO DOMAIN `electrostatics` — Cho LD + DT vector

#### F-049 | `coulomb_force_vector_superposition`
```
formula_sympy: F_net = sqrt(F1**2 + F2**2 + 2*F1*F2*cos(alpha))
formula_latex:  F_{net} = \sqrt{F_1^2 + F_2^2 + 2F_1F_2\cos\alpha}
variables:      F_net (N), F1, F2 (N), alpha (rad) — góc giữa hai lực
special_cases:
  alpha=0   → F_net = F1 + F2            (cùng chiều)
  alpha=π   → F_net = abs(F1 - F2)       (ngược chiều)
  alpha=π/2 → F_net = sqrt(F1²+F2²)     (vuông góc)
  alpha=π/3 (60°) → F_net = sqrt(F1²+F2²+F1·F2)
```
*Dùng cho:* LD008–LD013 và đa số bài LD/DT có 2+ điện tích — **232 bài vector**.  
> ⚡ Công thức impact lớn thứ 2 sau F-037.

---

#### F-050 | `electric_field_superposition`
```
formula_sympy: E_net = sqrt(E1**2 + E2**2 + 2*E1*E2*cos(alpha))
formula_latex:  E_{net} = \sqrt{E_1^2 + E_2^2 + 2E_1E_2\cos\alpha}
variables:      E_net (V/m), E1, E2 (V/m), alpha (rad)
```
*Dùng cho:* DT bài tính E tổng tại điểm M do nhiều điện tích gây ra.

---

#### F-051 | `zero_field_position`
```
formula_natural: Điểm có E=0 nằm trên đường nối hai điện tích
formula_sympy:   k*q1/x**2 = k*q2/(d-x)**2  → solve for x
                 x: khoảng cách từ q1 đến điểm cần tìm
                 d: khoảng cách q1-q2
variables:       x (m), d (m), q1, q2 (C)
condition:       cùng dấu → điểm giữa; trái dấu → ngoài đoạn
```
*Dùng cho:* DT bài tìm vị trí điểm có E=0 (đơn vị cm).

---

#### F-052 | `capacitor_energy_from_charge`
```
formula_sympy: W = Q**2 / (2 * C)
formula_latex:  W = \frac{Q^2}{2C}
variables:      W (J), Q (C), C (F)
```
*Dùng cho:* TD bài cho Q, hỏi W — dạng thứ 3 của công thức năng lượng tụ điện (F-012 cho C,V; F-052 cho Q,C).

---

## 3. Tổng hợp — 28 công thức cần thêm

| ID | Topic | Domain | Impact (bài) | Ưu tiên |
|----|-------|--------|-------------|---------|
| F-021 | inductive_reactance | ac_circuits | CH ~290 | 🔴 P1 |
| F-022 | capacitive_reactance | ac_circuits | CH ~290 | 🔴 P1 |
| F-023 | rlc_impedance | ac_circuits | CH ~290 | 🔴 P1 |
| F-024 | ac_current_rms | ac_circuits | CH ~150 | 🔴 P1 |
| F-025 | ac_power_factor | ac_circuits | CH ~80 | 🔴 P1 |
| F-026 | ac_active_power | ac_circuits | CH ~60 | 🔴 P1 |
| F-027 | rlc_voltage_components | ac_circuits | CH ~100 | 🔴 P1 |
| F-028 | rlc_resonance_frequency | ac_circuits | CH+CHLT ~80 | 🔴 P1 |
| F-029 | ac_resonance_condition | ac_circuits | CHLT 20 | 🔴 P1 |
| F-030 | capacitance_from_resonance | ac_circuits | CH ~20 | 🟡 P2 |
| F-031 | solenoid_magnetic_field | electromagnetic_induction | DDT ~38 | 🔴 P1 |
| F-032 | solenoid_turn_density | electromagnetic_induction | DDT ~15 | 🟡 P2 |
| F-033 | magnetic_flux | electromagnetic_induction | DDT ~20 | 🟡 P2 |
| F-034 | induced_emf_self_induction | electromagnetic_induction | DDT ~40 | 🔴 P1 |
| F-035 | induced_emf_faraday | electromagnetic_induction | DDT ~10 | 🟡 P2 |
| F-036 | solenoid_inductance | electromagnetic_induction | DDT ~10 | 🟡 P2 |
| F-037 | inductor_energy | electromagnetic_induction | DDT+NL ~130 | 🔴 P1 |
| F-038 | magnetic_energy_density | electromagnetic_induction | DDT ~10 | 🟢 P3 |
| F-039 | lc_total_energy | lc_oscillation | NL ~30 | 🟡 P2 |
| F-040 | lc_oscillation_frequency | lc_oscillation | NL/DDT ~20 | 🟡 P2 |
| F-041 | lc_energy_partition | lc_oscillation | NL ~26 (qualitative) | 🟡 P2 |
| F-042 | lc_current_at_equal_energy | lc_oscillation | NL ~5 | 🟢 P3 |
| F-043 | absolute_error_instrument | measurement_errors | THCB ~30 | 🔴 P1 |
| F-044 | relative_error | measurement_errors | THCB ~35 | 🔴 P1 |
| F-045 | error_propagation_product | measurement_errors | THCB ~20 | 🔴 P1 |
| F-046 | error_propagation_sum | measurement_errors | THCB ~10 | 🟡 P2 |
| F-047 | mean_absolute_error | measurement_errors | THCB ~15 | 🟡 P2 |
| F-048 | absolute_error_from_true | measurement_errors | THCB ~10 | 🟡 P2 |
| F-049 | coulomb_force_vector_superposition | electrostatics | LD ~232 | 🔴 P1 |
| F-050 | electric_field_superposition | electrostatics | DT ~25 | 🟡 P2 |
| F-051 | zero_field_position | electrostatics | DT ~10 | 🟢 P3 |
| F-052 | capacitor_energy_from_charge | electrostatics | TD ~20 | 🟡 P2 |

**Tổng: 32 công thức cần thêm** (20 hiện có + 32 mới = **52 công thức**)

---

## 4. Coverage sau khi bổ sung

| Nhóm | Trước | Sau | Ghi chú |
|------|-------|-----|---------|
| TD | ~80% | ~95% | F-052 thêm dạng W=Q²/2C |
| LD | ~50% | ~80% | F-049 vector; vẫn còn ~20% bài hình học phức tạp |
| DT | ~50% | ~80% | F-050, F-051 |
| NL | ~50% | ~90% | F-037 inductor_energy là key |
| CH | 0% | ~85% | F-021 đến F-030 |
| CHLT | 0% | ~100% | F-028, F-029 đủ giải toàn bộ |
| DDT | 0% | ~75% | F-031–F-038; ~25% còn là định tính (LLM) |
| THCB | 0% | ~85% | F-043–F-048 |
| **Tổng** | **~35%** | **~85%** | Còn ~15% cần LLM fallback (định tính, vector phức tạp) |

---

## 5. Domain mới cần thêm vào `formula_rag.py`

```python
VALID_DOMAINS = [
    "circuits",               # hiện có
    "electrostatics",         # hiện có — mở rộng thêm F-049..F-052
    "ac_circuits",            # MỚI — CH, CHLT
    "electromagnetic_induction",  # MỚI — DDT
    "lc_oscillation",         # MỚI — NL, DDT
    "measurement_errors",     # MỚI — THCB
]
```

## 6. Thứ tự implement (theo impact)

```
Batch 1 — P1 (9 công thức, ~450 bài mới được cover):
  F-037 inductor_energy          (+130 NL+DDT)
  F-049 vector_superposition     (+200 LD)
  F-031 solenoid_magnetic_field  (+38 DDT)
  F-034 induced_emf              (+40 DDT)
  F-043 absolute_error           (+30 THCB)
  F-044 relative_error           (+35 THCB)
  F-045 error_propagation_product(+20 THCB)
  F-021/022/023 XL,XC,Z RLC     (+100 CH)

Batch 2 — P1 AC circuits (6 công thức, ~180 bài CH còn lại):
  F-024 ac_current_rms
  F-025 ac_power_factor
  F-026 ac_active_power
  F-027 rlc_voltage_components
  F-028 resonance_frequency      (+20 CHLT)
  F-029 resonance_condition      (CHLT hoàn thiện)

Batch 3 — P2 (phần còn lại):
  F-033/035/036/038 DDT còn lại
  F-039/040/041 LC oscillation
  F-046/047/048 THCB còn lại
  F-050/051/052 electrostatics bổ sung
```
