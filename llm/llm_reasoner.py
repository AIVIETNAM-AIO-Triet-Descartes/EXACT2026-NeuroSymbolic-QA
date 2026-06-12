"""
LLM Reasoner - Wrapper cho Qwen 2.5 7B Instruct via llama-cpp-python.

Cung cấp các chức năng:
    1. generate_explanation: Sinh giải thích NL khi đã biết đáp án (post-Z3)
    2. solve_with_cot: Giải bài toán bằng Chain-of-Thought (fallback)
    3. generate_z3_code: Sinh Z3 Python code từ FOL (LLM-assisted translation)

References:
    - Logic-LM Self-Refinement: Pan et al., ACL 2023
    - Chain-of-Thought Prompting: Wei et al., NeurIPS 2022
"""

import re
import os
import json
from typing import Optional, Dict, List
from loguru import logger

from llm.prompt_templates import (
    SYSTEM_PROMPT_LOGIC,
    SYSTEM_PROMPT_Z3,
    EXPLANATION_PROMPT,
    COT_MCQ_PROMPT,
    COT_YESNO_PROMPT,
    Z3_CODE_GENERATION_PROMPT,
    Z3_REFINEMENT_PROMPT,
    ANSWER_EXTRACT_PATTERNS,
    SYSTEM_PROMPT_PHYSICS,
    PHYSICS_PARSE_PROMPT,
    PHYSICS_COT_PROMPT,
    PHYSICS_PAL_PROMPT,
    PHYSICS_PAL_REFINE_PROMPT,
    PHYSICS_EXPLAIN_PROMPT,
)


class LLMReasoner:
    """
    LLM Reasoning Engine — talks to an OpenAI-compatible server (vLLM in prod,
    llama.cpp in dev) over HTTP via the `openai` client. Does NOT load weights
    in-process: `model_name` must match the server's real /v1/models id, which
    the competition committee can inspect to verify the ≤8B open model.

    Switching backend is config-only (`llm.active` in configs/config.yaml) —
    build instances through `from llm import get_shared_reasoner`.

    Attributes:
        api_base:   OpenAI-compatible base URL (e.g. http://localhost:8001/v1).
        model_name: Served model id (must match GET /v1/models).
        temperature / max_tokens: default sampling params.
    """

    def __init__(
        self,
        api_base: str = "http://localhost:8000/v1",
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        api_key: str = "not-needed",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **_legacy,   # tolerate/ignore old llama.cpp kwargs (model_path, n_ctx, ...)
    ):
        self.api_base = api_base
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None  # lazy-init OpenAI client

    def _get_client(self):
        """Lazy-init the OpenAI client pointed at the local inference server."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.api_base, api_key=self.api_key)
        return self._client

    def check_server(self) -> bool:
        """Return True if the inference server answers GET /v1/models."""
        try:
            self._get_client().models.list()
            return True
        except Exception as e:
            logger.warning(f"LLM server not reachable at {self.api_base}: {e}")
            return False

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gửi chat completion request đến inference server (OpenAI-compatible).

        Returns "" khi lỗi / không kết nối được (KHÔNG raise — caller tự fallback).
        """
        temp = self.temperature if temperature is None else temperature

        try:
            resp = self._get_client().chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=max_tokens,
            )
            return (resp.choices[0].message.content or "").strip()

        except Exception as e:
            logger.error(f"LLM chat completion failed: {e}")
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

        # Detect DeepSeek-R1 models to optimize generation parameters (higher temperature and max_tokens)
        is_deepseek = "deepseek" in self.model_name.lower()
        max_toks = 2048 if is_deepseek else 1024
        temp = 0.6 if is_deepseek else 0.1

        response = self._chat(
            system_prompt=SYSTEM_PROMPT_LOGIC,
            user_prompt=prompt,
            max_tokens=max_toks,
            temperature=temp,
        )

        # Clean reasoning thinking blocks if present (DeepSeek-R1 style)
        cleaned_response = response
        if "</think>" in response:
            cleaned_response = response.split("</think>", 1)[1].strip()

        # Extract answer from response
        logger.debug(f"[LLM_COT] Raw Response:\n{response}\n")
        answer = self._extract_answer(cleaned_response)
        if not answer:
            logger.warning("[LLM_COT] Failed to extract answer from raw response. Returning None.")

        return {
            'answer': answer,
            'explanation': response,
            'method': 'llm_cot',
            'premises_used': self._extract_premises_used(cleaned_response),
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
    # Private Helpers
    # ══════════════════════════════════════════════════════════

    def _extract_premises_used(self, response: str) -> List[int]:
        """
        Trích xuất danh sách index premises 0-based từ phản hồi của LLM CoT.
        Ví dụ: "PREMISES USED: [0, 2]" -> [0, 2]
        """
        if not response:
            return []

        match = re.search(r'(?i)PREMISES\s*USED:\s*\[(.*?)\]', response)
        if not match:
            return []

        indices_str = match.group(1).strip()
        if not indices_str:
            return []

        try:
            # Tách bằng dấu phẩy, khoảng trắng hoặc chấm phẩy và lọc các chữ số
            indices = [
                int(x.strip())
                for x in re.split(r'[,;\s]+', indices_str)
                if x.strip().isdigit()
            ]
            return indices
        except Exception as e:
            logger.warning(f"Failed to parse premises_used from string '{indices_str}': {e}")
            return []

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
                        'Const', 'Function', 'BoolSort', 'IntSort', 'RealSort', 'ForAll', 'Exists', 'Implies', 
                        'And', 'Or', 'Not', 'unsat', 'sat', 'print', 'if', 'else', 
                        'push', 'pop', 'check', 'results', 'append', 'entailed', 'for', 'in',
                        'True', 'False', 'None', 'solve_yes_no', 'solve_mcq',
                        'x', 'y', 'z', 'a', 'b', 'c', 'd'}
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

    # ══════════════════════════════════════════════════════════
    # Track 2 — Physics (parse / CoT-solve / explain)
    # ══════════════════════════════════════════════════════════

    def parse_physics_question(self, question: str) -> Dict:
        """
        Extract {given, find, domain, formulas} from a physics question.

        LLM output parsed with json.loads (NEVER eval). Returns {} on failure so
        the regex pre-pass keeps its deterministic result (the caller merges with
        regex winning). Used by physics_parser_node / demo augment.
        """
        prompt = PHYSICS_PARSE_PROMPT.format(question=question)
        raw = self._chat(SYSTEM_PROMPT_PHYSICS, prompt, max_tokens=512)
        data = self._extract_json(raw)
        if not isinstance(data, dict):
            return {}
        data.setdefault("given", {})
        data.setdefault("find", "")
        data.setdefault("domain", "")
        data.setdefault("formulas", [])
        return data

    def solve_physics_cot(
        self,
        question: str,
        given: Optional[Dict] = None,
        find: str = "",
        formulas: Optional[List] = None,
    ) -> Dict:
        """
        Numeric Chain-of-Thought fallback when SymPy/vector solvers fail.

        Returns a dict shaped like sympy_result: {answer, unit, steps, source}.
        Parses the final 'ANSWER: <number> <unit>' line. source='llm_cot' so the
        caller assigns the lower fallback confidence.
        """
        prompt = PHYSICS_COT_PROMPT.format(
            question=question,
            given=given or {},
            find=find or "",
            formulas=formulas or [],
        )
        raw = self._chat(SYSTEM_PROMPT_PHYSICS, prompt, max_tokens=1024)
        answer, unit = self._extract_physics_answer(raw)
        return {
            "answer": answer,
            "unit": unit,
            "steps": [raw] if raw else [],
            "source": "llm_cot",
        }

    def generate_sympy_code(
        self,
        question: str,
        given: Optional[Dict] = None,
        find: str = "",
        formulas: Optional[List] = None,
    ) -> str:
        """
        PAL (Program-Aided) fallback: ask the LLM to WRITE Python (sympy/math) that
        computes the answer, instead of doing the arithmetic itself. Returns the raw
        code string (code fences stripped) — the CALLER runs it in a sandbox
        (`pipeline.type2.sympy_solver.execute_generated_code`). "" on failure.

        Rationale (docs/docs_vytriet/proposals.md §2): 8B models choose formulas and
        substitute well but mis-compute floats / scientific notation. Letting the
        machine execute the code removes arithmetic hallucination.
        """
        prompt = PHYSICS_PAL_PROMPT.format(
            question=question,
            given=given or {},
            find=find or "",
            formulas=formulas or [],
        )
        raw = self._chat(SYSTEM_PROMPT_PHYSICS, prompt, max_tokens=512)
        return self._strip_code_fences(raw)

    def refine_sympy_code(
        self,
        code: str,
        error: str,
        question: str,
        given: Optional[Dict] = None,
        find: str = "",
    ) -> str:
        """Self-repair: feed the failed PAL code + its error back to the LLM for one
        fix attempt. Returns the corrected code string ("" on failure). Mirrors the
        Track-1 `refine_z3_code` loop."""
        prompt = PHYSICS_PAL_REFINE_PROMPT.format(
            error=(error or "no `answer` produced")[:300],
            code=code,
            question=question,
            given=given or {},
            find=find or "",
        )
        raw = self._chat(SYSTEM_PROMPT_PHYSICS, prompt, max_tokens=512)
        return self._strip_code_fences(raw)

    @staticmethod
    def _strip_code_fences(raw: str) -> str:
        """Extract code from a ```python ...``` block, else return raw stripped."""
        if not raw:
            return ""
        m = re.search(r'```(?:python)?\s*(.*?)```', raw, re.DOTALL)
        return (m.group(1) if m else raw).strip()

    def explain_physics(
        self,
        question: str,
        answer: str,
        unit: str = "",
        steps: Optional[List[str]] = None,
    ) -> str:
        """Generate a short NL explanation for an already-solved physics problem."""
        steps_text = "\n".join(f"  - {s}" for s in (steps or []))
        prompt = PHYSICS_EXPLAIN_PROMPT.format(
            question=question, answer=answer, unit=unit or "", steps=steps_text,
        )
        text = self._chat(SYSTEM_PROMPT_PHYSICS, prompt, max_tokens=256)
        return text or (f"The answer is {answer} {unit}".strip() + ".")

    @staticmethod
    def _extract_json(raw: str) -> Optional[dict]:
        """First JSON object in an LLM response (tolerates ```fences``` / prose)."""
        if not raw:
            return None
        text = raw.strip()
        fence = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        if not text.startswith("{"):
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                text = m.group(0)
        try:
            return json.loads(text)
        except Exception:
            return None

    @staticmethod
    def _extract_physics_answer(raw: str):
        """Parse 'ANSWER: <value> <unit>' → (answer, unit); ("","") if absent."""
        if not raw:
            return "", ""
        m = re.search(r'(?i)ANSWER:\s*(.+)', raw)
        if not m:
            return "", ""
        tail = m.group(1).strip().strip("*").strip()
        nm = re.match(r'(-?[\d.]+(?:[eE][-+]?\d+)?)\s*(.*)$', tail)
        if nm:
            return nm.group(1), nm.group(2).strip().strip(".")
        return tail, ""


# ══════════════════════════════════════════════════════════════
# Factory Function
# ══════════════════════════════════════════════════════════════

def create_reasoner(*_args, **_kwargs) -> LLMReasoner:
    """
    DEPRECATED — use `from llm import get_shared_reasoner` instead.

    Thin shim kept for backward compatibility: returns the config-driven shared
    singleton so any legacy caller still talks to the configured backend
    (vLLM/llama.cpp) rather than building a stale GGUF reasoner. All positional/
    keyword args are ignored.
    """
    from llm import get_shared_reasoner
    return get_shared_reasoner()
