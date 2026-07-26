import json
import os
import pickle
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from pipeline.type2 import formula_rag


class _FakeIndex:
    d = 384


class _FakeSentenceTransformer:
    calls = []

    def __init__(self, model_name, **kwargs):
        self.calls.append((model_name, kwargs))

    def get_sentence_embedding_dimension(self):
        return 384


class FormulaRagEncoderTest(unittest.TestCase):
    def setUp(self):
        self.old_environment = {
            name: os.environ.get(name)
            for name in (
                "FORMULA_RAG_DISABLE_SEMANTIC",
                "FORMULA_RAG_EMBEDDING_MODEL",
                "FORMULA_RAG_EMBEDDING_REVISION",
            )
        }
        for name in self.old_environment:
            os.environ.pop(name, None)
        self._reset_singleton()
        _FakeSentenceTransformer.calls.clear()

    def tearDown(self):
        self._reset_singleton()
        for name, value in self.old_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    @staticmethod
    def _reset_singleton():
        formula_rag._faiss_index = None
        formula_rag._faiss_docs = None
        formula_rag._faiss_model = None
        formula_rag._faiss_embedding_identity = None

    @staticmethod
    def _write_index_fixture(root: Path, *, revision: str, dimension: int = 384):
        (root / "index.faiss").write_bytes(b"mocked by test")
        with (root / "metadata.pkl").open("wb") as handle:
            pickle.dump([{"id": "fixture"}], handle)
        (root / "encoder.json").write_text(
            json.dumps(
                {
                    "model": formula_rag.DEFAULT_EMBEDDING_MODEL,
                    "revision": revision,
                    "embedding_dimension": dimension,
                }
            ),
            encoding="utf-8",
        )

    def test_loader_uses_manifest_model_and_immutable_revision(self):
        fake_faiss = types.SimpleNamespace(read_index=lambda _: _FakeIndex())
        fake_st = types.SimpleNamespace(
            SentenceTransformer=_FakeSentenceTransformer
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_index_fixture(
                root, revision=formula_rag.DEFAULT_EMBEDDING_REVISION
            )
            with mock.patch.dict(
                sys.modules,
                {"faiss": fake_faiss, "sentence_transformers": fake_st},
            ):
                index, docs, model = formula_rag._load_faiss_index(str(root))

        self.assertIsInstance(index, _FakeIndex)
        self.assertEqual(docs, [{"id": "fixture"}])
        self.assertIsInstance(model, _FakeSentenceTransformer)
        self.assertEqual(
            _FakeSentenceTransformer.calls,
            [
                (
                    formula_rag.DEFAULT_EMBEDDING_MODEL,
                    {"revision": formula_rag.DEFAULT_EMBEDDING_REVISION},
                )
            ],
        )

    def test_disable_never_calls_loader(self):
        os.environ["FORMULA_RAG_DISABLE_SEMANTIC"] = "1"
        with mock.patch.object(formula_rag, "_load_faiss_index") as loader:
            formula_rag._ensure_faiss_loaded("/path/that/must/not/be/read")
        loader.assert_not_called()

    def test_manifest_revision_or_dimension_drift_rejects_index(self):
        fake_faiss = types.SimpleNamespace(read_index=lambda _: _FakeIndex())
        fake_st = types.SimpleNamespace(
            SentenceTransformer=_FakeSentenceTransformer
        )
        for revision, dimension in (
            ("0" * 40, 384),
            (formula_rag.DEFAULT_EMBEDDING_REVISION, 768),
        ):
            with self.subTest(revision=revision, dimension=dimension):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._write_index_fixture(
                        root, revision=revision, dimension=dimension
                    )
                    with mock.patch.dict(
                        sys.modules,
                        {"faiss": fake_faiss, "sentence_transformers": fake_st},
                    ):
                        loaded = formula_rag._load_faiss_index(str(root))
                self.assertEqual(loaded, (None, None, None))

    def test_loaded_singleton_rejects_encoder_change(self):
        formula_rag._faiss_index = _FakeIndex()
        formula_rag._faiss_docs = []
        formula_rag._faiss_model = _FakeSentenceTransformer(
            formula_rag.DEFAULT_EMBEDDING_MODEL
        )
        formula_rag._faiss_embedding_identity = (
            formula_rag.embedding_model_identity()
        )
        os.environ["FORMULA_RAG_EMBEDDING_REVISION"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "encoder changed"):
            formula_rag._ensure_faiss_loaded()


if __name__ == "__main__":
    unittest.main()
