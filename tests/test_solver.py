"""
Pruebas Unitarias para el Solucionador Paso a Paso de Cinemática.
"""

import unittest
from src.models.solver import KinematicsSolver


class TestKinematicsSolver(unittest.TestCase):
    """Verifica la resolución algebraica, paso a paso, diagnósticos y conversiones."""

    def test_solve_final_velocity_standard(self):
        """
        Ejemplo del RTF:
        v0 = 10 m/s, a = 2 m/s², t = 5 s -> v = 20 m/s.
        """
        sol = KinematicsSolver.solve(
            scenario="MRUA",
            known_inputs={"v0": (10.0, "m/s"), "a": (2.0, "m/s²"), "t": (5.0, "s")},
            target_code="v"
        )
        self.assertTrue(sol.is_solvable)
        self.assertAlmostEqual(sol.final_value_si, 20.0)
        self.assertEqual(sol.target_spec.symbol, "v")
        self.assertIn("v = v₀ + a · t", sol.equation_formula)
        self.assertIn("v = (10 m/s) + [(2 m/s²) · (5 s)]", sol.substitution_text)
        self.assertIn("20", sol.physical_interpretation)

    def test_solve_time_quadratic(self):
        """
        Calcular tiempo mediante ecuación cuadrática:
        v0 = 4 m/s, a = 2 m/s², dx = 12 m.
        0.5*2*t² + 4*t - 12 = 0 -> t² + 4t - 12 = 0 -> (t + 6)(t - 2) = 0.
        Raíz física: t = 2 s.
        """
        sol = KinematicsSolver.solve(
            scenario="MRUA",
            known_inputs={"v0": (4.0, "m/s"), "a": (2.0, "m/s²"), "dx": (12.0, "m")},
            target_code="t"
        )
        self.assertTrue(sol.is_solvable)
        self.assertAlmostEqual(sol.final_value_si, 2.0)
        self.assertIsNotNone(sol.multiple_solutions_note)
        self.assertIn("t = 2", sol.calculation_steps[-1])

    def test_solve_torricelli_without_time(self):
        """
        Torricelli:
        v0 = 0 m/s, a = 3 m/s², dx = 24 m -> v² = 2*3*24 = 144 -> v = 12 m/s.
        """
        sol = KinematicsSolver.solve(
            scenario="MRUA",
            known_inputs={"v0": (0.0, "m/s"), "a": (3.0, "m/s²"), "dx": (24.0, "m")},
            target_code="v"
        )
        self.assertTrue(sol.is_solvable)
        self.assertAlmostEqual(sol.final_value_si, 12.0)
        self.assertIn("Torricelli", sol.equation_name)

    def test_unit_conversion_in_solver(self):
        """
        Entrada en km/h y minutos:
        v0 = 72 km/h (= 20 m/s), a = 1 m/s², t = 0.5 min (= 30 s).
        v = 20 + 1*30 = 50 m/s = 180 km/h.
        """
        sol = KinematicsSolver.solve(
            scenario="MRUA",
            known_inputs={"v0": (72.0, "km/h"), "a": (1.0, "m/s²"), "t": (0.5, "min")},
            target_code="v",
            target_unit="km/h"
        )
        self.assertTrue(sol.is_solvable)
        self.assertAlmostEqual(sol.final_value_si, 50.0)
        self.assertAlmostEqual(sol.final_value_target, 180.0)

    def test_insufficient_data_diagnostic(self):
        """Si faltan datos, explica qué datos se necesitan sin inventar valores."""
        sol = KinematicsSolver.solve(
            scenario="MRUA",
            known_inputs={"v0": (10.0, "m/s")},
            target_code="v"
        )
        self.assertFalse(sol.is_solvable)
        self.assertIsNotNone(sol.diagnostic_error)
        self.assertIn("Datos insuficientes", sol.diagnostic_error)

    def test_free_fall_solver(self):
        """Caída libre: v0 = 0, y0 = 45 m, g = 10 m/s² -> t_impacto = 3 s."""
        sol = KinematicsSolver.solve(
            scenario="CAIDA_LIBRE",
            known_inputs={"y0": (45.0, "m"), "v0": (0.0, "m/s"), "g": (10.0, "m/s²")},
            target_code="t_impacto"
        )
        self.assertTrue(sol.is_solvable)
        self.assertAlmostEqual(sol.final_value_si, 3.0)


if __name__ == "__main__":
    unittest.main()
