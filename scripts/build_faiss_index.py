"""
scripts/build_faiss_index.py

One-time script: build FAISS index from physics_formulas.json.
Run before starting the API server:
    python scripts/build_faiss_index.py

Output: data/formula_index/index.faiss + data/formula_index/metadata.pkl
"""

import os
import sys
import pickle

import numpy as np

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.formula_rag import load_formula_db


def build_formula_index(
    docs: list[dict],
    save_dir: str = "data/formula_index",
    model_name: str = "all-MiniLM-L6-v2",
) -> None:
    """
    Encode formula docs with sentence-transformers, build IndexFlatL2, save to disk.

    Text representation: "{domain}: {formula_natural} — {keywords joined}"
    This gives FAISS enough signal to distinguish circuit vs electrostatics
    and match variable-specific formulas.
    """
    import faiss
    from sentence_transformers import SentenceTransformer

    os.makedirs(save_dir, exist_ok=True)

    model = SentenceTransformer(model_name)
    texts = [
        f"{d['domain']}: {d['formula_natural']} — {' '.join(d.get('keywords', []))}"
        for d in docs
    ]

    print(f"Encoding {len(texts)} formulas with {model_name}...")
    embeddings = model.encode(texts, show_progress_bar=True).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    index_path = os.path.join(save_dir, "index.faiss")
    meta_path = os.path.join(save_dir, "metadata.pkl")

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(docs, f)

    print(f"Saved FAISS index -> {index_path}")
    print(f"Saved metadata   -> {meta_path}")
    print(f"Index dimension  : {embeddings.shape[1]}")
    print(f"Total vectors    : {index.ntotal}")


if __name__ == "__main__":
    docs = load_formula_db()
    if not docs:
        print("ERROR: No valid formulas found in data/rag/physics_formulas.json")
        sys.exit(1)
    build_formula_index(docs)
    print("\nDone. Run this script once before starting the API server.")
