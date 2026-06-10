import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from api.schemas import QueryRequest


client = TestClient(app)


def resolve_logic_data_path() -> Path:
	root = Path(__file__).resolve().parents[1] / "data" / "train"
	matches = sorted(root.rglob("Logic_Based_Educational_Queries.json"))
	if not matches:
		raise FileNotFoundError("Logic_Based_Educational_Queries.json not found under data/train")
	return matches[-1]


LOGIC_DATA_PATH = resolve_logic_data_path()


def load_first_logic_sample():
	with LOGIC_DATA_PATH.open("r", encoding="utf-8") as handle:
		records = json.load(handle)

	first_record = records[0]
	return {
		"question": first_record["questions"][0],
		"premises": first_record["premises-NL"],
	}


def test_health_endpoint_returns_ok():
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_query_rejects_missing_question_field():
	response = client.post("/query", json={"premises": []})

	assert response.status_code == 422


def test_query_request_model_accepts_valid_payload():
	payload = load_first_logic_sample()

	request = QueryRequest(**payload)

	assert request.question == payload["question"]
	assert request.premises == payload["premises"]


def test_query_returns_mock_response_for_valid_payload():
	payload = load_first_logic_sample()

	response = client.post("/query", json=payload)

	assert response.status_code == 200
	body = response.json()
	assert isinstance(body["answer"], str) and body["answer"]
	assert isinstance(body["explanation"], str) and body["explanation"]

