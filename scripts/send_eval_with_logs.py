import json
import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_payloads(json_path):
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    logs = data.get("logs", [])
    print(f"Loaded {len(logs)} records from {json_path}")
    
    payloads = []
    for r in logs:
        req = r.get("request_payload", {})
        payload = {
            "query_id": r.get("query_id") or req.get("query_id"),
            "type": r.get("type") or req.get("type"),
            "query": req.get("query", ""),
            "premises": req.get("premises", []),
            "options": req.get("options", []),
            "logs": True
        }
        payloads.append(payload)
        
    return payloads

def send_request(url, payload, timeout=120):
    query_id = payload["query_id"]
    qtype = payload["type"]
    print(f"[{query_id}] type={qtype} - Sending request...")
    t0 = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        res_data = resp.json()
        elapsed = time.time() - t0
        
        # If response is a list, unpack it (the endpoint returns list[UnifiedResponse])
        if isinstance(res_data, list) and len(res_data) > 0:
            result = res_data[0]
        else:
            result = res_data
            
        print(f"[{query_id}] type={qtype} - Success ({elapsed:.2f}s)")
        return {
            "query_id": query_id,
            "type": qtype,
            "success": True,
            "elapsed_seconds": elapsed,
            "response": result
        }
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{query_id}] type={qtype} - Failed ({elapsed:.2f}s): {e}")
        return {
            "query_id": query_id,
            "type": qtype,
            "success": False,
            "elapsed_seconds": elapsed,
            "error": str(e),
            "response": None
        }

def main():
    json_path = "exact_eval_round1_Cay_Nha_La_Vuon.json"
    api_url = "http://13.229.155.181:9000/predict"
    output_path = "output/eval_round1_predictions_with_logs.json"
    workers = 1  # Run sequentially to avoid overloading remote GPU
    
    print("=" * 60)
    print(f"Extracting data from: {json_path}")
    print(f"Sending requests to: {api_url}")
    print(f"Saving output to: {output_path}")
    print("=" * 60)
    
    payloads = load_payloads(json_path)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Load existing success results
    existing_results = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for item in saved:
                    if item.get("success"):
                        existing_results[item["query_id"]] = item
            print(f"Resuming: found {len(existing_results)} already successful queries in {output_path}")
        except Exception as e:
            print(f"Could not load existing file, starting fresh: {e}")
            
    results = [None] * len(payloads)
    
    # Populate existing results
    for i, p in enumerate(payloads):
        qid = p["query_id"]
        if qid in existing_results:
            results[i] = existing_results[qid]
            
    # Filter payloads to run
    payloads_to_run = {}
    for i, p in enumerate(payloads):
        if results[i] is None:
            payloads_to_run[i] = p
            
    # Sort remaining payloads: type2 first, then type1
    sorted_indices = sorted(
        payloads_to_run.keys(),
        key=lambda idx: (0 if payloads_to_run[idx]["type"] == "type2" else 1, payloads_to_run[idx]["query_id"])
    )
    
    print(f"Remaining queries to execute: {len(sorted_indices)}")
    
    if len(sorted_indices) > 0:
        print(f"\nStarting API calls using {workers} worker(s) (Type 2 first)...")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Submit in prioritized order
            future_to_idx = {}
            for idx in sorted_indices:
                p = payloads_to_run[idx]
                future = pool.submit(send_request, api_url, p)
                future_to_idx[future] = idx
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
                
                # Save progress after each call
                temp_results = [r for r in results if r is not None]
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(temp_results, f, ensure_ascii=False, indent=2)
                    
    print("\n" + "=" * 60)
    print("Execution complete!")
    success_count = sum(1 for r in results if r is not None and r.get("success"))
    print(f"Successfully processed: {success_count}/{len(results)} queries")
    print(f"Final output saved to: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
