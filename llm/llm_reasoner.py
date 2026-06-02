"""
LLM Reasoner - Wrapper gọi Qwen 2.5 7B Instruct qua vLLM server (OpenAI-compatible API).

Thay vì load model trực tiếp (llama-cpp-python), module này gọi HTTP API đến
vLLM server đang chạy trên localhost. Điều này cho phép:
  - Committee verify model qua GET /v1/models (model_id = "Qwen/Qwen2.5-7B-Instruct")
  - Model chỉ load một lần, nhiều process dùng chung
  - Dễ switch model mà không thay code (chỉ đổi config.yaml)

Cung cấp các chức năng:
    1. generate_explanation: Sinh giải thích NL khi đã biết đáp án (post-Z3)
    2. solve_with_cot: Giải bài toán bằng Chain-of-Thought (fallback)
    3. generate_z3_code: Sinh Z3 Python code từ FOL (LLM-assisted translation)
    4. parse_physics_question: Extract biến số từ đề bài vật lý
    5. explain_physics: Sinh giải thích NL cho đáp án vật lý
    6. solve_physics_cot: Giải vật lý bằng CoT khi SymPy thất bại

References:
    - Logic-LM Self-Refinement: Pan et al., ACL 2023
    - Chain-of-Thought Prompting: Wei et al., NeurIPS 2022
"""

import re
from typing import Optional, Dict, List
from loguru import logger

from llm.prompt_templates import (
    SYSTEM_PROMPT_LOGIC,
    SYSTEM_PROMPT_Z3,
    SYSTEM_PROMPT_PHYSICS,
    EXPLANATION_PROMPT,
    COT_MCQ_PROMPT,
    COT_YESNO_PROMPT,
    Z3_CODE_GENERATION_PROMPT,
    Z3_REFINEMENT_PROMPT,
    PHYSICS_PARSE_PROMPT,
    PHYSICS_PARSE_SIMPLE_PROMPT,
    PHYSICS_EXPLANATION_PROMPT,
    PHYSICS_COT_PROMPT,
    ANSWER_EXTRACT_PATTERNS,
)


class LLMReasoner:
    """
    LLM Reasoning Engine — gọi Qwen 2.5 7B Instruct qua vLLM OpenAI-compatible API.

    Architecture:
        - Không load model trực tiếp; gọi HTTP đến vLLM server đang chạy riêng
        - vLLM serve Qwen/Qwen2.5-7B-Instruct --port 8000
        - openai.OpenAI(base_url="http://localhost:8000/v1") làm transport layer
        - Low temperature (0.1) cho output deterministic

    Attributes:
        base_url: URL của vLLM server (mặc định "http://localhost:8000/v1").
        model_name: Model ID khớp với --served-model-name trên vLLM server.
        temperature: Nhiệt độ sampling mặc định.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        api_key: str = "not-needed",
        temperature: float = 0.1,
    ):
        """
        Khởi tạo LLMReasoner với vLLM server endpoint.

        Args:
            base_url: URL base của vLLM OpenAI-compatible server.
            model_name: Tên model (phải khớp với model đang serve).
            api_key: API key (vLLM không yêu cầu, để "not-needed").
            temperature: Nhiệt độ sampling mặc định cho _chat().
        """
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature

        # OpenAI client — lazy init lần đầu khi _chat() được gọi
        self._client = None

    def _get_client(self):
        """
        Trả về OpenAI client, tạo mới nếu chưa có.
        Client kết nối đến vLLM server tại self.base_url.

        Fix A (2026-06-02): Đặt max_retries=0 và timeout rõ ràng để tránh
        block ~26s/câu khi vLLM server DOWN (openai default = 2 retries × ~13s).
          - connect_timeout=3s : fail-fast nếu port không mở
          - read_timeout=60s   : cho phép generation dài (large model)
          - max_retries=0      : không retry — physics_parser sẽ catch Exception
                                 và chạy regex-only thay thế
        """
        if self._client is None:
            try:
                from openai import OpenAI
                import httpx
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Run: pip install openai"
                )
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                max_retries=0,
                timeout=httpx.Timeout(
                    timeout=60.0,    # tổng timeout (generation)
                    connect=3.0,     # connection timeout: fail-fast khi server DOWN
                ),
            )
        return self._client

    def check_server(self) -> bool:
        """
        Kiểm tra vLLM server có reachable không bằng cách query GET /v1/models.
        Gọi từ demo_type2.py trước khi bắt đầu pipeline để fail-fast.

        Returns:
            True nếu server OK.
        Raises:
            ConnectionError nếu server không reachable hoặc model không đúng.
        """
        try:
            client = self._get_client()
            models = client.models.list()
            model_ids = [m.id for m in models.data]
            logger.info(f"[LLM_SERVER] Connected. Models: {model_ids}")
            if self.model_name not in model_ids:
                logger.warning(
                    f"[LLM_SERVER] model_name='{self.model_name}' "
                    f"not in server models {model_ids}. "
                    f"Check config.yaml llm.model_name."
                )
            return True
        except Exception as e:
            raise ConnectionError(
                f"vLLM server not reachable at '{self.base_url}': {e}\n"
                f"Start server with: vllm serve {self.model_name} --port 8000"
            )

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gửi chat completion request đến vLLM server qua OpenAI API.

        Args:
            system_prompt: System message định hướng hành vi LLM.
            user_prompt: User message chứa bài toán / câu hỏi.
            max_tokens: Giới hạn số token output.
            temperature: Override nhiệt độ (None = dùng self.temperature).

        Returns:
            Generated text string, hoặc "" nếu request thất bại.
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[LLM_CHAT] vLLM API call failed: {e}")
            return ""

    # ══════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════

    def generate_explanation(
        self,
        premises_nl: List[str],
        question: str,
        answer: str,
        premises_used: List[int],
    ) -> str:
        """
        Sinh giải thích NL cho đáp án đã verified bởi Z3.

        Đây là Phase 1 (post-Z3): LLM chỉ đóng vai "dịch giả",
        không cần suy luận logic vì đáp án đã chính xác.

        Args:
            premises_nl: Danh sách premises dạng NL.
            question: Câu hỏi gốc.
            answer: Đáp án đã verified.
            premises_used: Danh sách index premises đã dùng (1-based).

        Returns:
            Explanation text.
        """
        # Format premises with numbers
        premises_text = "\n".join(
            f"  Premise {i+1}: {p}" for i, p in enumerate(premises_nl)
        )

        # Format used premises
        used_text = ", ".join(f"Premise {idx}" for idx in premises_used) \
                    if premises_used else "all premises"

        prompt = EXPLANATION_PROMPT.format(
            premises_nl=premises_text,
            question=question,
            answer=answer,
            premises_used=used_text,
        )

        explanation = self._chat(
            system_prompt=SYSTEM_PROMPT_LOGIC,
            user_prompt=prompt,
            max_tokens=256,
        )

        return explanation if explanation else (
            f"Based on the given premises, the answer is {answer}."
        )

    def solve_with_cot(
        self,
        premises_nl: List[str],
        premises_fol: List[str],
        question: str,
        question_type: str = "mcq",
        derived_facts: Optional[List[str]] = None,
    ) -> Dict:
        """
        Giải bài toán bằng Chain-of-Thought (fallback khi Z3 fail).

        Args:
            premises_nl: Danh sách premises NL.
            premises_fol: Danh sách premises FOL.
            question: Câu hỏi gốc.
            question_type: "mcq" hoặc "yes_no".
            derived_facts: Các sự thật đã được Logic Tree chứng minh.

        Returns:
            Dict với keys: answer, explanation, method
        """
        # Format premises
        nl_text = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(premises_nl)
        )
        fol_text = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(premises_fol)
        )

        hints_text = ""
        if derived_facts:
            facts_str = "\n".join(f"  - {f}" for f in derived_facts)
            hints_text = f"SYMBOLIC SOLVER HINTS (Guaranteed True Facts):\n{facts_str}\n"

        # Select appropriate prompt
        if question_type == "mcq":
            prompt = COT_MCQ_PROMPT.format(
                premises_nl=nl_text,
                premises_fol=fol_text,
                hints=hints_text,
                question=question,
            )
        else:
            prompt = COT_YESNO_PROMPT.format(
                premises_nl=nl_text,
                premises_fol=fol_text,
                hints=hints_text,
                question=question,
            )

        response = self._chat(
            system_prompt=SYSTEM_PROMPT_LOGIC,
            user_prompt=prompt,
            max_tokens=1024,
            temperature=0.1,
        )

        # Extract answer from response
        logger.debug(f"[LLM_COT] Raw Response:\n{response}\n")
        answer = self._extract_answer(response)
        if not answer:
            logger.warning("[LLM_COT] Failed to extract answer from raw response. Returning None.")

        return {
            'answer': answer,
            'explanation': response,
            'method': 'llm_cot',
        }

    def generate_z3_code(
        self,
        premises_fol: List[str],
        premises_nl: List[str],
        question: str,
    ) -> str:
        """
        Sinh Z3 Python code từ FOL premises (LLM-assisted translation).

        Args:
            premises_fol: Danh sách premises FOL.
            premises_nl: Danh sách premises NL.
            question: Câu hỏi cần kiểm tra.

        Returns:
            Z3 Python code string.
        """
        fol_text = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(premises_fol)
        )
        nl_text = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(premises_nl)
        )

        prompt = Z3_CODE_GENERATION_PROMPT.format(
            premises_fol=fol_text,
            premises_nl=nl_text,
            question=question,
        )

        code = self._chat(
            system_prompt=SYSTEM_PROMPT_Z3,
            user_prompt=prompt,
            max_tokens=1024,
            temperature=0.0,
        )
        logger.debug(f"[Z3_GEN] Raw Generated Code:\n{code}\n")

        # Clean up code: remove markdown fences
        code = self._clean_code(code)
        return code

    def refine_z3_code(
        self,
        previous_code: str,
        error_message: str,
        premises_fol: List[str],
    ) -> str:
        """
        Self-refinement: sửa Z3 code bị lỗi (Logic-LM style).

        Args:
            previous_code: Code Z3 trước đó bị lỗi.
            error_message: Thông báo lỗi từ Z3 execution.
            premises_fol: FOL premises gốc.

        Returns:
            Corrected Z3 Python code string.
        """
        fol_text = "\n".join(
            f"  {i+1}. {p}" for i, p in enumerate(premises_fol)
        )

        prompt = Z3_REFINEMENT_PROMPT.format(
            previous_code=previous_code,
            error_message=error_message,
            premises_fol=fol_text,
        )

        code = self._chat(
            system_prompt=SYSTEM_PROMPT_Z3,
            user_prompt=prompt,
            max_tokens=1024,
            temperature=0.0,
        )
        logger.debug(f"[Z3_REFINE] Refined Generated Code:\n{code}\n")

        return self._clean_code(code)

    # ══════════════════════════════════════════════════════════
    # Track 2 — Physics
    # ══════════════════════════════════════════════════════════

    def parse_physics_question(self, question: str) -> dict:
        """
        Extract structured physics data from NL question text.

        Called by PhysicsParser node (step 3b). Returns parsed_physics dict
        for downstream nodes (FormulaRAG, SympySolver).

        Args:
            question: Raw physics question string.

        Returns:
            Dict with keys: given, find, domain, formulas, units.
            On total failure returns safe empty fallback dict.
        """
        import json

        prompt = PHYSICS_PARSE_PROMPT.format(question=question)
        raw = self._chat(
            system_prompt=SYSTEM_PROMPT_PHYSICS,
            user_prompt=prompt,
            max_tokens=512,
            temperature=0.0,
        )

        result = self._extract_json(raw)
        if result:
            result.setdefault("given", {})
            result.setdefault("find", "")
            result.setdefault("domain", "circuits")
            result.setdefault("formulas", [])
            result.setdefault("units", {})
            return result

        # Retry with simplified prompt
        logger.warning("[PHYSICS_PARSE] JSON parse failed, retrying simplified prompt")
        raw2 = self._chat(
            system_prompt=SYSTEM_PROMPT_PHYSICS,
            user_prompt=PHYSICS_PARSE_SIMPLE_PROMPT.format(question=question),
            max_tokens=128,
            temperature=0.0,
        )
        result2 = self._extract_json(raw2)
        if result2:
            result2.setdefault("given", {})
            result2.setdefault("find", "")
            result2.setdefault("domain", "circuits")
            result2.setdefault("formulas", [])
            result2.setdefault("units", {})
            return result2

        logger.error("[PHYSICS_PARSE] Both attempts failed, returning empty fallback")
        return {"given": {}, "find": "", "domain": "general", "formulas": [], "units": {}}

    def explain_physics(
        self,
        question: str,
        answer: str,
        unit: str,
        steps: list,
    ) -> str:
        """
        Generate NL explanation for a physics solution.

        Called by ExplainerAgent node (step 7) for Track 2.
        Different from generate_explanation() — focuses on physical meaning
        and formula application, not logical proof chains.

        Args:
            question: Original physics question.
            answer: Numerical answer string.
            unit: Physical unit string (e.g. "Ω", "mJ").
            steps: List of solution step strings from SympySolver.

        Returns:
            Explanation text. Never empty — has hardcoded fallback.
        """
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        prompt = PHYSICS_EXPLANATION_PROMPT.format(
            question=question,
            answer=answer,
            unit=unit,
            steps=steps_text,
        )

        explanation = self._chat(
            system_prompt=SYSTEM_PROMPT_PHYSICS,
            user_prompt=prompt,
            max_tokens=256,
            temperature=0.1,
        )

        if explanation:
            return explanation

        # Retry simplified
        logger.warning("[PHYSICS_EXPLAIN] First attempt failed, retrying")
        retry_prompt = (
            f"Explain in 2 sentences why the answer to '{question}' is {answer} {unit}."
        )
        explanation2 = self._chat(
            system_prompt=SYSTEM_PROMPT_PHYSICS,
            user_prompt=retry_prompt,
            max_tokens=128,
            temperature=0.1,
        )
        return explanation2 if explanation2 else f"The answer is {answer} {unit}."

    def solve_physics_cot(
        self,
        question: str,
        given: dict,
        find: str,
        formulas: Optional[List[str]] = None,
    ) -> dict:
        """
        Giải bài toán vật lý bằng Chain-of-Thought khi SymPy thất bại.

        Gửi prompt CoT đến LLM, parse kết quả số/Yes-No/text từ phần
        "ANSWER: ..." cuối response. Trả về dict tương thích sympy_result.

        Args:
            question: Đề bài gốc.
            given: Dict {symbol: SI_value} đã extract được.
            find: Ký hiệu cần tìm (ví dụ "F", "E_field", "W").
            formulas: Gợi ý công thức từ FormulaRAG (có thể None).

        Returns:
            Dict với keys: answer (str), unit (str), steps (list), source (str).
            source="llm_cot" khi parse thành công, "llm_fallback" khi thất bại.
        """
        # Định dạng given để hiển thị trong prompt
        given_str = (
            ", ".join(f"{k}={v:.4g}" for k, v in given.items())
            if given else "(none extracted)"
        )
        find_str = find if find else "(unknown)"

        # Thêm gợi ý công thức nếu FormulaRAG tìm được
        formula_hint = ""
        if formulas:
            formula_hint = f"Relevant formula hint: {formulas[0]}"

        prompt = PHYSICS_COT_PROMPT.format(
            question=question,
            given_str=given_str,
            find_str=find_str,
            formula_hint=formula_hint,
        )

        raw = self._chat(
            system_prompt=SYSTEM_PROMPT_PHYSICS,
            user_prompt=prompt,
            max_tokens=600,
            temperature=0.1,
        )

        if not raw:
            logger.warning("[PHYSICS_COT] LLM trả về empty response")
            return {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

        steps = [line.strip() for line in raw.split("\n") if line.strip()]

        # Ưu tiên 1: parse số từ "ANSWER: <float> <unit>"
        num_pat = re.compile(
            r'ANSWER:\s*([+-]?[\d.]+(?:[eE][+-]?\d+)?'
            r'(?:\s*[×x\*]\s*10\^?[+-]?\d+)?)\s*([^\n]*)',
            re.IGNORECASE,
        )
        m = num_pat.search(raw)
        if m:
            raw_num = m.group(1).strip()
            unit_str = m.group(2).strip().split()[0] if m.group(2).strip() else ""
            # Chuẩn hóa ký hiệu nhân thành Python float: "4.5 × 10^-2" → 4.5e-2
            norm = re.sub(r'\s*[×x\*]\s*10\^?([+-]?\d+)', r'e\1', raw_num)
            try:
                answer_val = float(norm)
                return {
                    "answer": f"{answer_val:.6g}",
                    "unit": unit_str,
                    "steps": steps,
                    "source": "llm_cot",
                }
            except ValueError:
                pass  # không parse được số → thử Yes/No

        # Ưu tiên 2: parse Yes/No từ "ANSWER: Yes/No"
        yesno_pat = re.compile(r'ANSWER:\s*(Yes|No)\b', re.IGNORECASE)
        m2 = yesno_pat.search(raw)
        if m2:
            return {
                "answer": m2.group(1).capitalize(),
                "unit": "",
                "steps": steps,
                "source": "llm_cot",
            }

        # Ưu tiên 3: bất kỳ text sau "ANSWER:" (qualitative answer)
        text_pat = re.compile(r'ANSWER:\s*(.+)', re.IGNORECASE)
        m3 = text_pat.search(raw)
        if m3:
            return {
                "answer": m3.group(1).strip()[:120],
                "unit": "",
                "steps": steps,
                "source": "llm_cot",
            }

        logger.warning("[PHYSICS_COT] Không tìm thấy 'ANSWER:' trong LLM response")
        return {"answer": "", "unit": "", "steps": steps, "source": "llm_fallback"}

    # ══════════════════════════════════════════════════════════
    # Private Helpers
    # ══════════════════════════════════════════════════════════

    def _extract_json(self, response: str) -> Optional[dict]:
        """Extract JSON dict from LLM response. Handles markdown fences."""
        import json
        if not response:
            return None
        # Strip ```json ... ``` or ``` ... ```
        clean = re.sub(r'```(?:json)?\s*', '', response)
        clean = re.sub(r'```', '', clean).strip()
        # Find first { ... } block
        start = clean.find('{')
        end = clean.rfind('}')
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(clean[start:end + 1])
        except json.JSONDecodeError as e:
            logger.debug(f"[JSON_EXTRACT] Failed: {e}")
            return None

    def _extract_answer(self, response: str) -> Optional[str]:
        """
        Trích xuất đáp án từ LLM response.

        Thử nhiều pattern khác nhau để robust extraction.
        """
        if not response:
            return None

        for pattern in ANSWER_EXTRACT_PATTERNS:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).strip()
                # Normalize
                if answer in ('A', 'B', 'C', 'D'):
                    return answer
                if answer.lower() in ('yes', 'no', 'unknown'):
                    return answer.capitalize()

        # Last resort: check last line
        lines = response.strip().split('\n')
        last_line = lines[-1].strip()
        for ch in ('A', 'B', 'C', 'D'):
            if last_line == ch or last_line.startswith(f"{ch}.") or \
               last_line.startswith(f"{ch})"):
                return ch
        for word in ('Yes', 'No', 'Unknown'):
            if last_line.lower().startswith(word.lower()):
                return word

        return None

    def _clean_code(self, code: str) -> str:
        """Remove markdown fences, clean up, and auto-fix common LLM hallucinations."""
        # 1. Remove ```python ... ``` blocks
        code = re.sub(r'```python\s*\n?', '', code)
        code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
        code = code.strip()

        # Ensure it starts with from z3 import
        if not code.startswith('from z3'):
            code = "from z3 import *\n" + code

        # 2. Normalize inverted entailment checks
        code = re.sub(
            r'print\s*\(\s*"No"\s+if\s+s\.check\(\)\s*==\s*unsat\s+else\s+"Yes"\s*\)',
            'print("Yes" if s.check() == unsat else "No")',
            code
        )
        code = re.sub(
            r'print\s*\(\s*"Yes"\s+if\s+s\.check\(\)\s*==\s*sat\s+else\s+"No"\s*\)',
            'print("Yes" if s.check() == unsat else "No")',
            code
        )

        # 3. Auto-fix A -> B (and A >> B) to Implies(A, B)
        code = code.replace('>>', '->')
        while '->' in code:
            idx = code.find('->')
            
            # Find LHS
            left_end = idx - 1
            while left_end > 0 and code[left_end].isspace():
                left_end -= 1
            
            parens = 0
            left_start = left_end
            while left_start >= 0:
                char = code[left_start]
                if char == ')':
                    parens += 1
                elif char == '(':
                    parens -= 1
                    if parens < 0:
                        left_start += 1
                        break
                elif parens == 0 and char in (',', '[', ']', '\n'):
                    left_start += 1
                    break
                left_start -= 1
            if left_start < 0: left_start = 0
            while left_start < len(code) and code[left_start].isspace():
                left_start += 1
                
            lhs = code[left_start:left_end+1]
            
            # Find RHS
            right_start = idx + 2
            while right_start < len(code) and code[right_start].isspace():
                right_start += 1
                
            parens = 0
            right_end = right_start
            while right_end < len(code):
                char = code[right_end]
                if char == '(':
                    parens += 1
                elif char == ')':
                    parens -= 1
                    if parens < 0:
                        right_end -= 1
                        break
                elif parens == 0 and char in (',', '\n'):
                    right_end -= 1
                    break
                right_end += 1
            if right_end >= len(code):
                right_end = len(code) - 1
                
            rhs = code[right_start:right_end+1]
            
            new_expr = f"Implies({lhs.strip()}, {rhs.strip()})"
            code = code[:left_start] + new_expr + code[right_end+1:]

        # Auto-fix Implies(d, BA) to d == BA (equality check hallucination)
        code = re.sub(r'Implies\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)', r'\1 == \2', code)

        # 4. Auto-declare missing variables and fix strings in predicates
        ignore_words = {'from', 'z3', 'import', 's', 'Solver', 'Entity', 'DeclareSort', 
                        'Const', 'Function', 'BoolSort', 'ForAll', 'Exists', 'Implies', 
                        'And', 'Or', 'Not', 'unsat', 'sat', 'print', 'if', 'else', 
                        'push', 'pop', 'check', 'results', 'append', 'entailed', 'for', 'in',
                        'True', 'False', 'x', 'y', 'z', 'a', 'b', 'c', 'd'}
        ignore_strings = {'Yes', 'No', 'A', 'B', 'C', 'D', 'Entity'}
        
        defined_vars = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*=', code))
        missing_funcs = set()
        missing_consts = set()

        def replace_strings_in_args(match):
            func_name = match.group(1)
            args_str = match.group(2)
            if func_name in ('Const', 'Function', 'DeclareSort', 'print', 'append'):
                return match.group(0)
            
            def string_replacer(s_match):
                lit = s_match.group(1)
                if lit in ignore_strings:
                    return s_match.group(0)
                missing_consts.add(lit)
                return lit
            
            new_args = re.sub(r"['\"]([A-Za-z0-9_]+)['\"]", string_replacer, args_str)
            return f"{func_name}({new_args})"
            
        code = re.sub(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)', replace_strings_in_args, code)

        for match in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\b(\s*\()?', code):
            word = match.group(1)
            is_func_call = bool(match.group(2))
            if word in ignore_words or word in defined_vars:
                continue
            if is_func_call:
                missing_funcs.add(word)
            elif word[0].isupper() or word in missing_consts:
                missing_consts.add(word)

        injections = []
        for f in missing_funcs:
            injections.append(f"{f} = Function('{f}', Entity, BoolSort())")
        for c in missing_consts:
            if c not in defined_vars:
                injections.append(f"{c} = Const('{c}', Entity)")
            
        if injections:
            if "Entity = DeclareSort('Entity')" in code:
                code = code.replace("Entity = DeclareSort('Entity')", "Entity = DeclareSort('Entity')\n" + "\n".join(injections))
            else:
                code = "Entity = DeclareSort('Entity')\n" + "\n".join(injections) + "\n" + code

        # 5. Fix unbalanced parentheses per statement (e.g. LLM forgot closing ')')
        statements = code.split(';')
        for i, stmt in enumerate(statements):
            lines = stmt.split('\n')
            for j, line in enumerate(lines):
                if line.strip().startswith('s.add(') or line.strip().startswith('results.append('):
                    open_p = line.count('(')
                    close_p = line.count(')')
                    if open_p > close_p:
                        lines[j] = line + ')' * (open_p - close_p)
            statements[i] = '\n'.join(lines)
        code = ';'.join(statements)

        return code


# ══════════════════════════════════════════════════════════════
# Factory Function
# ══════════════════════════════════════════════════════════════

def create_reasoner(
    base_url: str = "http://localhost:8000/v1",
    model_name: str = "Qwen/Qwen2.5-7B-Instruct",
    api_key: str = "not-needed",
    temperature: float = 0.1,
    **kwargs,
) -> LLMReasoner:
    """
    Factory function tạo LLMReasoner kết nối đến vLLM server.

    Args:
        base_url: URL của vLLM OpenAI-compatible server.
        model_name: Model ID khớp với --served-model-name trên server.
        api_key: API key (vLLM không yêu cầu).
        temperature: Nhiệt độ sampling mặc định.
        **kwargs: Bổ sung, bỏ qua (backward compat với caller cũ).

    Returns:
        LLMReasoner instance (chưa kết nối — lazy, connect khi _chat() gọi).
    """
    return LLMReasoner(
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
    )
