import argparse
import csv
import json
import os
import sys

# Add the project root to sys.path so we can import from evaluation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import evaluate

def load_csv(filepath):
    data = []
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def load_json(filepath):
    with open(filepath, mode='r', encoding='utf-8') as f:
        return json.load(f)

def write_markdown_report(metrics_result, out_md_path):
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(out_md_path)), exist_ok=True)
    
    with open(out_md_path, mode='w', encoding='utf-8') as f:
        f.write("# Evaluation Report\n\n")
        
        # Overall Metrics
        overall = metrics_result['overall']
        f.write("## Overall Metrics\n")
        f.write("| Total | Evaluable | Correct | Acc% |\n")
        f.write("|-------|-----------|---------|------|\n")
        f.write(f"| {overall['total']} | {overall['evaluable']} | {overall['correct']} | {overall['accuracy']*100:.2f}% |\n\n")
        
        # By Prefix
        f.write("## Metrics by Prefix\n")
        f.write("| Prefix | Total | Evaluable | Correct | Acc% |\n")
        f.write("|--------|-------|-----------|---------|------|\n")
        for p, stats in sorted(metrics_result['by_prefix'].items()):
            f.write(f"| {p} | {stats['total']} | {stats['evaluable']} | {stats['correct']} | {stats['accuracy']*100:.2f}% |\n")
        f.write("\n")
        
        # By Kind
        f.write("## Metrics by Answer Kind\n")
        f.write("| Kind | Total | Evaluable | Correct | Acc% |\n")
        f.write("|------|-------|-----------|---------|------|\n")
        for k, stats in sorted(metrics_result['by_kind'].items()):
            f.write(f"| {k} | {stats['total']} | {stats['evaluable']} | {stats['correct']} | {stats['accuracy']*100:.2f}% |\n")
        f.write("\n")
        
        # By Source (if present and not empty)
        if 'by_source' in metrics_result and metrics_result['by_source']:
            f.write("## Metrics by Source\n")
            f.write("| Source | Total | Evaluable | Correct | Acc% |\n")
            f.write("|--------|-------|-----------|---------|------|\n")
            for s, stats in sorted(metrics_result['by_source'].items()):
                f.write(f"| {s} | {stats['total']} | {stats['evaluable']} | {stats['correct']} | {stats['accuracy']*100:.2f}% |\n")
            f.write("\n")
            
        # Wrong cases
        f.write("## Wrong Cases\n")
        if metrics_result['wrong']:
            f.write("| ID | Kind | Gold | Pred |\n")
            f.write("|----|------|------|------|\n")
            for w in metrics_result['wrong']:
                id_val = w.get('id', '')
                kind_val = w.get('kind', '')
                gold_val = str(w.get('gold', '')).replace('\n', ' ')
                pred_val = str(w.get('pred', '')).replace('\n', ' ')
                f.write(f"| {id_val} | {kind_val} | `{gold_val}` | `{pred_val}` |\n")
        else:
            f.write("No wrong cases.\n")
        f.write("\n")
        
        # Skipped cases
        f.write("## Skipped Cases\n")
        if metrics_result['skipped']:
            f.write("| ID | Reason | Gold | Pred |\n")
            f.write("|----|--------|------|------|\n")
            for s in metrics_result['skipped']:
                id_val = s.get('id', '')
                reason_val = s.get('reason', '')
                gold_val = str(s.get('gold', '')).replace('\n', ' ')
                pred_val = str(s.get('pred', '')).replace('\n', ' ')
                f.write(f"| {id_val} | {reason_val} | `{gold_val}` | `{pred_val}` |\n")
        else:
            f.write("No skipped cases.\n")
        f.write("\n")

def write_json_report(metrics_result, out_md_path):
    out_json_path = os.path.splitext(out_md_path)[0] + '.json'
    with open(out_json_path, mode='w', encoding='utf-8') as f:
        json.dump(metrics_result, f, indent=4, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Evaluate predictions against ground truth.")
    parser.add_argument('--pred', type=str, default='output/predictions.json', help='Path to predictions JSON file')
    parser.add_argument('--truth', type=str, default='data/train/Physics_Problems_Text_Only.csv', help='Path to ground truth CSV file')
    parser.add_argument('--out', type=str, default='reports/eval_report.md', help='Path to output Markdown report')
    args = parser.parse_args()

    # Load data
    try:
        truth_data = load_csv(args.truth)
    except Exception as e:
        print(f"Error loading truth data: {e}")
        sys.exit(1)
        
    try:
        pred_data = load_json(args.pred)
    except Exception as e:
        print(f"Error loading prediction data: {e}")
        sys.exit(1)
        
    # Evaluate
    print(f"Loaded {len(truth_data)} ground truth records and {len(pred_data)} predictions.")
    metrics_result = evaluate(pred_data, truth_data)
    
    # Generate reports
    write_markdown_report(metrics_result, args.out)
    write_json_report(metrics_result, args.out)
    
    # Print summary
    overall = metrics_result['overall']
    print("\n--- Evaluation Summary ---")
    print(f"Total:      {overall['total']}")
    print(f"Evaluable:  {overall['evaluable']}")
    print(f"Correct:    {overall['correct']}")
    print(f"Accuracy:   {overall['accuracy']*100:.2f}%")
    print(f"--------------------------")
    print(f"Reports saved to: {args.out} and its .json equivalent")

if __name__ == '__main__':
    main()
