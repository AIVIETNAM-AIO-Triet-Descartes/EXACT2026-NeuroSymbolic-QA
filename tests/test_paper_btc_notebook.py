import ast
import json
import re
import unittest
from pathlib import Path


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "paper"
    / "EXACT2026_BTC_Test_Replay_T4_Colab.ipynb"
)
RUNNER_COMMIT = "031298bc63e3a3d48c24b10a1de53ed90becd9f7"


class PaperBtcNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.sources = [
            "".join(cell.get("source") or [])
            for cell in cls.notebook["cells"]
        ]
        cls.all_text = "\n".join(cls.sources)

    def test_notebook_is_clean_and_all_code_parses(self) -> None:
        self.assertEqual(self.notebook["nbformat"], 4)
        for index, cell in enumerate(self.notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            self.assertIsNone(cell.get("execution_count"))
            self.assertEqual(cell.get("outputs"), [])
            try:
                ast.parse("".join(cell.get("source") or []))
            except SyntaxError as exc:
                self.fail(f"Notebook code cell {index} does not parse: {exc}")

    def test_notebook_pins_validated_runner_and_models(self) -> None:
        match = re.search(
            r'VALIDATED_RUNNER_COMMIT = "([0-9a-f]{40})"',
            self.all_text,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), RUNNER_COMMIT)
        self.assertIn(
            "a09a35458c702b33eeacc393d103063234e8bc28",
            self.all_text,
        )
        self.assertIn(
            "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            self.all_text,
        )

    def test_full_command_is_exact_350_job_btc_protocol(self) -> None:
        full_cell = next(source for source in self.sources if "full_cmd = [" in source)
        required_fragments = (
            '"--mode", "full"',
            '"--evaluation-data", "btc-rounds"',
            '"--tracks", "both"',
            '"--quantization", "4bit"',
            '"--temperature", "0"',
            '"--repeats", "1"',
            '"--deterministic-repeats", "1"',
            '"--latency-samples", "0"',
            '"--bootstrap-samples", "2000"',
            '"--cache-shared-stages", "--resume"',
        )
        for fragment in required_fragments:
            self.assertIn(fragment, full_cell)
        self.assertIn(
            'quality["expected_total"] == quality["completed_total"] == 350',
            self.all_text,
        )
        self.assertNotIn("9672", self.all_text)
        self.assertNotIn('"--temperature", "0.1"', self.all_text)
        self.assertNotIn('"--repeats", "3"', self.all_text)
        self.assertNotIn('"--latency-samples", "50"', self.all_text)

    def test_smoke_uses_public_not_hidden_inference_data(self) -> None:
        smoke_cell = next(
            source for source in self.sources if "smoke_cmd = [" in source
        )
        self.assertIn('"--evaluation-data", "public"', smoke_cell)
        self.assertIn("Public smoke PASS: 60/60", smoke_cell)

    def test_log_identity_and_privacy_warnings_are_present(self) -> None:
        self.assertIn(
            "6d5e7a86a5e0a7ed1e1c3e9f43b7228bd930d0e4a7a6133f62ad302483b7fd4b",
            self.all_text,
        )
        self.assertIn(
            "03032ec92f384d3c0ccf76e9f7801cf0b107452805b97115b00061e9c6fdc813",
            self.all_text,
        )
        self.assertIn("Không chia sẻ", self.all_text)
        self.assertIn("predictions.jsonl", self.all_text)
        self.assertIn("stage_cache.jsonl", self.all_text)


if __name__ == "__main__":
    unittest.main()
