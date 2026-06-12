import sys
import os
import csv
import re
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock llm_server_available and get_shared_reasoner before importing physics_parser
import llm
llm.llm_server_available = lambda: False
llm.get_shared_reasoner = lambda: None

from pipeline.type2.physics_parser import physics_parser_node
from pipeline.type2.formula_rag import _ensure_faiss_loaded, _faiss_index, _faiss_docs, _faiss_model, _get_formula_docs

DATASET_PATH = "data/physics/physics_dev.csv"
REPORT_PATH = "reports/rag_evaluation.csv"

def compute_keyword_match(given_keys: list, top_formulas: list[str]) -> bool:
    """
    Check if variables extracted from question (given_keys) appear in the retrieved formula.
    """
    if not given_keys or not top_formulas:
        return False
    
    top_1 = top_formulas[0]
    formula_tokens = set(re.findall(r'[A-Za-z_]\w*', top_1))
    
    # Return True if at least one given variable is present in the formula
    return any(k in formula_tokens for k in given_keys)

def compute_rank_of_correct(cot: str, top_formulas: list[str]) -> int:
    """
    So khớp thô formula_sympy với công thức suy ra từ ground_truth_cot.
    """
    if not cot or not top_formulas:
        return -1
    
    norm_cot = cot.replace(" ", "")
    for i, f_sympy in enumerate(top_formulas):
        parts = f_sympy.split("=")
        if len(parts) == 2:
            lhs = parts[0].strip()
            # Very basic heuristic: check if the target variable LHS is being equated in the CoT
            if f"{lhs}=" in norm_cot or f"={lhs}" in norm_cot:
                return i + 1
                
        # Fallback: check if the normalized RHS is literally in the CoT
        rhs = parts[-1].strip().replace(" ", "")
        if rhs in norm_cot:
            return i + 1
            
    return -1

def main():
    # Đọc dataset physics_dev.csv (200 câu).
    rows = []
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return
        
    with open(DATASET_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    out_f = open(REPORT_PATH, "w", encoding="utf-8", newline="")
    fieldnames = ["id", "question", "ground_truth_cot", "retrieved_formulas", "keyword_match", "rank_of_correct", "human_eval"]
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    writer.writeheader()

    _ensure_faiss_loaded()
    docs = _get_formula_docs()

    # Khởi tạo physics_parser_node ở chế độ regex-only (bypass LLM).
    # Patch llm_server_available to always return False so LLM augment is bypassed
    with patch("pipeline.type2.physics_parser.llm_server_available", return_value=False):
        for row in rows:
            qid = row["id"]
            question = row["question"]
            cot = row.get("cot", "")
            
            state = {"question": question, "confidence": 1.0}
            state = physics_parser_node(state)
            parsed = state.get("parsed_physics", {})
            
            given_keys = list(parsed.get("given", {}).keys())
            domain = parsed.get("domain", "")
            find = parsed.get("find", "")
            
            # Gọi retrieval component để lấy retrieved_formulas.
            # Tái tạo lại logic Layer 1 và Layer 2 FAISS của formula_rag để lấy top-k (thay vì chỉ lấy top-1)
            candidates = [
                d for d in docs
                if d.get("domain") == domain and find and find in d.get("variables", {})
            ]
            
            top_k_formulas = []
            if len(candidates) == 1:
                top_k_formulas.append(candidates[0]["formula_sympy"])
            else:
                search_pool = candidates if candidates else docs
                if _faiss_index is not None and _faiss_model is not None and _faiss_docs is not None:
                    query = f"{domain} {find} {question}".strip()
                    emb = _faiss_model.encode([query]).astype("float32")
                    k = min(len(_faiss_docs), 10)
                    _, I = _faiss_index.search(emb, k=k)
                    
                    for idx in I[0]:
                        if 0 <= idx < len(_faiss_docs) and _faiss_docs[idx] in search_pool:
                            top_k_formulas.append(_faiss_docs[idx]["formula_sympy"])
                            
                    # Expand search if pool was restricted but yielded no matches
                    if not top_k_formulas and search_pool is not docs:
                        _, I2 = _faiss_index.search(emb, k=k)
                        for idx in I2[0]:
                            if 0 <= idx < len(_faiss_docs):
                                top_k_formulas.append(_faiss_docs[idx]["formula_sympy"])
            
            # Fallback if no FAISS results but candidates exist
            if not top_k_formulas and candidates:
                top_k_formulas = [c["formula_sympy"] for c in candidates[:10]]
            
            # Tính các score
            kw_match = compute_keyword_match(given_keys, top_k_formulas)
            rank_correct = compute_rank_of_correct(cot, top_k_formulas)
            
            # Xuất file report ra reports/rag_evaluation.csv.
            writer.writerow({
                "id": qid,
                "question": question,
                "ground_truth_cot": cot,
                "retrieved_formulas": " | ".join(top_k_formulas),
                "keyword_match": kw_match,
                "rank_of_correct": rank_correct,
                "human_eval": ""
            })

    out_f.close()
    print(f"Done evaluating RAG. Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    main()
