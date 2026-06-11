import requests

url = "http://localhost:8000/predict"
headers = {"Content-Type": "application/json"}

# Type 2
data2 = {
    "query_id": "T2_123",
    "type": "type2",
    "query": "A parallel-plate capacitor has C = 4 \mu F and is charged to 6 V. Calculate the energy.",
    "premises": [],
    "options": []
}

try:
    response = requests.post(url, json=data2)
    print("Type 2 Response:", response.status_code)
    print(response.json())
except Exception as e:
    print("Error Type 2:", e)

# Type 1
data1 = {
    "query_id": "T1_123",
    "type": "type1",
    "query": "Is it true?",
    "premises": ["Premise 1", "Premise 2"],
    "options": ["Yes", "No"]
}

try:
    response = requests.post(url, json=data1)
    print("\nType 1 Response:", response.status_code)
    print(response.json())
except Exception as e:
    print("Error Type 1:", e)
