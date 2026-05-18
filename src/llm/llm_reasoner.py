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
from typing import Optional, Dict, List
from loguru import logger

from src.llm.prompt_templates import (
    SYSTEM_PROMPT_LOGIC,
    SYSTEM_PROMPT_Z3,
    EXPLANATION_PROMPT,
    COT_MCQ_PROMPT,
    COT_YESNO_PROMPT,
    Z3_CODE_GENERATION_PROMPT,
    Z3_REFINEMENT_PROMPT,
    ANSWER_EXTRACT_PATTERNS,
)


class LLMReasoner:
    """
    LLM Reasoning Engine sử dụng Qwen 2.5 7B Instruct (GGUF).

    Architecture:
        - Model loaded via llama-cpp-python for efficient GPU inference
        - Low temperature (0.1) for deterministic logical output
        - Structured prompts enforce consistent output format

    Attributes:
        model_path: Đường dẫn đến file GGUF.
        n_ctx: Context window size.
        n_gpu_layers: Số layer offload lên GPU.
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        temperature: float = 0.1,
        verbose: bool = False,
    ):
        """
        Khởi tạo LLM Reasoner.

        Args:
            model_path: Đường dẫn file .gguf model.
            n_ctx: Kích thước context window.
            n_gpu_layers: Số layer GPU (-1 = tất cả).
            temperature: Nhiệt độ sampling.
            verbose: Hiển thị log từ llama.cpp.
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.temperature = temperature
        self.llm = None

        # Lazy loading - only load model when first needed
        self._model_loaded = False
        self._verbose = verbose

    def _ensure_model_loaded(self):
        """Lazy load model on first use."""
        if self._model_loaded:
            return

        try:
            from llama_cpp import Llama

            logger.info(f"Loading LLM model from {self.model_path}...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=self._verbose,
            )
            self._model_loaded = True
            logger.info("LLM model loaded successfully.")

        except ImportError:
            logger.error(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            raise

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gửi chat completion request đến model.

        Args:
            system_prompt: System message.
            user_prompt: User message.
            max_tokens: Giới hạn output tokens.
            temperature: Override temperature.

        Returns:
            Generated text response.
        """
        self._ensure_model_loaded()

        temp = temperature or self.temperature

        try:
            output = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=max_tokens,
                stop=["\n\n\n"],  # Prevent excessive output
            )
            return output['choices'][0]['message']['content'].strip()

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
    # Private Helpers
    # ══════════════════════════════════════════════════════════

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

        # 3. Auto-fix A -> B to Implies(A, B)
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
    model_dir: str = ".",
    model_name: str = "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
    **kwargs,
) -> LLMReasoner:
    """
    Factory function để tạo LLMReasoner với cấu hình mặc định.

    Args:
        model_dir: Thư mục chứa model file.
        model_name: Tên file GGUF.
        **kwargs: Override parameters.

    Returns:
        LLMReasoner instance.
    """
    model_path = os.path.join(model_dir, model_name)

    defaults = {
        'n_ctx': 4096,
        'n_gpu_layers': -1,
        'temperature': 0.1,
        'verbose': False,
    }
    defaults.update(kwargs)

    return LLMReasoner(model_path=model_path, **defaults)
