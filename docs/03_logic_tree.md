# 🌳 Logic Tree - Cây Luận Lý Chi Tiết

> **Nghiên cứu nền tảng:** Tree-of-Thought (Yao et al., 2023), ProofWriter (Tafjord et al., 2021)  
> **Mục đích:** Xây dựng cấu trúc DAG biểu diễn chuỗi suy luận từ premises → conclusion

---

## 1. Tổng Quan Logic Tree

### 1.1 Tại Sao Cần Logic Tree?

| Vấn đề | Logic Tree giải quyết |
|:---|:---|
| Premises quá nhiều (max 36) | **Premise Selection** - chỉ chọn premises liên quan |
| Chuỗi suy luận dài | **Path Finding** - tìm đường ngắn nhất đến conclusion |
| Nhiều đường suy luận | **Branch Exploration** - thử tất cả branches |
| Phát hiện contradiction | **Conflict Detection** - tìm ¬P khi đã có P |
| Giải thích reasoning | **Trace Generation** - output step-by-step proof |
| Xử lý "Unknown" | **Incompleteness Detection** - biết khi nào thiếu info |

### 1.2 Formal Definition

```
Logic Tree T = (N, E, F, R, G) where:
  N = set of nodes (propositions)
  E = set of directed edges (inference rules)
  F ⊆ N = set of fact nodes (atomic premises, leaves)
  R ⊆ N = set of rule nodes (implication premises)
  G ∈ N = goal node (conclusion to prove)
  
  Each edge e = (n1, n2, rule_id) means:
    "node n1 contributes to deriving node n2 via rule rule_id"
```

---

## 2. Các Loại Node Trong Logic Tree

### 2.1 Fact Node (Lá - Leaf)

```python
@dataclass
class FactNode:
    """Atomic proposition đã biết đúng/sai."""
    id: str
    predicate: str          # e.g., "completed_courses"
    arguments: List[str]    # e.g., ["John"]
    is_negated: bool        # True nếu ¬P(x)
    premise_index: int      # Index trong premises list
    
    # Ví dụ:
    # "completed_core_curriculum(Sophia)" → FactNode("f1", "completed_core_curriculum", ["Sophia"], False, 7)
    # "¬received_safety_endorsement(John)" → FactNode("f2", "received_safety_endorsement", ["John"], True, 7)
```

### 2.2 Rule Node (Nút trung gian)

```python
@dataclass 
class RuleNode:
    """Implication rule: antecedents → consequent."""
    id: str
    antecedents: List[str]     # Predicates cần thỏa mãn
    consequent: str            # Predicate được suy ra
    premise_index: int         # Index trong premises list
    is_universal: bool         # True nếu ∀x
    bound_variables: List[str] # Biến bị ràng buộc
    
    # Ví dụ:
    # "∀x (WT(x) → O(x))" → RuleNode("r1", ["WT"], "O", 1, True, ["x"])
    # "∀x (A(x) ∧ B(x) → C(x))" → RuleNode("r2", ["A", "B"], "C", 2, True, ["x"])
```

### 2.3 Derived Node (Nút được suy ra)

```python
@dataclass
class DerivedNode:
    """Proposition suy ra từ forward/backward chaining."""
    id: str
    predicate: str
    arguments: List[str]
    derived_from: List[str]    # IDs of contributing nodes
    rule_used: str             # ID of rule used
    depth: int                 # Số bước suy luận từ facts
```

### 2.4 Goal Node (Đích)

```python
@dataclass
class GoalNode:
    """Conclusion cần chứng minh/bác bỏ."""
    id: str
    predicate: str
    arguments: List[str]
    is_negated: bool
    status: str  # "proven" | "disproven" | "unknown"
```

---

## 3. Thuật Toán Xây Dựng Logic Tree

### 3.1 Phase 1: Parse Premises

```python
def parse_premises(premises_fol: List[str]) -> Tuple[List[FactNode], List[RuleNode]]:
    """
    Phân loại premises thành Facts và Rules.
    
    Rules for classification:
    - Nếu có quantifier + implication → RuleNode
    - Nếu là atomic proposition → FactNode
    - Nếu có negation trước atomic → FactNode(negated=True)
    """
    facts = []
    rules = []
    
    for i, fol in enumerate(premises_fol):
        if is_implication(fol):
            antecedents, consequent = split_implication(fol)
            rules.append(RuleNode(
                id=f"r{i+1}",
                antecedents=antecedents,
                consequent=consequent,
                premise_index=i+1,
                is_universal='ForAll' in fol or '∀' in fol,
                bound_variables=extract_bound_vars(fol)
            ))
        else:
            predicate, args, negated = parse_atomic(fol)
            facts.append(FactNode(
                id=f"f{i+1}",
                predicate=predicate,
                arguments=args,
                is_negated=negated,
                premise_index=i+1
            ))
    
    return facts, rules
```

### 3.2 Phase 2: Build Adjacency Graph

```python
def build_graph(facts: List[FactNode], rules: List[RuleNode]) -> dict:
    """
    Xây dựng đồ thị adjacency cho Logic Tree.
    
    Graph structure:
    {
        predicate_name: {
            'facts': [FactNode, ...],
            'as_antecedent': [RuleNode, ...],  # Rules where this is antecedent
            'as_consequent': [RuleNode, ...],   # Rules where this is consequent
        }
    }
    """
    graph = defaultdict(lambda: {'facts': [], 'as_antecedent': [], 'as_consequent': []})
    
    for fact in facts:
        graph[fact.predicate]['facts'].append(fact)
    
    for rule in rules:
        for ant in rule.antecedents:
            graph[ant]['as_antecedent'].append(rule)
        graph[rule.consequent]['as_consequent'].append(rule)
    
    return graph
```

### 3.3 Phase 3: Forward Chaining

```python
def forward_chaining(graph: dict, facts: List[FactNode], 
                     max_depth: int = 10) -> List[DerivedNode]:
    """
    Forward Chaining Algorithm:
    
    1. Initialize known_facts = set of all FactNodes
    2. Repeat:
       a. For each RuleNode R:
          - Check if ALL antecedents of R are in known_facts
          - If yes AND consequent not already known:
            * Create DerivedNode
            * Add to known_facts
       b. If no new facts derived → STOP
    3. Return all derived nodes with derivation trace
    
    Time Complexity: O(|Rules| × |Facts| × max_depth)
    """
    known = {}  # predicate → {entity → DerivedNode}
    derived = []
    
    # Initialize with atomic facts
    for fact in facts:
        entity = tuple(fact.arguments)
        known.setdefault(fact.predicate, {})[entity] = fact
    
    for depth in range(max_depth):
        new_derived = []
        
        for rule in get_all_rules(graph):
            # Try to match all antecedents
            bindings = find_matching_bindings(rule, known)
            
            for binding in bindings:
                consequent_entity = apply_binding(rule.consequent, binding)
                
                if consequent_entity not in known.get(rule.consequent, {}):
                    node = DerivedNode(
                        id=f"d{len(derived)+1}",
                        predicate=rule.consequent,
                        arguments=list(consequent_entity),
                        derived_from=[
                            known[ant][apply_binding(ant, binding)].id 
                            for ant in rule.antecedents
                        ],
                        rule_used=rule.id,
                        depth=depth + 1
                    )
                    new_derived.append(node)
                    known.setdefault(rule.consequent, {})[consequent_entity] = node
        
        if not new_derived:
            break
        derived.extend(new_derived)
    
    return derived
```

### 3.4 Phase 4: Backward Chaining

```python
def backward_chaining(graph: dict, goal: GoalNode, 
                      known: dict, max_depth: int = 10) -> Optional[List]:
    """
    Backward Chaining Algorithm:
    
    1. If goal is in known_facts → RETURN proof trace
    2. Find all rules where goal.predicate is consequent
    3. For each rule R:
       a. Recursively try to prove each antecedent
       b. If ALL antecedents proven → goal is proven
    4. If no rule works → RETURN None (cannot prove)
    
    This is essentially a depth-first search on the Logic Tree.
    """
    # Base case: goal already known
    if goal.predicate in known:
        return [known[goal.predicate]]
    
    # Find applicable rules
    rules = graph[goal.predicate]['as_consequent']
    
    for rule in rules:
        proof_branches = []
        all_proved = True
        
        for antecedent in rule.antecedents:
            sub_goal = GoalNode(
                id=f"sg_{antecedent}",
                predicate=antecedent,
                arguments=goal.arguments,
                is_negated=False,
                status="unknown"
            )
            sub_proof = backward_chaining(graph, sub_goal, known, max_depth - 1)
            
            if sub_proof is None:
                all_proved = False
                break
            proof_branches.extend(sub_proof)
        
        if all_proved:
            return proof_branches + [rule, goal]
    
    return None  # Cannot prove
```

---

## 4. Xử Lý Các Pattern Đặc Biệt

### 4.1 Contraposition (Phản đề)

Từ `A → B`, tự động sinh thêm `¬B → ¬A`

```python
def generate_contrapositions(rules: List[RuleNode]) -> List[RuleNode]:
    """
    Cho mỗi rule A → B, sinh rule ¬B → ¬A
    
    Ví dụ:
      ∀x (WT(x) → O(x))
    Sinh thêm:
      ∀x (¬O(x) → ¬WT(x))
    
    Quan trọng cho câu hỏi dạng:
    "If not optimized, then not well-tested" (contraposition of P1)
    """
    contras = []
    for rule in rules:
        contra = RuleNode(
            id=f"{rule.id}_contra",
            antecedents=[f"NOT_{rule.consequent}"],
            consequent=f"NOT_{rule.antecedents[0]}",
            premise_index=rule.premise_index,
            is_universal=rule.is_universal,
            bound_variables=rule.bound_variables
        )
        contras.append(contra)
    return contras
```

### 4.2 Transitivity Closure

```python
def compute_transitivity_closure(graph: dict, relation: str) -> dict:
    """
    Cho relation có tính bắc cầu (vd: higher(A,B) ∧ higher(B,C) → higher(A,C))
    Tính closure đầy đủ.
    
    Ví dụ dataset:
      higher(PhD, MSc), higher(MSc, BA)
      → Sinh: higher(PhD, BA)
    
    Algorithm: Floyd-Warshall trên relation
    """
    # Collect all (a, b) pairs where relation(a, b) holds
    pairs = set()
    for fact in graph.get(relation, {}).get('facts', []):
        pairs.add((fact.arguments[0], fact.arguments[1]))
    
    # Closure
    changed = True
    while changed:
        changed = False
        new_pairs = set()
        for (a, b) in pairs:
            for (c, d) in pairs:
                if b == c and (a, d) not in pairs:
                    new_pairs.add((a, d))
                    changed = True
        pairs.update(new_pairs)
    
    return pairs
```

### 4.3 Negation Handling

```python
def handle_negation_in_tree(graph: dict, facts: List[FactNode]):
    """
    Xử lý negation trong Logic Tree:
    
    1. Nếu ¬P(x) là fact:
       - Block tất cả rules cần P(x) làm antecedent
       - Kích hoạt contraposition rules cần ¬P(x)
    
    2. Nếu rule có negation trong antecedent: ¬P(x) → Q(x)
       - Chỉ fire khi P(x) KHÔNG có trong known facts
       - Closed World Assumption (CWA): nếu P(x) không biết → ¬P(x)
    
    Ví dụ: "¬received_safety_endorsement(John)"
    → Blocks: rule "can_transport_hazardous_materials" vì cần safety_endorsement
    """
    negated_facts = {f.predicate: f for f in facts if f.is_negated}
    
    for predicate, fact in negated_facts.items():
        # Block rules requiring this predicate
        for rule in graph[predicate]['as_antecedent']:
            rule.blocked = True
            rule.block_reason = f"Negated by {fact.id}"
```

### 4.4 Existential Quantifier (∃)

```python
def handle_existential(fol: str) -> FactNode:
    """
    Skolemization: ∃x P(x) → P(skolem_constant)
    
    Ví dụ: "∃x (BP(x))" → "BP(entity_1)"
    
    Lưu ý: Skolem constant chỉ dùng cho chứng minh tồn tại,
    không dùng cho universal conclusions.
    """
    pass
```

---

## 5. Logic Tree cho Từng Loại Câu Hỏi

### 5.1 MCQ: Chuyển giao (Fallback) cho Z3 & LLM-CoT

Logic Tree là một cấu trúc biểu diễn DAG dựa trên ký hiệu (Symbolic FOL), do đó nó **rất mạnh** với các phép chứng minh mệnh đề đơn giản (Yes/No), nhưng lại **vô cùng yếu** khi đối mặt với các đáp án trắc nghiệm bằng ngôn ngữ tự nhiên (Natural Language).

Ví dụ một đáp án MCQ phức tạp: *"Which conclusion follows with the fewest premises?"*
Để giải câu này bằng Logic Tree, ta cần một bộ phân tích cú pháp (Parser) hoàn hảo để dịch ngược mỗi đáp án A, B, C, D từ tiếng Anh sang FOL, sau đó chạy Backward Chaining cho từng cái, rồi so sánh độ dài (`proof_length`). Điều này là không khả thi và thiếu chính xác.

Do đó, **chiến lược hiện tại của Pipeline đối với MCQ là:**
1. Logic Tree **không giải** câu hỏi dạng MCQ (trả về `None`) để tránh đưa ra kết luận sai lệch dựa trên so khớp chuỗi (keyword matching).
2. Tự động chuyển giao (fallback) sang **Z3 Solver** (nếu LLM dịch được sang code Z3).
3. Nếu Z3 thất bại, chuyển giao cho **LLM Chain-of-Thought (CoT)** để giải quyết bằng khả năng suy luận ngôn ngữ tự nhiên.

```python
# Trích xuất từ src/main.py
elif classified.question_type == QuestionType.MCQ:
    # Logic Tree operates purely on symbolic FOL predicates.
    # Since MCQ options are in Natural Language and can contain complex logic
    # (like counting premises or nested implications), a simple keyword match
    # is logically unsound and leads to wrong answers.
    # 
    # Proper solution: Fallback to Z3 or LLM-CoT.
    return None
```

### 5.2 Yes/No: Entailment Check

```python
def solve_yesno_with_tree(premises_fol, question):
    """
    Strategy:
    1. Parse question thành goal proposition
    2. Forward chain từ facts
    3. Check if goal is derived:
       - Goal in derived → "Yes"
       - ¬Goal in derived → "No"
       - Neither → "Unknown"
    """
    facts, rules = parse_premises(premises_fol)
    graph = build_graph(facts, rules)
    derived = forward_chaining(graph, facts)
    
    goal = parse_question_to_goal(question)
    neg_goal = negate_goal(goal)
    
    if goal_is_derived(goal, derived):
        return "Yes"
    elif goal_is_derived(neg_goal, derived):
        return "No"
    else:
        return "Unknown"
```

---

## 6. Visualization & Debugging

```python
def visualize_logic_tree(tree, output_path: str):
    """
    Generate DOT/Graphviz visualization of Logic Tree.
    
    Color coding:
    - 🟢 Green: Fact nodes (known facts)
    - 🔵 Blue: Derived nodes (proven)
    - 🔴 Red: Blocked nodes (negated/unreachable)
    - 🟡 Yellow: Goal node
    - ⚪ Gray: Unused premises
    """
    pass
```

### Ví Dụ Output

```
Logic Tree for: "Does John qualify for fellowship?"

[FACT] completed_courses(John)     ← P5
[FACT] gpa_above_3_5(John)         ← P6
[FACT] thesis(John)                ← P7
  │
  ├──[RULE P1]──→ [DERIVED] eligible_graduation(John)     depth=1
  │                    │
  │                    ├──[RULE P2]──→ [DERIVED] honors(John)    depth=2
  │                    │                    │
  │                    │                    ├──[RULE P3]──→ [DERIVED] distinction(John)  depth=3
  │                    │                    │                    │
  │                    │                    │                    ├──[RULE P4]──→ [GOAL ✅] fellowship(John)  depth=4
  
Answer: Yes
Premises used: P1, P2, P3, P4, P5, P6, P7
Proof depth: 4 steps
```

---

## 7. Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|:---|:---|:---|
| Parse premises | O(n) | O(n) |
| Build graph | O(n × m) | O(n × m) |
| Forward chaining | O(R × F × D) | O(F × D) |
| Backward chaining | O(R^D) worst case | O(D) stack |
| Contraposition | O(R) | O(R) |
| Transitivity closure | O(V³) | O(V²) |

Trong đó: n = premises, m = predicates, R = rules, F = facts, D = max depth, V = values
