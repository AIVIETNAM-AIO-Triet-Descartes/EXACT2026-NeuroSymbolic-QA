"""
Main Pipeline - EXACT 2026 Neuro-Symbolic QA System.

Orchestrates the full pipeline:
    Stage 1: Preprocessing (FOL Normalization + Question Classification)
    Stage 2: Logic Tree Construction (Forward/Backward Chaining)
    Stage 3: Z3 Symbolic Solver (Formal Verification)
    Stage 4: LLM Reasoning (Explanation Generation + CoT Fallback)

Architecture:
    Hybrid Neuro-Symbolic approach combining:
    - Symbolic: Z3 Theorem Prover for guaranteed logical correctness
    - Neural: Qwen 2.5 7B for NL explanation generation
    - Structural: Logic Tree (DAG) for proof trace extraction

References:
    - Logic-LM: Pan et al., ACL 2023
    - LINC: Olausson et al., EMNLP 2023
    - Tree-of-Thought: Yao et al., NeurIPS 2023

Usage:
    python -m src.main --input data.json --output results.json
    python -m src.main --input data.json --output results.json --no-llm
"""

import json
import time
import argparse
import signal
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from loguru import logger
from tqdm import tqdm

from src.preprocessor.fol_normalizer import FOLNormalizer
from src.preprocessor.question_classifier import (
    QuestionClassifier, QuestionType, detect_answer_type,
)
from src.reasoning.logic_tree import LogicTree
from src.reasoning.z3_solver import (
    Z3Translator, EntailmentChecker, execute_z3_code,
)
from src.llm.llm_reasoner import LLMReasoner, create_reasoner


# ══════════════════════════════════════════════════════════════
# Data Models
# ══════════════════════════════════════════════════════════════

@dataclass
class QuestionResult:
    """Kết quả xử lý một câu hỏi."""
    answer: str = ""
    explanation: str = ""
    premises_used: List[int] = field(default_factory=list)
    method: str = ""               # z3_verified | logic_tree | llm_cot | llm_z3
    confidence: float = 0.0
    time_ms: float = 0.0


@dataclass
class SampleResult:
    """Kết quả xử lý một sample."""
    sample_index: int = 0
    questions: List[QuestionResult] = field(default_factory=list)
    total_time_ms: float = 0.0


# ══════════════════════════════════════════════════════════════
# Pipeline Configuration
# ══════════════════════════════════════════════════════════════

@dataclass
class PipelineConfig:
    """Cấu hình pipeline."""
    input_path: str = "Logic_Based_Educational_Queries.json"
    output_path: str = "output/predictions.json"
    model_path: str = "./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
    n_gpu_layers: int = -1
    n_ctx: int = 4096
    z3_timeout_ms: int = 30000
    max_time_per_sample: int = 55  # seconds (buffer for 60s limit)
    use_llm: bool = True
    use_z3: bool = True
    use_logic_tree: bool = True
    max_samples: Optional[int] = None  # None = process all
    log_level: str = "INFO"


# ══════════════════════════════════════════════════════════════
# Timeout Handler
# ══════════════════════════════════════════════════════════════

class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Processing timed out!")


# ══════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════

class NeuroSymbolicPipeline:
    """
    Main Pipeline cho EXACT 2026 Logic-Based QA.

    Pipeline Flow:
        Input JSON → Preprocess → Logic Tree → Z3 Solver → LLM → Output JSON

    Attributes:
        config: Pipeline configuration.
        normalizer: FOL normalizer.
        classifier: Question classifier.
        z3_translator: Z3 translator.
        llm: LLM reasoner (lazy loaded).
    """

    def __init__(self, config: PipelineConfig):
        self.config = config

        # Initialize components
        self.normalizer = FOLNormalizer()
        self.classifier = QuestionClassifier()

        if config.use_z3:
            try:
                self.z3_translator = Z3Translator(
                    timeout_ms=config.z3_timeout_ms
                )
            except Exception as e:
                logger.warning(f"Z3 initialization failed: {e}")
                self.z3_translator = None
        else:
            self.z3_translator = None

        self.llm: Optional[LLMReasoner] = None

        # Statistics
        self.stats = {
            'total': 0,
            'z3_solved': 0,
            'logic_tree_solved': 0,
            'llm_solved': 0,
            'failed': 0,
            'total_time': 0.0,
        }

    def _ensure_llm(self):
        """Lazy load LLM model."""
        if self.llm is None and self.config.use_llm:
            self.llm = create_reasoner(
                model_dir=".",
                model_name=Path(self.config.model_path).name,
                n_ctx=self.config.n_ctx,
                n_gpu_layers=self.config.n_gpu_layers,
            )

    # ── Main Entry Point ─────────────────────────────────────

    def run(self, dataset: List[Dict]) -> List[SampleResult]:
        """
        Chạy pipeline trên toàn bộ dataset.

        Args:
            dataset: List of samples from JSON.

        Returns:
            List of SampleResult.
        """
        results = []
        total = len(dataset)

        if self.config.max_samples:
            dataset = dataset[:self.config.max_samples]
            total = len(dataset)

        logger.info(f"Processing {total} samples...")

        for i, sample in enumerate(tqdm(dataset, desc="Processing")):
            start_time = time.time()

            try:
                result = self.process_sample(sample, i)
            except TimeoutException:
                logger.warning(f"Sample {i} timed out")
                result = self._make_fallback_result(sample, i)
            except Exception as e:
                logger.error(f"Sample {i} failed: {e}")
                result = self._make_fallback_result(sample, i)
                self.stats['failed'] += 1

            elapsed = (time.time() - start_time) * 1000
            result.total_time_ms = elapsed
            self.stats['total_time'] += elapsed
            self.stats['total'] += 1

            results.append(result)

        self._print_stats()
        return results

    def process_sample(self, sample: Dict, index: int) -> SampleResult:
        """
        Xử lý một sample đầy đủ (tất cả câu hỏi).

        Pipeline cho mỗi sample:
            1. Normalize FOL premises
            2. Build Logic Tree
            3. Forward chain to derive all conclusions
            4. For each question:
                a. Classify question type
                b. Try Z3 solver
                c. Use Logic Tree proof trace
                d. Fallback to LLM CoT
                e. Generate explanation
        """
        premises_fol = sample.get('premises-FOL', [])
        premises_nl = sample.get('premises-NL', [])
        questions = sample.get('questions', [])
        ground_truth = sample.get('answers', [])

        result = SampleResult(sample_index=index)

        # ── Stage 1: Preprocessing ──
        norm_premises = self.normalizer.normalize_batch(premises_fol)
        metadata = self.normalizer.extract_all_metadata(norm_premises)

        # ── Stage 2: Logic Tree ──
        logic_tree = None
        if self.config.use_logic_tree:
            try:
                logic_tree = LogicTree(premises_fol)
                logic_tree.handle_negations()
                logic_tree.generate_contrapositions()
                logic_tree.forward_chain()
            except Exception as e:
                logger.debug(f"Logic Tree construction failed: {e}")

        # ── Stage 3 & 4: Process each question ──
        for q_idx, question in enumerate(questions):
            q_start = time.time()
            classified = self.classifier.classify(question)

            q_result = self._solve_question(
                classified=classified,
                premises_fol=premises_fol,
                premises_nl=premises_nl,
                logic_tree=logic_tree,
                metadata=metadata,
                q_idx=q_idx,
            )

            q_result.time_ms = (time.time() - q_start) * 1000
            result.questions.append(q_result)

        return result

    def _solve_question(
        self,
        classified,
        premises_fol: List[str],
        premises_nl: List[str],
        logic_tree: Optional[LogicTree],
        metadata: Dict,
        q_idx: int,
    ) -> QuestionResult:
        """
        Giải một câu hỏi cụ thể với chiến lược phân tầng.

        Strategy Priority:
            1. Z3 Solver (highest confidence)
            2. LLM-assisted Z3 (medium confidence)
            3. Logic Tree heuristic (medium confidence)
            4. LLM CoT (lowest confidence, always available)
        """
        q_result = QuestionResult()

        # ── Strategy 1: LLM-Assisted Z3 ──
        if self.config.use_z3 and self.config.use_llm:
            z3_result = self._try_llm_z3(
                premises_fol, premises_nl, classified
            )
            if z3_result and z3_result.get('answer'):
                q_result.answer = z3_result['answer']
                q_result.method = 'llm_z3'
                q_result.confidence = 0.9
                q_result.premises_used = z3_result.get('premises_used', [])
                # Generate explanation
                q_result.explanation = self._generate_explanation(
                    premises_nl, classified.original,
                    q_result.answer, q_result.premises_used
                )
                self.stats['z3_solved'] += 1
                return q_result

        # ── Strategy 2: Logic Tree ──
        if logic_tree:
            tree_result = self._try_logic_tree(
                logic_tree, classified, premises_fol
            )
            if tree_result and tree_result.get('answer'):
                q_result.answer = tree_result['answer']
                q_result.method = 'logic_tree'
                q_result.confidence = 0.7
                q_result.premises_used = tree_result.get('premises_used', [])
                q_result.explanation = self._generate_explanation(
                    premises_nl, classified.original,
                    q_result.answer, q_result.premises_used
                )
                self.stats['logic_tree_solved'] += 1
                return q_result

        # ── Strategy 3: LLM Chain-of-Thought (Fallback) ──
        if self.config.use_llm:
            cot_result = self._try_llm_cot(
                premises_fol, premises_nl, classified, logic_tree
            )
            if cot_result and cot_result.get('answer'):
                q_result.answer = cot_result['answer']
                q_result.explanation = cot_result.get('explanation', '')
                q_result.method = 'llm_cot'
                q_result.confidence = 0.5
                self.stats['llm_solved'] += 1
                return q_result

        # ── Fallback: Default answer ──
        q_result.answer = "Unknown"
        q_result.explanation = "Insufficient information to determine the answer."
        q_result.method = 'default'
        q_result.confidence = 0.0
        self.stats['failed'] += 1
        return q_result

    # ── Strategy Implementations ─────────────────────────────

    def _try_llm_z3(
        self, premises_fol, premises_nl, classified
    ) -> Optional[Dict]:
        """LLM generates Z3 code → execute → get answer."""
        try:
            self._ensure_llm()
            if not self.llm:
                return None

            # Generate Z3 code
            code = self.llm.generate_z3_code(
                premises_fol, premises_nl, classified.original
            )

            if not code:
                return None

            # Execute with retry
            output = execute_z3_code(code)

            if output is None:
                # Self-refinement: try once more
                code2 = self.llm.refine_z3_code(
                    code, "Execution returned no output", premises_fol
                )
                output = execute_z3_code(code2) if code2 else None

            if output:
                answer = self._parse_z3_output(output, classified)
                if answer:
                    return {'answer': answer, 'premises_used': []}

        except Exception as e:
            logger.debug(f"LLM-Z3 failed: {e}")

        return None

    def _try_logic_tree(
        self, logic_tree: LogicTree, classified, premises_fol
    ) -> Optional[Dict]:
        """Use Logic Tree for reasoning."""
        try:
            derived_preds = logic_tree.get_all_derived_predicates()

            if classified.question_type == QuestionType.YES_NO:
                # Extract target predicate from question
                keywords = classified.keywords
                # Check if any derived predicate matches keywords
                for kw in keywords:
                    for derived in derived_preds:
                        if kw.lower() in derived.lower() or \
                           derived.lower() in kw.lower():
                            proof = logic_tree.get_proof_trace(derived)
                            if proof['provable']:
                                return {
                                    'answer': 'Yes',
                                    'premises_used': proof['premises_used'],
                                }

            elif classified.question_type == QuestionType.MCQ:
                # Logic Tree operates purely on symbolic FOL predicates.
                # Since MCQ options are in Natural Language and can contain complex logic
                # (like counting premises or nested implications), a simple keyword match
                # is logically unsound and leads to wrong answers (e.g. vacuously matching "PEP 8").
                # 
                # Proper solution: Fallback to Z3 or LLM-CoT which can handle natural language reasoning.
                return None

        except Exception as e:
            logger.debug(f"Logic Tree failed: {e}")

        return None

    def _try_llm_cot(
        self, premises_fol, premises_nl, classified, logic_tree: Optional[Any] = None
    ) -> Optional[Dict]:
        """LLM direct Chain-of-Thought reasoning."""
        try:
            self._ensure_llm()
            if not self.llm:
                return None

            q_type = "mcq" if classified.question_type == QuestionType.MCQ \
                     else "yes_no"

            # Extract symbolic hints from LogicTree
            derived_facts = []
            if logic_tree:
                for fact in logic_tree.facts:
                    neg = "~" if fact.is_negated else ""
                    args = f"({', '.join(fact.arguments)})" if fact.arguments else "(x)"
                    derived_facts.append(f"{neg}{fact.predicate}{args}")
                for node in logic_tree.derived:
                    neg = "~" if node.is_negated else ""
                    args = f"({', '.join(node.arguments)})" if node.arguments else "(x)"
                    derived_facts.append(f"{neg}{node.predicate}{args}")
                # Remove duplicates
                derived_facts = list(dict.fromkeys(derived_facts))

            result = self.llm.solve_with_cot(
                premises_nl, premises_fol,
                classified.original, q_type, derived_facts
            )

            return result

        except Exception as e:
            logger.debug(f"LLM CoT failed: {e}")

        return None

    def _generate_explanation(
        self, premises_nl, question, answer, premises_used
    ) -> str:
        """Generate NL explanation via LLM."""
        try:
            self._ensure_llm()
            if self.llm:
                return self.llm.generate_explanation(
                    premises_nl, question, answer, premises_used
                )
        except Exception as e:
            logger.debug(f"Explanation generation failed: {e}")

        return f"Based on the given premises, the answer is {answer}."

    def _parse_z3_output(self, output: str, classified) -> Optional[str]:
        """Parse Z3 execution output to extract answer.
        
        Handles two formats:
        1. Direct letter output: "A" or "B" etc.
        2. Multi-line Yes/No from MCQ option checks: maps first "Yes" to corresponding letter.
        """
        raw = output.strip()
        lines = [l.strip().lower() for l in raw.split('\n') if l.strip()]
        
        logger.debug(f"[Z3_PARSE] Raw output: {repr(raw)}, classified type: {classified.question_type}")

        # ── Case 1: Direct MCQ letter answer ──
        for line in lines:
            for ch in ('a', 'b', 'c', 'd'):
                if line == ch or line.startswith(f"{ch}.") or line.startswith(f"{ch})"):
                    return ch.upper()

        # ── Case 2: MCQ with multi-line Yes/No ──
        # When Z3 code checks all 4 options and prints Yes/No for each,
        # map the first "Yes" to the corresponding option letter.
        if classified.question_type == QuestionType.MCQ and len(lines) >= 2:
            option_letters = ['A', 'B', 'C', 'D']
            for i, line in enumerate(lines):
                if i < len(option_letters) and line in ('yes', 'true'):
                    return option_letters[i]
            # If no "Yes" found among multi-line output, return None
            return None

        # ── Case 3: Yes/No question ──
        if classified.question_type != QuestionType.MCQ:
            full = raw.lower()
            if 'yes' in full:
                return 'Yes'
            if 'no' in full:
                return 'No'
            if 'unknown' in full:
                return 'Unknown'

        return None

    def _make_fallback_result(
        self, sample: Dict, index: int
    ) -> SampleResult:
        """Create a fallback result when processing fails."""
        result = SampleResult(sample_index=index)
        for q in sample.get('questions', []):
            result.questions.append(QuestionResult(
                answer="Unknown",
                explanation="Processing failed; defaulting to Unknown.",
                method="fallback",
                confidence=0.0,
            ))
        return result

    def _print_stats(self):
        """Print pipeline execution statistics."""
        s = self.stats
        total = max(s['total'], 1)
        avg_time = s['total_time'] / total

        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total samples:      {s['total']}")
        logger.info(f"Z3 solved:          {s['z3_solved']} ({100*s['z3_solved']/total:.1f}%)")
        logger.info(f"Logic Tree solved:  {s['logic_tree_solved']} ({100*s['logic_tree_solved']/total:.1f}%)")
        logger.info(f"LLM CoT solved:     {s['llm_solved']} ({100*s['llm_solved']/total:.1f}%)")
        logger.info(f"Failed/Default:     {s['failed']} ({100*s['failed']/total:.1f}%)")
        logger.info(f"Avg time/sample:    {avg_time:.0f} ms")
        logger.info("=" * 60)


# ══════════════════════════════════════════════════════════════
# Output Formatting
# ══════════════════════════════════════════════════════════════

def format_output(
    results: List[SampleResult], dataset: List[Dict]
) -> List[Dict]:
    """
    Format kết quả theo chuẩn submission EXACT 2026.

    Output format per sample:
    {
        "idx": [[premises_used_q1], [premises_used_q2]],
        "answers": ["A", "Yes"],
        "explanation": ["...", "..."]
    }
    """
    output = []

    for result, sample in zip(results, dataset):
        entry = {
            "idx": [],
            "answers": [],
            "explanation": [],
        }

        for q_result in result.questions:
            entry["answers"].append(q_result.answer or "Unknown")
            entry["explanation"].append(
                q_result.explanation or "No explanation available."
            )
            entry["idx"].append(
                q_result.premises_used if q_result.premises_used
                else list(range(1, len(sample.get('premises-FOL', [])) + 1))
            )

        output.append(entry)

    return output


def evaluate_accuracy(
    results: List[SampleResult], dataset: List[Dict]
) -> Dict:
    """
    Đánh giá accuracy so với ground truth.

    Returns:
        Dict với accuracy metrics.
    """
    total_q = 0
    correct_q = 0
    by_method = {}

    for result, sample in zip(results, dataset):
        gt_answers = sample.get('answers', [])

        for i, q_result in enumerate(result.questions):
            if i >= len(gt_answers):
                continue

            total_q += 1
            predicted = (q_result.answer or "").strip()
            expected = gt_answers[i].strip()

            method = q_result.method
            if method not in by_method:
                by_method[method] = {'total': 0, 'correct': 0}
            by_method[method]['total'] += 1

            if predicted.lower() == expected.lower():
                correct_q += 1
                by_method[method]['correct'] += 1

    overall_acc = correct_q / max(total_q, 1)

    return {
        'total_questions': total_q,
        'correct': correct_q,
        'accuracy': overall_acc,
        'by_method': {
            k: {
                **v,
                'accuracy': v['correct'] / max(v['total'], 1)
            }
            for k, v in by_method.items()
        },
    }


# ══════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="EXACT 2026 Neuro-Symbolic QA Pipeline"
    )
    parser.add_argument(
        "--input", "-i",
        default="Logic_Based_Educational_Queries.json",
        help="Path to input JSON dataset",
    )
    parser.add_argument(
        "--output", "-o",
        default="output/predictions.json",
        help="Path to output predictions JSON",
    )
    parser.add_argument(
        "--model", "-m",
        default="./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        help="Path to GGUF model file",
    )
    parser.add_argument(
        "--max-samples", "-n",
        type=int, default=None,
        help="Maximum number of samples to process",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM (use only Z3 + Logic Tree)",
    )
    parser.add_argument(
        "--no-z3",
        action="store_true",
        help="Disable Z3 solver",
    )
    parser.add_argument(
        "--gpu-layers",
        type=int, default=-1,
        help="Number of GPU layers for LLM (-1 = all)",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Evaluate accuracy against ground truth",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: tqdm.write(msg, end=""),
        level=args.log_level,
        colorize=True,
    )
    logger.add(
        "logs/pipeline_{time}.log",
        level="DEBUG",
        rotation="10 MB",
    )

    # Load dataset
    logger.info(f"Loading dataset from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    logger.info(f"Loaded {len(dataset)} samples.")

    # Create pipeline config
    config = PipelineConfig(
        input_path=args.input,
        output_path=args.output,
        model_path=args.model,
        n_gpu_layers=args.gpu_layers,
        use_llm=not args.no_llm,
        use_z3=not args.no_z3,
        max_samples=args.max_samples,
        log_level=args.log_level,
    )

    # Run pipeline
    pipeline = NeuroSymbolicPipeline(config)
    results = pipeline.run(dataset[:config.max_samples or len(dataset)])

    # Format and save output
    output_data = format_output(
        results, dataset[:config.max_samples or len(dataset)]
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Predictions saved to {output_path}")

    # Evaluate if requested
    if args.evaluate:
        eval_results = evaluate_accuracy(
            results, dataset[:config.max_samples or len(dataset)]
        )
        logger.info("\n" + "=" * 60)
        logger.info("EVALUATION RESULTS")
        logger.info("=" * 60)
        logger.info(
            f"Overall Accuracy: {eval_results['accuracy']:.4f} "
            f"({eval_results['correct']}/{eval_results['total_questions']})"
        )
        for method, stats in eval_results['by_method'].items():
            logger.info(
                f"  {method}: {stats['accuracy']:.4f} "
                f"({stats['correct']}/{stats['total']})"
            )

        # Save evaluation
        eval_path = output_path.parent / "evaluation.json"
        with open(eval_path, 'w') as f:
            json.dump(eval_results, f, indent=2)
        logger.info(f"Evaluation saved to {eval_path}")


if __name__ == "__main__":
    main()
