# Physics Formula RAG - Vector DB Data

Dữ liệu vật lý chuẩn hóa dạng JSON dùng để xây dựng Vector Database (FAISS) phục vụ node ④b Formula RAG nằm trong pipeline EXACT 2026 (Track Type 2).

## Thống kê dữ liệu (Data Metrics)
- *Tổng số tài liệu (Total Documents):* 20
- *Số lượng domains:* 2 (circuits, electrostatics)
- *Độ phủ các Topic:* Đạt 100% các topic cốt lõi yêu cầu cho demo hệ thống.

## Danh sách các Topic đã phủ (Covered Topics)

### 1. Domain: Circuits (Mạch điện)
- *ohms_law:* Định luật Ohm ($V = IR$).
- *series_resistance:* Điện trở tương đương mạch nối tiếp ($R_{total} = R_1 + R_2 + R_3$).
- *parallel_resistance:* Điện trở tương đương mạch song song song cho 2 điện trở ($R = \frac{R_1 R_2}{R_1 + R_2}$).
- *power_vi / power_i2r / power_v2r:* Các công thức tính công suất điện tiêu thụ ($P = VI, P = I^2R, P = \frac{V^2}{R}$).
- *kvl:* Định luật điện áp Kirchhoff trong một vòng kín.
- *kcl:* Định luật dòng điện Kirchhoff tại một nút dòng.
- *voltage_divider:* Công thức bộ chia điện áp.
- *current_divider:* Công thức bộ chia dòng điện cho mạch song song.

### 2. Domain: Electrostatics (Tĩnh điện)
- *capacitor_charge:* Công thức tính điện tích tụ trên tụ điện ($Q = CV$).
- *capacitor_energy:* Năng lượng tích trữ trong tụ điện ($E = \frac{1}{2}CV^2$).
- *series_capacitance:* Điện dung tương đương mạch nối tiếp ($C = \frac{C_1 C_2}{C_1 + C_2}$).
- *parallel_capacitance:* Điện dung tương đương mạch song song ($C_{total} = C_1 + C_2$).
- *electric_field_uniform:* Cường độ điện trường đều giữa hai bản tụ ($E = \frac{V}{d}$).
- *coulombs_law:* Định luật Coulomb tính lực tương tác tĩnh điện giữa hai điện tích điểm ($F = k \frac{q_1 q_2}{r^2}$).
- *electric_potential_energy:* Thế năng tĩnh điện của hệ hai điện tích điểm ($U = k \frac{q_1 q_2}{r}$).
- *capacitor_with_dielectric:* Điện dung của tụ phẳng có hằng số điện môi phẳng ($C = \frac{\epsilon A}{d}$).
- *electric_potential_point:* Điện thế gây ra bởi một điện tích điểm ($V = k \frac{q}{r}$).
- *electric_field_point:* Cường độ điện trường gây ra bởi một điện tích điểm ($E = k \frac{q}{r^2}$).

## Quy tắc thiết kế và Kiểm thử (Validation)
1. *SymPy Compliance:* Tất cả các chuỗi công thức trong trường formula_sympy đã được cấu trúc và kiểm tra tự động bằng thư viện sympy để đảm bảo tương thích tốt với Python (ví dụ: dùng ** thay cho ^, phân tách rõ các phép toán nhân với toán tử *).
2. *Retrieval Optimization:* Mỗi document chứa tối thiểu từ 10 - 15 từ khóa đa dạng (keywords) bao gồm cả ký hiệu đại số lẫn ngôn ngữ tự nhiên để tăng tỷ lệ hit-rate của cơ chế embedding / RAG.

## Nguồn tham khảo (References)
Theo đúng rules quy định của cuộc thi:
1. Tài liệu tập huấn kỹ thuật từ Ban tổ chức kỳ thi EXACT 2026 (Kick-off workshop ngày 04/05).
2. Giáo trình Vật lý đại cương (Phần Điện - Từ), Trường Đại học Bách khoa - ĐHQG TP.HCM (Sách giáo trình chính thống tương thích với nguồn đề thi của BTC).