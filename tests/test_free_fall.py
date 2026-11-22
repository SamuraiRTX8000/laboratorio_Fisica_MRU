"""
Pruebas Unitarias para el Modelo Físico de Caída Libre y Lanzamiento Vertical.
"""

import unittest
from src.models.physics import FreeFallParameters, FreeFallPhysicsModel


class TestFreeFall(unittest.TestCase):
    """Verifica caída libre desde el reposo, lanzamiento vertical hacia arriba y hacia abajo."""

    def test_drop_from_rest(self):
        """
        Caída desde 45 metros con v0 = 0, g = 10 m/s²:
        t_impacto = √(2*45/10) = 3 s.
        v_impacto = -10 * 3 = -30 m/s.
        """
        params = FreeFallParameters(y0=45.0, v0=0.0, g=10.0)
        model = FreeFallPhysicsModel(params)

        self.assertAlmostEqual(model.t_subida, 0.0)
        self.assertAlmostEqual(model.h_max, 45.0)
        self.assertAlmostEqual(model.t_impact, 3.0)
        self.assertAlmostEqual(model.v_impact, -30.0)

        # En t = 1 s: y = 45 - 0.5*10*1 = 40 m, v = -10 m/s
        s1 = model.evaluate(1.0)
        self.assertAlmostEqual(s1.position, 40.0)
        self.assertAlmostEqual(s1.velocity, -10.0)
        self.assertAlmostEqual(s1.displacement, -5.0)
        self.assertAlmostEqual(s1.distance, 5.0)
        self.assertFalse(s1.reached_boundary)

        # En t = 3 s: impacta en y = 0
        s3 = model.evaluate(3.0)
        self.assertAlmostEqual(s3.position, 0.0)
        self.assertTrue(s3.reached_boundary)
        self.assertEqual(s3.boundary_name, "ground")

    def test_vertical_launch_upwards(self):
        """
        Lanzamiento vertical hacia arriba desde el suelo (y0 = 0) con v0 = +20 m/s, g = 10 m/s²:
        t_subida = 20 / 10 = 2 s.
        h_max = 20² / (2*10) = 20 m.
        t_vuelo = 2 * 2 = 4 s.
        v(4 s) = -20 m/s.
        """
        params = FreeFallParameters(y0=0.0, v0=20.0, g=10.0)
        model = FreeFallPhysicsModel(params)

        self.assertAlmostEqual(model.t_subida, 2.0)
        self.assertAlmostEqual(model.h_max, 20.0)
        self.assertAlmostEqual(model.t_vuelo_y0, 4.0)
        self.assertAlmostEqual(model.t_impact, 4.0)
        self.assertAlmostEqual(model.v_impact, -20.0)

        # En t = 2 s (cúspide)
        s2 = model.evaluate(2.0)
        self.assertAlmostEqual(s2.position, 20.0)
        self.assertAlmostEqual(s2.velocity, 0.0)
        self.assertAlmostEqual(s2.displacement, 20.0)
        self.assertAlmostEqual(s2.distance, 20.0)

        # En t = 3 s (bajando)
        # y = 20*3 - 0.5*10*9 = 60 - 45 = 15 m
        # d = 20 m subida + 5 m bajada = 25 m
        s3 = model.evaluate(3.0)
        self.assertAlmostEqual(s3.position, 15.0)
        self.assertAlmostEqual(s3.velocity, -10.0)
        self.assertAlmostEqual(s3.displacement, 15.0)
        self.assertAlmostEqual(s3.distance, 25.0)

    def test_thrown_downwards(self):
        """Lanzamiento hacia abajo desde 50 m con v0 = -10 m/s, g = 10 m/s²."""
        params = FreeFallParameters(y0=50.0, v0=-10.0, g=10.0)
        model = FreeFallPhysicsModel(params)

        self.assertEqual(model.t_subida, 0.0)
        self.assertEqual(model.h_max, 50.0)
        # y = 50 - 10*t - 5*t² = 0 -> 5t² + 10t - 50 = 0 -> t² + 2t - 10 = 0
        # t = (-2 + √(4 + 40))/2 = (-2 + √44)/2 = -1 + √11 ≈ 2.3166 s
        self.assertAlmostEqual(model.t_impact, -1.0 + (11.0 ** 0.5))


if __name__ == "__main__":
    unittest.main()
