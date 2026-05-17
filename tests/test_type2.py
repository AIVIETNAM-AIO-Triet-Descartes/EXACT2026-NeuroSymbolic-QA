import csv
from pathlib import Path

import pytest

from api.router import classify_query


def resolve_physics_data_path() -> Path:
	root = Path(__file__).resolve().parents[1] / "data" / "train"
	matches = sorted(root.rglob("Physics_Problems_Text_Only.csv"))
	if not matches:
		raise FileNotFoundError("Physics_Problems_Text_Only.csv not found under data/train")
	return matches[-1]


DATA_PATH = resolve_physics_data_path()
PHYSICS_KEYWORDS = {
	"calculate",
	"resistance",
	"voltage",
	"current",
	"capacitor",
	"circuit",
	"power",
	"energy",
	"charge",
	"ohm",
	"ampere",
	"farad",
	"watt",
	"coulomb",
	"electric",
	"parallel",
	"series",
	"kirchhoff",
}


def load_type2_cases(limit: int = 5):
	cases = []
	with DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
		reader = csv.DictReader(handle)
		for row in reader:
			question = row.get("question", "").strip()
			words = set(question.lower().split())
			if question and PHYSICS_KEYWORDS.intersection(words):
				cases.append(question)
			if len(cases) >= limit:
				return cases
	return cases


TYPE2_CASES = load_type2_cases(5)


@pytest.mark.parametrize("question", TYPE2_CASES)
def test_type2_queries_are_classified_as_type2(question):
	assert classify_query(question, []) == "type2"


def test_type2_dataset_has_at_least_five_samples():
	assert len(TYPE2_CASES) == 5


def test_type2_router_handles_plural_and_punctuation_keywords():
	question = "Determine forces on charges in electric fields."
	assert classify_query(question, []) == "type2"

