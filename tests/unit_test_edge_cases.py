"""
tests/unit_test_edge_cases.py

Unit tests cho P0: Symbol Registry và SymPy Solver alias fallback.
Dàn test này đảm bảo rằng Registry hoạt động đúng và Solver có thể giải
được các bài toán dù ký hiệu bị lệch pha.
"""

import sys
import os
import unittest

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.symbol_registry import get_aliases
from pipeline.type2.sympy_solver import _solve_single

class TestSymbolRegistry(unittest.TestCase):
    def test_get_aliases_electrostatics(self):
        # Yêu cầu tìm năng lượng E trong bài tĩnh điện -> Nó là E_field
        aliases = get_aliases("E", domain="electrostatics")
        self.assertEqual(aliases[0], "E_field")
        self.assertIn("E", aliases)

    def test_get_aliases_ac_circuits(self):
        # Yêu cầu tìm năng lượng E trong bài xoay chiều -> Nó là W (năng lượng)
        aliases = get_aliases("E", domain="ac_circuits")
        self.assertEqual(aliases[0], "W")
        self.assertIn("E", aliases)

    def test_get_aliases_reactance(self):
        # Yêu cầu tìm dung kháng
        aliases = get_aliases("Z_C", domain="ac_circuits")
        self.assertEqual(aliases[0], "Z_C")
        self.assertIn("X_C", aliases)

class TestSympySolverFallback(unittest.TestCase):
    def test_solve_capacitor_energy_with_E_find(self):
        # Giả lập: Bài toán yêu cầu tìm "E" (năng lượng) nhưng DB dùng "W" (theo chuẩn hoá mới)
        formula = "W = 0.5 * C * U**2"
        given = {"C": 1e-6, "U": 10}
        find = "E"
        domain = "ac_circuits" # Domain mà E -> W
        
        # Hàm _solve_single giờ sẽ thử get_aliases("E", "ac_circuits") -> ["W", "E", ...]
        # Nên nó sẽ giải ra được W
        res = _solve_single(formula, given, find, domain=domain)
        self.assertIsNotNone(res)
        self.assertAlmostEqual(float(res["answer"]), 0.5 * 1e-6 * 100)
        self.assertIn("W", res["steps"][-2]) # Result: E = ...

if __name__ == "__main__":
    unittest.main()
