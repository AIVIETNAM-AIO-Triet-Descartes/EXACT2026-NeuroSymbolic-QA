# 🚀 Pipeline Implementation Guide

> **Mục tiêu:** Hướng dẫn cách ghép nối các module (Normalizer, Logic Tree, Z3, LLM) thành một pipeline chạy end-to-end, đáp ứng time limit < 60s/query.

---

## 1. Cấu Trúc Data Flow

Hệ thống sẽ chạy trên một danh sách các samples. Hàm xử lý chính sẽ nhận input là 1 sample từ `Logic_Based_Educational_Queries.json`.

```python
def process_single_sample(sample: dict, llm_reasoner: LLMReasoner) -> dict:
    """
    Xử lý 1 sample, trả về kết quả cho tất cả các câu hỏi trong sample đó.
    """
    premises_nl = sample['premises-NL']
    premises_fol = sample['premises-FOL']
    questions = sample['questions']
    
    results = []
    
    # --- STAGE 1: Preprocessing & Normalization ---
    normalizer = FOLNormalizer()
    norm_premises = [normalizer.normalize(f) for f in premises_fol]
    
    # --- STAGE 2 & 3: Symbolic Reasoning ---
    z3_translator = Z3Translator()
    
    try:
        # Build Z3 context for all premises
        ctx = z3_translator.translate_all([p.normalized for p in norm_premises])
        z3_success = True
    except Exception as e:
        z3_success = False
        print(f"Z3 translation failed: {e}")
    
    # --- STAGE 4: Process Each Question ---
    for i, question in enumerate(questions):
        q_result = {
            "question": question,
            "answer": None,
            "explanation": "",
            "used_premises": []
        }
        
        q_type = detect_question_type(question)
        
        if z3_success:
            # Try solving with Z3
            if q_type == "MCQ":
                options = extract_options(question)
                ans = solve_mcq_with_z3(ctx, options)
            else: # Yes/No/Unknown
                ans = solve_yesno_with_z3(ctx, question)
            
            if ans is not None:
                q_result['answer'] = ans
                # Generate explanation using verified answer
                expl = llm_reasoner.generate_explanation(
                    premises_nl, premises_fol, question, ans
                )
                q_result['explanation'] = expl
                
                # Bonus: Logic Tree to extract used_premises (idx)
                tree_facts, tree_rules = parse_premises(premises_fol)
                graph = build_graph(tree_facts, tree_rules)
                derived = forward_chaining(graph, tree_facts)
                q_result['used_premises'] = extract_premises_used_by_tree(...)
                
                results.append(q_result)
                continue
                
        # --- FALLBACK: If Z3 failed or returned None ---
        # Run LLM CoT fallback
        fallback_res = llm_reasoner.solve_with_cot(premises_nl, question)
        q_result['answer'] = fallback_res['answer']
        q_result['explanation'] = "[LLM Fallback] " + fallback_res['explanation']
        results.append(q_result)
        
    return results
```

## 2. Multi-threading / Async Execution

Để đảm bảo chạy qua 411 samples nhanh chóng, cần dùng parallel processing (cẩn thận GPU VRAM lock với LLM).

```python
import concurrent.futures
from tqdm import tqdm

def run_pipeline_batch(dataset: list, num_workers: int = 4):
    # Khởi tạo LLM model 1 lần (dùng chung cho các worker nếu framework hỗ trợ, 
    # hoặc spawn logic thuần chạy song song, LLM query chạy tuần tự)
    
    # Architecture tối ưu: Z3/Logic Tree chạy threadpool, LLM requests đẩy vào queue.
    llm_reasoner = LLMReasoner(...)
    
    results = []
    
    # Vì Llama-cpp-python không thread-safe khi gọi create_completion, 
    # ta nên chạy vòng lặp tuần tự hoặc dùng server-client (FastAPI).
    
    for sample in tqdm(dataset, desc="Processing samples"):
        res = process_single_sample(sample, llm_reasoner)
        results.append(res)
        
    return results
```

## 3. Xử Lý Lỗi Và Timeout

```python
import signal
from contextlib import contextmanager

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Trong pipeline:
try:
    with time_limit(30): # Giới hạn Z3 chạy 30s
        solve_with_z3(...)
except TimeoutException:
    print("Z3 timeout, switching to LLM fallback.")
    fallback_to_llm(...)
```

## 4. Format Output Cuối Cùng

Output cần đúng chuẩn của bài toán (JSON):

```json
[
  {
    "idx": [[1], [7, 10]],
    "answers": ["A", "Yes"],
    "explanation": [
      "Premise 1 states that if a Python project is well-tested, it is optimized...",
      "Premise 10 confirms all Python projects are well-structured..."
    ]
  },
  ...
]
```
