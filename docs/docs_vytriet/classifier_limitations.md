# Phân tích các hạn chế của Type 2 Classifier

Tài liệu này ghi nhận lại các "tử huyệt" (bottlenecks) trong cơ chế phân loại câu hỏi vật lý hiện tại của file `pipeline/type2/type2_classifier.py`. Cơ chế hiện tại sử dụng **Keyword Matching (khớp chuỗi thô)** dẫn đến nhiều rủi ro nghiêm trọng (False Positives/Negatives).

## 1. Hàm `_detect_target_variable`: Lỗi nhận diện sai biến CẦN TÌM (Nghiêm trọng nhất)
Hàm này quét qua một danh sách từ khóa theo thứ tự cố định (từ trên xuống dưới) và trả về biến vật lý đầu tiên nó thấy.
*   **Ví dụ:** Nếu câu hỏi là *"Find the **current** if the **voltage** is 5V."*
*   **Bug:** Vòng lặp dictionary sẽ check từ khóa `"voltage"` trước `"current"`. Nó thấy chữ "voltage" có trong câu hỏi, và ngay lập tức trả kết quả là đang đi tìm `V`, trong khi thực tế đề bài yêu cầu tìm `I` (current).
*   **Hậu quả:** SymPy solver sẽ thiết lập sai phương trình, cố gắng giải tìm Voltage (vốn đã có sẵn là 5V) và dẫn đến báo lỗi hoặc văng kết quả rác. Hàm này hoàn toàn phớt lờ cấu trúc ngữ pháp như cụm *"Find the..."* hay *"What is..."*.

## 2. Hàm `_detect_physics_type`: Nhận diện sai dạng bài toán (False Positives)
*   **Lỗi nhầm sang bài toán Yes/No:** Bất kỳ câu hỏi nào có cụm `"does the circuit"` đều bị quy thành bài cộng hưởng Yes/No. Nếu câu hỏi là *"Does the circuit have a higher resistance than 5 ohms?"* -> Nó sẽ bỏ qua công cụ giải toán và đẩy vào luồng check cộng hưởng (Resonance check) -> Kết quả chắc chắn sai.
*   **Lỗi nhầm sang bài Multi-answer:** Dựa vào từ `"and the"`. Từ này quá phổ biến. Ví dụ: *"The voltage is 5V **and the** current is 2A. Find the error of resistance."* Câu này chỉ tìm 1 biến, nhưng vì có chữ `"and the"`, nó bị ép thành bài tìm nhiều đáp án.
*   **Lỗi nhầm sang bài Multi-step:** Dựa vào chữ `"after"`. Ví dụ: *"Find the voltage **after** the switch is closed."* Đây là câu tính toán bình thường (1 bước), nhưng vì dính keyword `"after"`, hệ thống tự làm phức tạp hóa vấn đề.
*   **Vector tĩnh điện (Hình học):** Chỉ quét các từ như `"triangle"`, `"perpendicular"`. Nếu bài toán là hình vuông (`"square"`) hay hình chữ nhật (`"rectangle"`), nó hoàn toàn mù tịt và giải như một đường thẳng vô hướng.

## 3. Hàm `_detect_domain`: Nhận diện sai chuyên đề
*   **Từ khóa "a.c.":** Khai báo kiểm tra là `"a.c."` nhưng chuỗi trước đó đã bị đưa về chữ thường (`q_lower = question.lower()`). Nếu đề ghi là "AC", chữ thường là `"ac"`, nó sẽ KHÔNG khớp với `"a.c."` và có khả năng trượt khỏi chuyên đề Dòng điện xoay chiều.
*   **Đánh đồng bằng Default:** Bất cứ câu nào không khớp các keyword trên đều bị ném tuốt vào chuyên đề Mạch điện DC (`"circuits"`). Nếu mở rộng bộ dataset (như động lực học, quang học) mà quên sửa file này, toàn bộ sẽ bị giải theo công thức... mạch điện.

## Đề xuất giải pháp
Cơ chế "Regex/Keyword thô" này là một điểm nghẽn cổ chai rất lớn, làm lãng phí năng lực của LLM ở những khâu sau. Để nâng cấp, chúng ta có 2 hướng:
1. **Hướng Fix nhẹ (Viết lại Regex):** Thay vì check chuỗi thô, viết lại toàn bộ bằng Regular Expression (RegEx) để bắt đúng ngữ cảnh. Ví dụ: Target Variable phải là chữ đứng ngay sau cụm *"find", "calculate", "what is"*.
2. **Hướng Fix triệt để (Dùng LLM Router):** Gỡ bỏ mớ keyword cứng nhắc này và đưa cho mô hình Qwen 7B tự phân loại thông qua một prompt nhỏ gọn (Zero-shot classification).
