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
import hashlib

import numpy as np

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.formula_rag import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_REVISION,
    load_formula_db,
)


def build_formula_index(
    docs: list[dict],
    save_dir: str = "data/formula_index",
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    model_revision: str = DEFAULT_EMBEDDING_REVISION,
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

    model = SentenceTransformer(model_name, revision=model_revision)
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
    encoder_path = os.path.join(save_dir, "encoder.json")
    with open(encoder_path, "w", encoding="utf-8") as f:
        import json

        json.dump(
            {
                "model": model_name,
                "revision": model_revision,
                "embedding_dimension": int(embeddings.shape[1]),
            },
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print(f"Saved FAISS index -> {index_path}")
    print(f"Saved metadata   -> {meta_path}")
    print(f"Saved encoder    -> {encoder_path}")
    # MD5 Drift Guard: save hash
    db_path = "data/rag/physics_formulas.json"
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        md5_path = os.path.join(save_dir, "db_md5.txt")
        with open(md5_path, "w") as f:
            f.write(md5)
        print(f"Saved DB MD5     -> {md5_path}")

    print(f"Index dimension  : {embeddings.shape[1]}")
    print(f"Total vectors    : {index.ntotal}")


if __name__ == "__main__":
    docs = load_formula_db()
    if not docs:
        print("ERROR: No valid formulas found in data/rag/physics_formulas.json")
        sys.exit(1)
    build_formula_index(docs)
    print("\nDone. Run this script once before starting the API server.")
