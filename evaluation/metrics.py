import re
from evaluation.answer_compare import compare_answer, parse_number

def evaluate(predictions: list[dict], truth: list[dict]) -> dict:
    """
    Join predictions and truth by id. Call compare_answer for each pair.
    Aggregate metrics overall, by prefix, by kind, and by source.
    """
    STANDARD_PREFIXES = ["LD", "CH", "NL", "TD", "DDT", "THCB", "DT", "CHLT"]
    
    overall = {"total": 0, "evaluable": 0, "correct": 0, "accuracy": 0.0}
    by_prefix = {p: {"total": 0, "evaluable": 0, "correct": 0, "accuracy": 0.0} for p in STANDARD_PREFIXES}
    by_kind = {k: {"total": 0, "evaluable": 0, "correct": 0, "accuracy": 0.0} for k in ["numeric", "yes_no", "qualitative", "multi"]}
    by_source = {}
    
    wrong = []
    skipped = []
    
    # Map predictions by ID for fast lookup
    pred_map = {}
    for p in predictions:
        if isinstance(p, dict) and "id" in p:
            pred_map[p["id"]] = p
            
    for gold_item in truth:
        if not isinstance(gold_item, dict) or "id" not in gold_item:
            continue
            
        qid = gold_item["id"]
        gold_ans = gold_item.get("answer", "")
        gold_unit = gold_item.get("unit", "")
        
        # Determine prefix from ID (e.g. LD401 -> LD)
        prefix_match = re.match(r'^[A-Z]+', qid)
        prefix = prefix_match.group(0) if prefix_match else "UNKNOWN"
        if prefix not in by_prefix:
            by_prefix[prefix] = {"total": 0, "evaluable": 0, "correct": 0, "accuracy": 0.0}
            
        # Determine base kind of gold answer
        gold_str = str(gold_ans).strip()
        if ";" in gold_str:
            base_kind = "multi"
        elif gold_str.lower() in ("yes", "no"):
            base_kind = "yes_no"
        elif parse_number(gold_str) is not None:
            base_kind = "numeric"
        else:
            base_kind = "qualitative"
            
        # Update totals
        overall["total"] += 1
        by_prefix[prefix]["total"] += 1
        by_kind[base_kind]["total"] += 1
        
        # Check if prediction is missing
        if qid not in pred_map:
            skipped.append({
                "id": qid,
                "reason": "missing prediction"
            })
            continue
            
        pred_item = pred_map[qid]
        pred_ans = pred_item.get("answer", "")
        
        # Determine source if present
        source = pred_item.get("source")
        if source:
            source = str(source).strip()
            if source not in by_source:
                by_source[source] = {"total": 0, "evaluable": 0, "correct": 0, "accuracy": 0.0}
            by_source[source]["total"] += 1
            
        # Call compare_answer
        res = compare_answer(pred_ans, gold_ans, gold_unit)
        correct = res.get("correct", False)
        res_kind = res.get("kind", "")
        
        # Decide evaluable vs skipped
        # evaluable = numeric + yes_no + multi (excluding qualitative, unparseable)
        if base_kind == "qualitative":
            skipped.append({
                "id": qid,
                "reason": f"qualitative needs_review: {res.get('detail', '')}"
            })
        elif res_kind == "unparseable":
            skipped.append({
                "id": qid,
                "reason": f"unparseable: {res.get('detail', '')}"
            })
        else:
            # It is evaluable
            overall["evaluable"] += 1
            by_prefix[prefix]["evaluable"] += 1
            by_kind[base_kind]["evaluable"] += 1
            if source:
                by_source[source]["evaluable"] += 1
                
            if correct:
                overall["correct"] += 1
                by_prefix[prefix]["correct"] += 1
                by_kind[base_kind]["correct"] += 1
                if source:
                    by_source[source]["correct"] += 1
            else:
                wrong.append({
                    "id": qid,
                    "gold": gold_ans,
                    "pred": pred_ans,
                    "kind": base_kind
                })
                
    # Calculate accuracies
    def calc_acc(d):
        if d["evaluable"] > 0:
            d["accuracy"] = d["correct"] / d["evaluable"]
        else:
            d["accuracy"] = 0.0
            
    calc_acc(overall)
    for p in by_prefix:
        calc_acc(by_prefix[p])
    for k in by_kind:
        calc_acc(by_kind[k])
    for s in by_source:
        calc_acc(by_source[s])
        
    return {
        "overall": overall,
        "by_prefix": by_prefix,
        "by_kind": by_kind,
        "by_source": by_source,
        "wrong": wrong,
        "skipped": skipped
    }
