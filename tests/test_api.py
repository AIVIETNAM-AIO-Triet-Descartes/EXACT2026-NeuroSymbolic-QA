import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from api.schemas import UnifiedRequest


client = TestClient(app)


def resolve_logic_data_path() -> Path:
	root = Path(__file__).resolve().parents[1] / "data" / "train"
	matches = sorted(root.rglob("Logic_Based_Educational_Queries.json"))
	if not matches:
		raise FileNotFoundError("Logic_Based_Educational_Queries.json not found under data/train")
	return matches[-1]


LOGIC_DATA_PATH = resolve_logic_data_path()


def load_first_logic_payload() -> dict:
	"""Build an official /predict UnifiedRequest payload from the first logic record."""
	with LOGIC_DATA_PATH.open("r", encoding="utf-8") as handle:
		records = json.load(handle)

	first_record = records[0]
	return {
		"query_id": "T1_1",
		"type": "type1",
		"query": first_record["questions"][0],
		"premises": first_record["premises-NL"],
		"options": [],
	}


def test_health_endpoint_returns_ok():
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_predict_rejects_missing_required_fields():
	# query_id / type / query are mandatory in UnifiedRequest → 422 on omission.
	response = client.post("/predict", json={"premises": []})

	assert response.status_code == 422


def test_unified_request_accepts_valid_payload():
	payload = load_first_logic_payload()

	request = UnifiedRequest(**payload)

	assert request.query_id == "T1_1"
	assert request.type == "type1"
	assert request.query == payload["query"]
	assert request.premises == payload["premises"]


def test_predict_returns_list_for_type1():
	payload = load_first_logic_payload()

	response = client.post("/predict", json=payload)

	assert response.status_code == 200
	body = response.json()
	# Official schema: response is a LIST, one object per query, query_id echoed.
	assert isinstance(body, list) and len(body) == 1
	item = body[0]
	assert item["query_id"] == "T1_1"
	assert isinstance(item["answer"], str) and item["answer"]
	assert isinstance(item["explanation"], str) and item["explanation"]


def test_predict_type2_returns_ascii_unit():
	payload = {
		"query_id": "T2_1",
		"type": "type2",
		"query": "Two resistors R1 = 4 ohm and R2 = 6 ohm in parallel across U = 12 V. Find the total current.",
		"premises": [],
		"options": [],
	}

	response = client.post("/predict", json=payload)

	assert response.status_code == 200
	body = response.json()
	assert isinstance(body, list) and len(body) == 1
	item = body[0]
	assert item["query_id"] == "T2_1"
	assert isinstance(item["answer"], str)
	# Unit field must be ASCII per Submission Guide §4 (no Ω / μ glyphs).
	assert "Ω" not in item["unit"] and "μ" not in item["unit"]
