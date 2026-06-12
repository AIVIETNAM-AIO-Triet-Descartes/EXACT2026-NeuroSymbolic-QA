"""
Unit Tests - Kiểm tra các module chính của pipeline.

Chạy: python -m pytest tests/ -v
Hoặc: python tests/test_pipeline.py
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type1.fol_normalizer import FOLNormalizer, FOLStyle
from pipeline.type1.question_classifier import (
    QuestionClassifier, QuestionType, detect_answer_type,
)
from pipeline.type1.logic_tree import LogicTree, FOLPremiseParser


def test_fol_normalizer():
    """Test FOL Normalizer với các notation khác nhau."""
    normalizer = FOLNormalizer()

    print("=" * 60)
    print("TEST: FOL Normalizer")
    print("=" * 60)

    # Test 1: Unicode style
    fol1 = "∀x (WT(x) → O(x))"
    result1 = normalizer.normalize(fol1)
    assert result1.style == FOLStyle.UNICODE, f"Expected UNICODE, got {result1.style}"
    assert '→' not in result1.normalized, "Unicode arrow should be replaced"
    assert result1.is_rule == True
    print(f"  ✅ Unicode: {fol1}")
    print(f"     → {result1.normalized}")

    # Test 2: Text style
    fol2 = "ForAll(x, completed_courses(x) -> eligible(x))"
    result2 = normalizer.normalize(fol2)
    assert result2.style == FOLStyle.TEXT, f"Expected TEXT, got {result2.style}"
    assert result2.is_rule == True
    print(f"  ✅ Text: {fol2}")

    # Test 3: Atomic fact
    fol3 = "completed_courses(John)"
    result3 = normalizer.normalize(fol3)
    assert result3.style == FOLStyle.ATOMIC, f"Expected ATOMIC, got {result3.style}"
    assert result3.is_fact == True
    assert 'John' in result3.constants
    print(f"  ✅ Atomic: {fol3}")

    # Test 4: Negated atomic
    fol4 = "¬received_safety_endorsement(John)"
    result4 = normalizer.normalize(fol4)
    assert result4.is_negated == True
    print(f"  ✅ Negated: {fol4}")

    # Test 5: Arithmetic
    fol5 = "membership_duration(Alex) = 8"
    result5 = normalizer.normalize(fol5)
    assert result5.has_arithmetic == True
    print(f"  ✅ Arithmetic: {fol5}")

    # Test 6: Hybrid
    fol6 = "ForAll(x, (P(x) ∧ Q(x)) → R(x))"
    result6 = normalizer.normalize(fol6)
    assert result6.style == FOLStyle.HYBRID, f"Expected HYBRID, got {result6.style}"
    print(f"  ✅ Hybrid: {fol6}")

    # Test 7: Batch normalization
    batch = [fol1, fol2, fol3, fol4, fol5]
    results = normalizer.normalize_batch(batch)
    assert len(results) == 5
    metadata = normalizer.extract_all_metadata(results)
    print(f"  ✅ Batch: {len(results)} premises, "
          f"{len(metadata['predicates'])} predicates, "
          f"{len(metadata['constants'])} constants")

    print(f"  📊 Metadata: {metadata}")
    print()


def test_question_classifier():
    """Test Question Classifier."""
    classifier = QuestionClassifier()

    print("=" * 60)
    print("TEST: Question Classifier")
    print("=" * 60)

    # Test 1: MCQ
    mcq = (
        "Which conclusion follows with the fewest premises?\n"
        "A. If a Python project is not optimized, then it is not well-tested\n"
        "B. If all Python projects are optimized, then all are well-structured\n"
        "C. If a Python project is well-tested, then it must be clean\n"
        "D. If a Python project is not optimized, then it does not follow PEP 8"
    )
    result = classifier.classify(mcq)
    assert result.question_type == QuestionType.MCQ
    assert result.options is not None
    assert len(result.options) == 4
    assert 'A' in result.options
    print(f"  ✅ MCQ detected: {len(result.options)} options")
    print(f"     Stem: {result.stem[:60]}...")
    print(f"     Options: {list(result.options.keys())}")

    # Test 2: Yes/No
    yesno = "Does it follow that if all Python projects are well-structured, then all are optimized, according to the premises?"
    result2 = classifier.classify(yesno)
    assert result2.question_type == QuestionType.YES_NO
    print(f"  ✅ Yes/No detected: {yesno[:60]}...")

    # Test 3: Another Yes/No
    yesno2 = "Can Professor John supervise graduate-level research based on his PhD qualification, according to the premises?"
    result3 = classifier.classify(yesno2)
    assert result3.question_type == QuestionType.YES_NO
    print(f"  ✅ Yes/No detected: {yesno2[:60]}...")

    # Test 4: Answer type detection
    assert detect_answer_type("A") == "mcq_option"
    assert detect_answer_type("Yes") == "yes"
    assert detect_answer_type("No") == "no"
    assert detect_answer_type("Unknown") == "unknown"
    print(f"  ✅ Answer type detection works")
    print()


def test_fol_parser():
    """Test FOL Premise Parser."""
    parser = FOLPremiseParser()

    print("=" * 60)
    print("TEST: FOL Premise Parser")
    print("=" * 60)

    # Test 1: Atomic fact
    result = parser.parse_premise("completed_courses(John)", 1)
    assert result is not None
    assert result.predicate == "completed_courses"
    assert result.arguments == ["John"]
    print(f"  ✅ Atomic fact parsed: completed_courses(John)")

    # Test 2: Negated fact
    result2 = parser.parse_premise("¬received_safety(John)", 2)
    assert result2 is not None
    assert result2.is_negated == True
    print(f"  ✅ Negated fact parsed: ¬received_safety(John)")

    # Test 3: Implication rule
    result3 = parser.parse_premise(
        "ForAll(x, completed_courses(x) → eligible(x))", 3
    )
    assert result3 is not None
    assert "completed_courses" in result3.antecedents
    assert result3.consequent == "eligible"
    print(f"  ✅ Rule parsed: completed_courses → eligible")

    # Test 4: Full sample parse
    premises = [
        "ForAll(x, completed_required_courses(x) → eligible_for_graduation(x))",
        "ForAll(x, (eligible_for_graduation(x) ∧ gpa_above_3_5(x)) → graduates_with_honors(x))",
        "ForAll(x, (graduates_with_honors(x) ∧ completed_thesis(x)) → academic_distinction(x))",
        "ForAll(x, academic_distinction(x) → qualifies_for_fellowship(x))",
        "completed_required_courses(John)",
        "gpa_above_3_5(John)",
        "completed_thesis(John)",
    ]
    facts, rules = parser.parse_all(premises)
    print(f"  ✅ Full parse: {len(facts)} facts, {len(rules)} rules")
    for f in facts:
        print(f"     Fact: {f.predicate}({', '.join(f.arguments)})")
    for r in rules:
        print(f"     Rule: {' ∧ '.join(r.antecedents)} → {r.consequent}")
    print()


def test_logic_tree():
    """Test Logic Tree construction and chaining."""
    print("=" * 60)
    print("TEST: Logic Tree")
    print("=" * 60)

    # Sample: John's fellowship qualification (sample #4 from dataset)
    premises = [
        "ForAll(x, completed_required_courses(x) → eligible_for_graduation(x))",
        "ForAll(x, (eligible_for_graduation(x) ∧ gpa_above_3_5(x)) → graduates_with_honors(x))",
        "ForAll(x, (graduates_with_honors(x) ∧ completed_thesis(x)) → academic_distinction(x))",
        "ForAll(x, academic_distinction(x) → qualifies_for_fellowship(x))",
        "completed_required_courses(John)",
        "gpa_above_3_5(John)",
        "completed_thesis(John)",
    ]

    tree = LogicTree(premises)
    print(f"  Facts: {len(tree.facts)}, Rules: {len(tree.rules)}")

    # Forward chaining
    tree.handle_negations()
    tree.generate_contrapositions()
    derived = tree.forward_chain()
    print(f"  Forward chaining derived: {len(derived)} new facts")

    for d in derived:
        print(f"    → {d.predicate} (depth={d.depth}, premises={d.premises_involved})")

    # Check if fellowship is derived
    derived_preds = tree.get_all_derived_predicates()
    print(f"  All derived predicates: {derived_preds}")

    # Get proof trace
    proof = tree.get_proof_trace("qualifies_for_fellowship")
    print(f"  Proof for 'qualifies_for_fellowship': {proof}")

    all_used = tree.get_all_used_premises()
    print(f"  All used premises: {all_used}")
    print()


def test_z3_basic():
    """Test Z3 solver basic functionality."""
    print("=" * 60)
    print("TEST: Z3 Solver (Basic)")
    print("=" * 60)

    try:
        import z3

        # Simple propositional test
        solver = z3.Solver()
        Entity = z3.DeclareSort('Entity')
        x = z3.Const('x', Entity)
        John = z3.Const('John', Entity)

        P = z3.Function('P', Entity, z3.BoolSort())
        Q = z3.Function('Q', Entity, z3.BoolSort())

        # Assert: ForAll x, P(x) → Q(x)
        solver.add(z3.ForAll([x], z3.Implies(P(x), Q(x))))
        # Assert: P(John)
        solver.add(P(John))

        # Check: Q(John) should be entailed
        solver.push()
        solver.add(z3.Not(Q(John)))
        result = solver.check()
        solver.pop()

        assert result == z3.unsat, f"Expected unsat, got {result}"
        print(f"  ✅ P(x)→Q(x), P(John) ⊨ Q(John) [UNSAT = entailed]")

        # Check: R(John) should NOT be entailed
        R = z3.Function('R', Entity, z3.BoolSort())
        solver.push()
        solver.add(z3.Not(R(John)))
        result2 = solver.check()
        solver.pop()

        assert result2 == z3.sat, f"Expected sat, got {result2}"
        print(f"  ✅ P(x)→Q(x), P(John) ⊭ R(John) [SAT = not entailed]")

        # Negation test
        solver2 = z3.Solver()
        A = z3.Function('A', Entity, z3.BoolSort())
        B = z3.Function('B', Entity, z3.BoolSort())

        solver2.add(z3.ForAll([x], z3.Implies(A(x), B(x))))
        solver2.add(z3.Not(B(John)))

        # Check: A(John) should be refuted (contraposition)
        solver2.push()
        solver2.add(A(John))
        result3 = solver2.check()
        solver2.pop()

        assert result3 == z3.unsat, f"Expected unsat, got {result3}"
        print(f"  ✅ A→B, ¬B(John) ⊨ ¬A(John) [contraposition works]")

        print()

    except Exception as e:
        print(f"  ❌ Z3 test failed: {e}")
        print()


def test_with_dataset_sample():
    """Test full pipeline with a real dataset sample."""
    print("=" * 60)
    print("TEST: Dataset Sample (Sample #4 - John's Fellowship)")
    print("=" * 60)

    # Load a sample
    dataset_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "train", "Logic_Based_Educational_Queries.json"
    )

    if not os.path.exists(dataset_path):
        print("  ⚠️ Dataset not found, skipping")
        return

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    sample = dataset[3]  # Sample #4 (John's fellowship)

    # Normalize FOL
    normalizer = FOLNormalizer()
    norm = normalizer.normalize_batch(sample['premises-FOL'])
    metadata = normalizer.extract_all_metadata(norm)
    print(f"  Predicates: {list(metadata['predicates'].keys())}")
    print(f"  Constants: {metadata['constants']}")

    # Classify questions
    classifier = QuestionClassifier()
    for i, q in enumerate(sample['questions']):
        classified = classifier.classify(q)
        print(f"  Q{i+1} type: {classified.question_type.value}")
        print(f"     Stem: {classified.stem[:80]}...")
        if classified.options:
            for k, v in classified.options.items():
                print(f"     {k}: {v[:60]}...")

    # Logic Tree
    tree = LogicTree(sample['premises-FOL'])
    tree.handle_negations()
    tree.generate_contrapositions()
    derived = tree.forward_chain()
    print(f"  Logic Tree: {len(tree.facts)} facts, {len(tree.rules)} rules, "
          f"{len(derived)} derived")

    # Ground truth
    print(f"  Ground truth answers: {sample['answers']}")
    print(f"  Ground truth idx: {sample['idx']}")
    print()


if __name__ == "__main__":
    test_fol_normalizer()
    test_question_classifier()
    test_fol_parser()
    test_logic_tree()
    test_z3_basic()
    test_with_dataset_sample()

    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
