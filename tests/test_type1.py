import json
from pathlib import Path

import pytest

from api.router import classify_query


def resolve_logic_data_path() -> Path:
	root = Path(__file__).resolve().parents[1] / "data" / "train"
	matches = sorted(root.rglob("Logic_Based_Educational_Queries.json"))
	if not matches:
		raise FileNotFoundError("Logic_Based_Educational_Queries.json not found under data/train")
	return matches[-1]


DATA_PATH = resolve_logic_data_path()


def load_type1_cases(limit: int = 5):
	with DATA_PATH.open("r", encoding="utf-8") as handle:
		records = json.load(handle)

	cases = []
	for record in records:
		questions = record.get("questions", [])
		premises = record.get("premises-NL", [])
		for question in questions:
			cases.append((question, premises))
			if len(cases) >= limit:
				return cases
	return cases


TYPE1_CASES = load_type1_cases(5)


@pytest.mark.parametrize("question,premises", TYPE1_CASES)
def test_type1_queries_are_classified_as_type1(question, premises):
	assert classify_query(question, premises) == "type1"


def test_type1_dataset_has_at_least_five_samples():
	assert len(TYPE1_CASES) == 5

