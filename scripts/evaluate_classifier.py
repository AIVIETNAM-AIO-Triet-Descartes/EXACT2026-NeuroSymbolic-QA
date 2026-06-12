        
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.type2_classifier import PhysicsClassifier
from evaluation.answer_compare import parse_number

DATASET_PATH = "data/physics/physics_dev.csv"
REPORT_PATH = "reports/classifier_evaluation.csv"

def get_ground_truth_answer_type(answer: str, unit: str) -> str:
    # Parse ground_truth_answer_type từ file CSV sử dụng hàm parse_number.
    ans_lower = str(answer).strip().lower()
    if ans_lower in ("yes", "no"):
        return "yes_no"
    if ";" in answer:
        return "multi_answer"
    
    # Try parsing as number
    if parse_number(answer) is not None:
        return "numeric"
        
    return "qualitative"

def compute_anomaly_flag(pred_type: str, gt_type: str) -> bool:
    # Tích hợp tính logic anomaly_flag.
    # Dạng toán (tính toán số học/đại số)
    math_types = [
        "single_formula", "multi_step", "circuit", "electrostatic", 
        "vector", "error_calc", "electromagnetic", "multi_answer"
    ]
    
    # Nếu hệ thống phân loại là dạng bài tính toán nhưng đáp án thực tế
    # lại là qualitative/yes_no thì đánh cờ anomaly.
    if pred_type in math_types and gt_type in ("qualitative", "yes_no"):
        return True
    return False

def main():
    # Đọc dataset physics_dev.csv.
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return

    rows = []
    with open(DATASET_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    out_f = open(REPORT_PATH, "w", encoding="utf-8", newline="")
    fieldnames = [
        "id", "question", "predicted_domain", "predicted_type",
        "target_variable", "ground_truth_answer_type", "anomaly_flag"
    ]
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    writer.writeheader()

    # Gọi hàm phân loại PhysicsClassifier để test rule base.
    classifier = PhysicsClassifier()

    for row in rows:
        qid = row["id"]
        question = row["question"]
        answer = row.get("answer", "")
        unit = row.get("unit", "")
        
        # Phân loại câu hỏi
        classified = classifier.classify_physics(question)
        
        # Lấy ground truth answer type
        gt_type = get_ground_truth_answer_type(answer, unit)
        
        # Tính cờ anomaly
        anomaly = compute_anomaly_flag(classified.question_type.value, gt_type)
        
        target_var = classified.target_variable if classified.target_variable else ""
        
        # Xuất file report ra reports/classifier_evaluation.csv.
        writer.writerow({
            "id": qid,
            "question": question,
            "predicted_domain": classified.domain,
            "predicted_type": classified.question_type.value,
            "target_variable": target_var,
            "ground_truth_answer_type": gt_type,
            "anomaly_flag": anomaly
        })

    out_f.close()
    print(f"Done evaluating Classifier. Report saved to {REPORT_PATH}")

    total_count = 0
    anomaly_count = 0
    gt_distribution = {}
    pred_distribution = {}

    # Đọc lại file báo cáo vừa ghi để tính toán số liệu thống kê độc lập
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_count += 1
            if row["anomaly_flag"] == "True":
                anomaly_count += 1
            
            gt_type = row["ground_truth_answer_type"]
            pred_type = row["predicted_type"]
            
            gt_distribution[gt_type] = gt_distribution.get(gt_type, 0) + 1
            pred_distribution[pred_type] = pred_distribution.get(pred_type, 0) + 1

    print("\n" + "="*60)
    print(" PHYSICS CLASSIFIER EVALUATION REPORT")
    print("="*60)
    print(f" Total questions evaluated: {total_count}")
    print(f" Critical routing mismatches (Anomaly Flag = True): {anomaly_count}")
    
    anomaly_rate = (anomaly_count / total_count * 100) if total_count > 0 else 0
    print(f" Misrouting / Fallback Rate: {anomaly_rate:.2f}%")
    
    print("\n Ground Truth Answer Type Distribution:")
    for gt_k, gt_v in gt_distribution.items():
        print(f"  - {gt_k}: {gt_v} questions")
        
    print("\n PSystem Predicted Type Distribution:")
    for pred_k, pred_v in pred_distribution.items():
        print(f"  - {pred_k}: {pred_v} questions")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

