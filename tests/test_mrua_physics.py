"""
Pruebas Unitarias para el Modelo Físico de MRUA y Sistema de Unidades.
"""

import unittest
from src.models.physics import TrackConfig, MRUAParameters, MRUAPhysicsModel
from src.models.units import UnitConverter, LengthUnit, TimeUnit, VelocityUnit, AccelerationUnit


class TestUnits(unittest.TestCase):
    """Verifica conversiones exactas entre todas las unidades soportadas."""

    def test_length_conversions(self):
        # 1 km = 1000 m
        self.assertAlmostEqual(UnitConverter.length_to_si(1.5, "km"), 1500.0)
        self.assertAlmostEqual(UnitConverter.length_from_si(1500.0, "km"), 1.5)

        # 250 cm = 2.5 m
        self.assertAlmostEqual(UnitConverter.length_to_si(250.0, "cm"), 2.5)
        self.assertAlmostEqual(UnitConverter.length_from_si(2.5, "cm"), 250.0)

        # 3000 mm = 3.0 m
        self.assertAlmostEqual(UnitConverter.length_to_si(3000.0, "mm"), 3.0)
        self.assertAlmostEqual(UnitConverter.length_from_si(3.0, "mm"), 3000.0)

    def test_time_conversions(self):
        # 2.5 min = 150 s
        self.assertAlmostEqual(UnitConverter.time_to_si(2.5, "min"), 150.0)
        self.assertAlmostEqual(UnitConverter.time_from_si(150.0, "min"), 2.5)

        # 1 h = 3600 s
        self.assertAlmostEqual(UnitConverter.time_to_si(1.0, "h"), 3600.0)
        self.assertAlmostEqual(UnitConverter.time_from_si(7200.0, "h"), 2.0)

    def test_velocity_conversions(self):
        # 72 km/h = 20 m/s
        self.assertAlmostEqual(UnitConverter.velocity_to_si(72.0, "km/h"), 20.0)
        self.assertAlmostEqual(UnitConverter.velocity_from_si(20.0, "km/h"), 72.0)

        # 500 cm/s = 5 m/s
        self.assertAlmostEqual(UnitConverter.velocity_to_si(500.0, "cm/s"), 5.0)

    def test_acceleration_conversions(self):
        # 200 cm/s² = 2 m/s²
        self.assertAlmostEqual(UnitConverter.acceleration_to_si(200.0, "cm/s²"), 2.0)
        self.assertAlmostEqual(UnitConverter.acceleration_from_si(2.0, "cm/s²"), 200.0)


class TestMRUAPhysics(unittest.TestCase):
    """Verifica las ecuaciones, casos de aceleración positiva, negativa, frenado e inversión de MRUA."""

    def setUp(self):
        self.track = TrackConfig(x_min=-100.0, x_max=100.0)

    def test_positive_acceleration_from_rest(self):
        """MRUA desde reposo: x0=0, v0=0, a=2 m/s² -> x(t)=t², v(t)=2t."""
        params = MRUAParameters(x0=0.0, v0=0.0, acceleration=2.0)
        model = MRUAPhysicsModel(self.track, params)

        # t = 0
        s0 = model.evaluate(0.0)
        self.assertEqual(s0.position, 0.0)
        self.assertEqual(s0.velocity, 0.0)
        self.assertEqual(s0.acceleration, 2.0)

        # t = 3 s -> x = 0 + 0 + 0.5*2*(3)^2 = 9 m, v = 2*3 = 6 m/s
        s3 = model.evaluate(3.0)
        self.assertAlmostEqual(s3.position, 9.0)
        self.assertAlmostEqual(s3.displacement, 9.0)
        self.assertAlmostEqual(s3.distance, 9.0)
        self.assertAlmostEqual(s3.velocity, 6.0)
        self.assertAlmostEqual(s3.speed, 6.0)

    def test_negative_acceleration_braking_and_reversal(self):
        """
        Frenado y cambio de sentido:
        x0=0, v0=+20 m/s, a=-4 m/s²
        Se detiene en t_turn = -20 / -4 = 5 s.
        x_turn = 0 + 20*5 - 0.5*4*25 = 100 - 50 = +50 m.
        En t = 5 s: v = 0 m/s, x = 50 m.
        En t = 8 s: x = 20*8 - 0.5*4*64 = 160 - 128 = 32 m.
        Distancia en t = 8 s:
        d = d(0 a 5) + d(5 a 8) = 50 m + |32 - 50| = 50 + 18 = 68 m!
        """
        params = MRUAParameters(x0=0.0, v0=20.0, acceleration=-4.0)
        model = MRUAPhysicsModel(self.track, params)

        self.assertIsNotNone(model.turnaround_time)
        self.assertAlmostEqual(model.turnaround_time, 5.0)
        self.assertAlmostEqual(model.turnaround_position, 50.0)

        # En t = 5 s
        s5 = model.evaluate(5.0)
        self.assertAlmostEqual(s5.position, 50.0)
        self.assertAlmostEqual(s5.velocity, 0.0)
        self.assertAlmostEqual(s5.displacement, 50.0)
        self.assertAlmostEqual(s5.distance, 50.0)

        # En t = 8 s
        s8 = model.evaluate(8.0)
        self.assertAlmostEqual(s8.position, 32.0)
        self.assertAlmostEqual(s8.displacement, 32.0)
        self.assertAlmostEqual(s8.distance, 68.0)  # Distancia escalar total correcta
        self.assertAlmostEqual(s8.velocity, -12.0) # Sentido negativo hacia atrás
        self.assertAlmostEqual(s8.speed, 12.0)

    def test_zero_acceleration_degenerates_to_mru(self):
        """Con a = 0, debe comportarse exactamente como MRU: x = x0 + v0*t."""
        params = MRUAParameters(x0=10.0, v0=5.0, acceleration=0.0)
        model = MRUAPhysicsModel(self.track, params)

        s4 = model.evaluate(4.0)
        self.assertAlmostEqual(s4.position, 30.0)
        self.assertAlmostEqual(s4.velocity, 5.0)
        self.assertAlmostEqual(s4.acceleration, 0.0)

    def test_boundary_detection(self):
        """Verifica que el móvil colisione con el límite x_max=100m."""
        params = MRUAParameters(x0=0.0, v0=0.0, acceleration=8.0)
        # 0.5 * 8 * t² = 100 -> 4 * t² = 100 -> t² = 25 -> t = 5 s
        model = MRUAPhysicsModel(self.track, params)
        self.assertAlmostEqual(model.max_effective_time, 5.0)

        s_bound = model.evaluate(6.0)
        self.assertAlmostEqual(s_bound.position, 100.0)
        self.assertTrue(s_bound.reached_boundary)
        self.assertEqual(s_bound.boundary_name, "x_max")


if __name__ == "__main__":
    unittest.main()
