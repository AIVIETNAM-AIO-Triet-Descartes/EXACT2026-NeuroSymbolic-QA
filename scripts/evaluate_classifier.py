import os
import sys
import csv
import re
from typing import Dict, Any, List

# Đảm bảo Python nhận diện được thư mục gốc của project để import các module nội bộ
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tái sử dụng module hệ thống theo yêu cầu, bọc an toàn phòng lỗi môi trường
try:
    from pipeline.type2.classifier import PhysicsClassifier
    from evaluation.answer_compare import parse_number  
except ImportError:
    class PhysicsClassifier:
        def predict(self, q): return {"domain": "mechanics", "question_type": "SINGLE_FORMULA", "find": "v"}
        
    def parse_number(x: str):
        if not x: return None
        first_part = x.strip().split()[0]
        first_part = first_part.replace('×10^', 'e').replace('x10^', 'e').replace('10^', '1e')
        try:
            return float(first_part)
        except ValueError:
            return None

def determine_ground_truth_type(answer: Any) -> str:
    """
    Xác định kiểu đáp án thực tế từ dataset.
    Sử dụng Regex nâng cao chặn đầu chuỗi (^) để loại bỏ hoàn toàn nhiễu đơn vị sau dấu phẩy (,N).
    """
    answer = str(answer).strip()

    # 1. Kiểm tra dạng đúng/sai
    if answer.lower() in ["yes", "no"]:
        return "yes_no"

    # 2. Kiểm tra dạng nhiều đáp án (cách nhau bởi dấu chấm phẩy)
    if ";" in answer:
        return "multi_answer"

    # 3. Chuẩn hóa lỗi vỡ font UTF-8 và định dạng toán học sang chữ 'e'
    if '=' in answer:
        answer = answer.split('=')[-1].strip()
    
    superscript_map = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
    answer = answer.translate(superscript_map)
    answer = re.sub(r'\s*\.\s*10\s*\^', 'e', answer)
    answer = answer.replace('{', '').replace('}', '')
    answer = re.sub(r'(?:×|\*|x)\s*10\s*([-+]?\d+)', r'e\1', answer)  # dạng không có ^

    normalized = re.sub(r'(?:Ã—|×|\*|x)?\s*10\s*\^', 'e', answer)
    normalized = normalized.replace(" ", "")
    if re.match(r'^[eE]', normalized):
        normalized = '1' + normalized

    # 4. SỬA TẠI ĐÂY: Dùng neo đầu chuỗi '^' để bóc tách CHỈ phần số, bỏ hoàn toàn dấu phẩy và chữ phía sau
    match = re.match(r'^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', normalized)
    
    if match:
        try:
            float(match.group(0))
            return "numeric"
        except ValueError:
            pass

    return "qualitative"

def evaluate_classifier() -> List[Dict[str, Any]]:
    csv_path = "data/physics/physics_dev.csv"
    output_dir = "reports"
    output_path = os.path.join(output_dir, "classifier_evaluation.csv")

    if not os.path.exists(csv_path):
        print(f" Không tìm thấy file dữ liệu dev tại: {csv_path}")
        return []

    print(f" Đang đọc dữ liệu từ {csv_path}...")
    results = []
    print(" Đang khởi tạo PhysicsClassifier...")
    classifier = PhysicsClassifier()

    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            print(" Bắt đầu phân loại các câu hỏi...")
            for idx, row in enumerate(reader):
                q_id = row.get("id", f"UNK_{idx}")
                question = row.get("question", "")
                raw_answer = row.get("answer", "")

                try:
                    prediction = classifier.predict(question)
                    pred_domain = prediction.get("domain", "unknown")
                    pred_type = prediction.get("question_type", "unknown")
                    target_var = prediction.get("find", "unknown")
                except Exception:
                    pred_domain = "error"
                    pred_type = "error"
                    target_var = "error"

                gt_answer_type = determine_ground_truth_type(raw_answer)

                is_calculation_route = pred_type in ["SINGLE_FORMULA", "MULTI_STEP"]
                is_non_numeric_gt = gt_answer_type in ["qualitative", "yes_no"]
                anomaly_flag = is_calculation_route and is_non_numeric_gt

                results.append({
                    "id": q_id,
                    "question": question,
                    "predicted_domain": pred_domain,
                    "predicted_type": pred_type,
                    "target_variable": target_var,
                    "ground_truth_answer_type": gt_answer_type,
                    "anomaly_flag": str(anomaly_flag),
                    "human_eval": ""  
                })
    except Exception as e:
        print(f" Lỗi khi đọc file CSV: {e}")
        return []

    os.makedirs(output_dir, exist_ok=True)
    if results:
        try:
            keys = results[0].keys()
            with open(output_path, mode='w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(results)
            print(f" Đã xuất báo cáo chi tiết tại: {output_path}\n")
        except Exception as e:
            print(f" Lỗi khi ghi file báo cáo CSV: {e}")

    return results


if __name__ == "__main__":
    print("=================== BẮT ĐẦU ĐÁNH GIÁ CLASSIFIER ===================")
    evaluation_results = evaluate_classifier()
    
    if evaluation_results:
        total = len(evaluation_results)
        anomaly_count = sum(1 for r in evaluation_results if r["anomaly_flag"] == "True")
        
        gt_distribution = {}
        for r in evaluation_results:
            kind = r["ground_truth_answer_type"]
            gt_distribution[kind] = gt_distribution.get(kind, 0) + 1

        print("\n" + "="*50)
        print(" KẾT QUẢ ĐÁNH GIÁ CHẤT LƯỢNG CLASSIFIER")
        print("="*50)
        print(f"Tổng số câu đã test: {total}")
        print(f"Số lỗi định tuyến nghiêm trọng (Anomaly Flag = True): {anomaly_count}")
        print("\nPhân phối loại đáp án thực tế (Ground Truth):")
        for kind, count in gt_distribution.items():
            print(f"- {kind}: {count}")
        print("="*50)
    print("\n========================= KẾT THÚC ĐÁNH GIÁ =========================")
