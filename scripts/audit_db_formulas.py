"""
scripts/audit_db_formulas.py

Diagnostic script to scan physics_train.csv and identify missing formulas.
Uses the regex_extract and type2_classifier to extract given and find variables,
then cross-references them with the RAG DB.
"""

import sys
import os
import pandas as pd
import json

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.type2_classifier import PhysicsClassifier
from pipeline.type2.regex_extract import extract_given, detect_find_from_verb
from pipeline.type2.formula_rag import load_formula_db

def main():
    print("Loading datasets...")
    df_train = pd.read_csv("data/physics/physics_train.csv")
    df_dev = pd.read_csv("data/physics/physics_dev.csv")
    df = pd.concat([df_train, df_dev], ignore_index=True)
    
    print("Loading RAG DB...")
    db_docs = load_formula_db("data/rag/physics_formulas.json")
    
    # Extract available targets per domain from DB
    db_targets_by_domain = {}
    for doc in db_docs:
        domain = doc.get("domain", "")
        if domain not in db_targets_by_domain:
            db_targets_by_domain[domain] = set()
        
        # In a formula, any variable can be the target
        vars_dict = doc.get("variables", {})
        for var in vars_dict.keys():
            db_targets_by_domain[domain].add(var)

    classifier = PhysicsClassifier()
    
    missing_counts = {}
    total_evaluable = 0
    missing_evaluable = 0
    
    print(f"Scanning {len(df)} questions...")
    for idx, row in df.iterrows():
        question = str(row['question'])
        if pd.isna(question) or not question.strip():
            continue
            
        # 1. Classify
        try:
            pq = classifier.classify_physics(question)
        except Exception:
            continue
            
        domain = pq.domain
        
        # 2. Extract Target
        find = pq.target_variable
        if not find:
            find = detect_find_from_verb(question)
            
        if not find:
            continue
            
        # 3. Check against DB
        total_evaluable += 1
        domain_targets = db_targets_by_domain.get(domain, set())
        
        # Note: In symbol_registry, `find` is already normalized to canonical, 
        # and DB LHS is also normalized to canonical.
        if find not in domain_targets:
            missing_evaluable += 1
            key = f"{domain}::{find}"
            if key not in missing_counts:
                missing_counts[key] = {
                    "count": 0,
                    "examples": []
                }
            missing_counts[key]["count"] += 1
            if len(missing_counts[key]["examples"]) < 3:
                missing_counts[key]["examples"].append(question)
                
    print("\n" + "="*50)
    print("AUDIT REPORT: MISSING FORMULA TARGETS")
    print("="*50)
    print(f"Total questions with detectable targets: {total_evaluable}")
    print(f"Questions missing target in DB: {missing_evaluable} ({(missing_evaluable/total_evaluable)*100:.1f}%)")
    print("\nMissing targets ranked by frequency:")
    
    sorted_missing = sorted(missing_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    for key, data in sorted_missing:
        if data["count"] < 3:
            continue # Skip noise
        domain, find = key.split("::")
        print(f"\n- Domain: {domain} | Missing Target: {find} | Occurrences: {data['count']}")
        for i, ex in enumerate(data['examples']):
            print(f"  Ex {i+1}: {ex[:100]}...")

if __name__ == "__main__":
    main()
