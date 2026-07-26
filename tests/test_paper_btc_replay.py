import argparse
import json
import tempfile
import unittest
from pathlib import Path

from paper import run_paper_experiments as runner


def make_record(
    *,
    track: str,
    query_id: str,
    query: str,
    premises: list[str],
    options: list[str] | None,
    answer: str,
    unit: str = "",
    premises_used: list[int] | None = None,
    aliases: list[str] | None = None,
    historical_answer: str = "must-not-be-used",
) -> dict:
    request = {
        "query_id": query_id,
        "type": track,
        "query": query,
        "premises": premises,
    }
    if options is not None:
        request["options"] = options
    return {
        "query_id": query_id,
        "type": track,
        "request_payload": request,
        "expected": {
            "answer": answer,
            "unit": unit,
            "premises_used": premises_used or [],
            "aliases": aliases or [],
        },
        "model_response": {"answer": historical_answer},
        "result": {"p1_score": 100},
        "status": "correct",
    }


def write_round(root: Path, round_name: str, records: list[dict]) -> Path:
    path = root / f"{round_name}.json"
    path.write_text(
        json.dumps(
            {
                "eval_round": round_name,
                "sample_version": f"synthetic-{round_name}",
                "logs": records,
                "summary": {"score": 0},
            }
        ),
        encoding="utf-8",
    )
    return path


def synthetic_sources(root: Path) -> tuple[Path, Path]:
    # The raw ID intentionally collides across rounds; the loader must namespace it.
    round1 = write_round(
        root,
        "round1",
        [
            make_record(
                track="type1",
                query_id="T1_same",
                query="Does alpha imply beta?",
                premises=["Alpha holds.", "Alpha implies beta."],
                options=["Yes", "No", "Uncertain"],
                answer="Yes",
                premises_used=[0, 1],
                aliases=["true"],
            ),
            make_record(
                track="type2",
                query_id="T2_r1",
                query="Synthetic physics question one.",
                premises=[],
                options=None,
                answer="5",
                unit="J",
            ),
        ],
    )
    round2 = write_round(
        root,
        "round2",
        [
            make_record(
                track="type1",
                query_id="T1_same",
                query="Who satisfies the synthetic rule?",
                premises=["A synthetic subject satisfies the rule."],
                options=[],
                answer="Synthetic subject",
                premises_used=[0],
                aliases=["the synthetic subject"],
            ),
            make_record(
                track="type2",
                query_id="T2_r2",
                query="Synthetic physics question two.",
                premises=[],
                options=[],
                answer="2",
                unit="m",
            ),
        ],
    )
    return round1, round2


def canonical_args() -> argparse.Namespace:
    return runner.build_parser().parse_args(
        [
            "--mode",
            "full",
            "--evaluation-data",
            runner.EVALUATION_BTC_ROUNDS,
            "--temperature",
            "0",
            "--repeats",
            "1",
            "--deterministic-repeats",
            "1",
            "--latency-samples",
            "0",
        ]
    )


class PaperBtcReplayTests(unittest.TestCase):
    def test_loader_projects_only_request_and_gold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            type1, type2 = runner.load_btc_test_replay(
                synthetic_sources(Path(directory)),
                verify_known_identity=False,
            )

        self.assertEqual(
            [item.query_id for item in type1],
            ["round1:T1_same", "round2:T1_same"],
        )
        self.assertEqual(len({item.query_id for item in [*type1, *type2]}), 4)
        self.assertEqual(type1[0].question, "Does alpha imply beta?")
        self.assertEqual(
            type1[0].premises,
            ["Alpha holds.", "Alpha implies beta."],
        )
        self.assertEqual(type1[0].options, ["Yes", "No", "Uncertain"])
        self.assertEqual(type1[0].gold_answer, "Yes")
        self.assertEqual(type1[0].gold_premises, [0, 1])
        self.assertEqual(type1[0].gold_aliases, ["true"])
        self.assertEqual(type1[1].options, [])
        self.assertFalse(type1[1].metadata["z3_eligible"])
        self.assertEqual(type2[0].options, [])

        inference_projection = json.dumps(
            {
                "question": type1[0].question,
                "premises": type1[0].premises,
                "options": type1[0].options,
            }
        )
        self.assertNotIn("must-not-be-used", inference_projection)

    def test_loader_rejects_duplicate_within_round(self) -> None:
        duplicate = make_record(
            track="type1",
            query_id="duplicate",
            query="Does the synthetic statement hold?",
            premises=["Synthetic premise."],
            options=["Yes", "No", "Uncertain"],
            answer="Yes",
            premises_used=[0],
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            round1 = write_round(root, "round1", [duplicate, duplicate])
            round2 = write_round(
                root,
                "round2",
                [
                    make_record(
                        track="type2",
                        query_id="other",
                        query="Synthetic physics.",
                        premises=[],
                        options=[],
                        answer="1",
                    )
                ],
            )
            with self.assertRaisesRegex(ValueError, "duplicate query_id"):
                runner.load_btc_test_replay(
                    [round1, round2],
                    verify_known_identity=False,
                )

    def test_alias_scoring_is_safe_for_letters_and_phrases(self) -> None:
        self.assertTrue(
            runner.score_type1(
                "The selected module is Module Orion.",
                [],
                "A",
                [],
                ["Module Orion"],
            )["answer_correct"]
        )
        self.assertTrue(
            runner.score_type1("A", [], "A", [], [])["answer_correct"]
        )
        self.assertFalse(
            runner.score_type1(
                "A longer unrelated sentence",
                [],
                "A",
                [],
                [],
            )["answer_correct"]
        )

    def test_canonical_matrix_is_350_and_gate_is_strict(self) -> None:
        args = canonical_args()
        jobs = runner.expected_experiment_jobs(args)
        self.assertEqual(sum(int(job["expected"]) for job in jobs), 350)
        self.assertEqual(len(jobs), 7)

        records: list[dict] = []
        for job in jobs:
            for index in range(int(job["expected"])):
                records.append(
                    {
                        "phase": job["phase"],
                        "track": job["track"],
                        "variant": job["variant"],
                        "repeat": job["repeat"],
                        "query_id": f"{job['track']}:{index}",
                        "status": "completed",
                    }
                )
        complete = runner.experiment_completeness(records, args)
        self.assertEqual(complete["expected_total"], 350)
        self.assertEqual(complete["completed_total"], 350)
        self.assertTrue(complete["btc_replay_scope"])
        self.assertTrue(complete["paper_ready"])

        incomplete = runner.experiment_completeness(records[:-1], args)
        self.assertEqual(incomplete["completed_total"], 349)
        self.assertFalse(incomplete["paper_ready"])


if __name__ == "__main__":
    unittest.main()
