"""
Pruebas Unitarias Automatizadas para el Modelo Físico de Cinemática (MRU).
"""

import unittest
from src.models.physics import TrackConfig, MRUParameters, MRUPhysicsModel


class TestMRUPhysics(unittest.TestCase):
    """Pruebas del rigor físico y matemático de las ecuaciones de MRU."""

    def setUp(self):
        self.track = TrackConfig(x_min=-50.0, x_max=50.0)

    def test_positive_velocity_motion(self):
        """Comprueba el movimiento en sentido positivo: x(t) = x0 + v * t."""
        params = MRUParameters(x0=0.0, velocity=10.0)
        model = MRUPhysicsModel(self.track, params)

        # En t=0 s
        s0 = model.evaluate(0.0)
        self.assertEqual(s0.position, 0.0)
        self.assertEqual(s0.displacement, 0.0)
        self.assertEqual(s0.distance, 0.0)
        self.assertEqual(s0.velocity, 10.0)
        self.assertEqual(s0.speed, 10.0)

        # En t=2.5 s -> x = 0 + 10 * 2.5 = 25.0 m
        s2 = model.evaluate(2.5)
        self.assertAlmostEqual(s2.position, 25.0)
        self.assertAlmostEqual(s2.displacement, 25.0)
        self.assertAlmostEqual(s2.distance, 25.0)
        self.assertFalse(s2.reached_boundary)

        # En t=5.0 s -> x = 0 + 10 * 5.0 = 50.0 m (alcanza x_max)
        s5 = model.evaluate(5.0)
        self.assertAlmostEqual(s5.position, 50.0)
        self.assertTrue(s5.reached_boundary)
        self.assertEqual(s5.boundary_name, "x_max")

    def test_negative_velocity_motion(self):
        """Comprueba el movimiento en sentido negativo hacia x_min."""
        params = MRUParameters(x0=10.0, velocity=-5.0)
        model = MRUPhysicsModel(self.track, params)

        # En t=4 s -> x = 10 + (-5)*4 = -10 m
        s4 = model.evaluate(4.0)
        self.assertAlmostEqual(s4.position, -10.0)
        self.assertAlmostEqual(s4.displacement, -20.0)  # -10 - 10 = -20 m (vector)
        self.assertAlmostEqual(s4.distance, 20.0)        # Distancia recorrida es escalar positivo
        self.assertEqual(s4.speed, 5.0)

        # Tiempo para alcanzar x_min (-50 m):
        # t = (-50 - 10) / (-5) = 12 s
        self.assertAlmostEqual(model.max_effective_time, 12.0)
        s_bound = model.evaluate(12.0)
        self.assertAlmostEqual(s_bound.position, -50.0)
        self.assertTrue(s_bound.reached_boundary)
        self.assertEqual(s_bound.boundary_name, "x_min")

    def test_zero_velocity_at_rest(self):
        """Comprueba que con v = 0 el vehículo permanezca en reposo."""
        params = MRUParameters(x0=15.0, velocity=0.0)
        model = MRUPhysicsModel(self.track, params)

        self.assertEqual(model.max_effective_time, float('inf'))

        for t in [0.0, 10.0, 100.0]:
            st = model.evaluate(t)
            self.assertEqual(st.position, 15.0)
            self.assertEqual(st.displacement, 0.0)
            self.assertEqual(st.distance, 0.0)
            self.assertEqual(st.velocity, 0.0)
            self.assertEqual(st.speed, 0.0)
            self.assertFalse(st.reached_boundary)

    def test_boundary_capping_no_overshoot(self):
        """Verifica que el móvil nunca traspase los límites físicos de la pista."""
        params = MRUParameters(x0=40.0, velocity=10.0)
        model = MRUPhysicsModel(self.track, params)

        # Tiempo hasta x_max (50 m): (50 - 40) / 10 = 1.0 s
        self.assertAlmostEqual(model.max_effective_time, 1.0)

        # Si se evalúa en t = 5.0 s (mucho mayor al límite), debe mantenerse en 50 m
        s_over = model.evaluate(5.0)
        self.assertEqual(s_over.position, 50.0)
        self.assertTrue(s_over.reached_boundary)
        self.assertEqual(s_over.t_eff, 1.0)  # t_eff saturado al límite exacto

    def test_invalid_parameters_validation(self):
        """Verifica que configuraciones físicamente imposibles lancen excepciones descriptivas."""
        # x_min >= x_max
        with self.assertRaises(ValueError):
            TrackConfig(x_min=10.0, x_max=5.0)

        # x0 fuera de la pista
        with self.assertRaises(ValueError):
            params = MRUParameters(x0=60.0, velocity=5.0)
            MRUPhysicsModel(self.track, params)

        # x0 en el límite x_max y velocidad positiva (imposible avanzar a la derecha)
        with self.assertRaises(ValueError):
            params = MRUParameters(x0=50.0, velocity=2.0)
            MRUPhysicsModel(self.track, params)

        # x0 en el límite x_min y velocidad negativa (imposible avanzar a la izquierda)
        with self.assertRaises(ValueError):
            params = MRUParameters(x0=-50.0, velocity=-2.0)
            MRUPhysicsModel(self.track, params)

    def test_average_velocity_and_speed_calculations(self):
        """Verifica la distinción entre velocidad media (vector) y rapidez media (escalar)."""
        disp = -30.0
        dist = 30.0
        t = 6.0

        v_avg = MRUPhysicsModel.calculate_average_velocity(disp, t)
        s_avg = MRUPhysicsModel.calculate_average_speed(dist, t)

        self.assertAlmostEqual(v_avg, -5.0)
        self.assertAlmostEqual(s_avg, 5.0)

        # Manejo de t = 0
        self.assertEqual(MRUPhysicsModel.calculate_average_velocity(disp, 0.0), 0.0)
        self.assertEqual(MRUPhysicsModel.calculate_average_speed(dist, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
