from llama_cpp import Llama

# Trỏ tới file 00001 (thư viện sẽ tự tìm các phần còn lại)
model_path = "./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"

print("--- Đang nạp mô hình vào VRAM... ---")
llm = Llama(
    model_path=model_path,
    n_gpu_layers=20, # Offload 20 layers lên RTX 3050
    n_ctx=2048,
    verbose=False
)

print("--- Mô hình đã sẵn sàng! Đang thử suy luận... ---")

prompt = "Question: If A implies B, and A is true, what is B? Answer in one word."

output = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": "You are a logic assistant."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.1
)

print("\nKết quả suy luận:")
print(output)
