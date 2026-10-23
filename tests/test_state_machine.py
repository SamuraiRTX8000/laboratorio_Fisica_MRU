"""
Pruebas Unitarias para el Controlador de Estado, Cronometría y Pausas.
"""

import unittest
import time
from src.models.physics import TrackConfig, MRUParameters
from src.models.experiment_state import (
    ExperimentStatus,
    ExperimentControllerModel
)


class TestExperimentStateMachine(unittest.TestCase):
    """Verifica la lógica temporal, transiciones de estado y recolección de muestras."""

    def setUp(self):
        self.track = TrackConfig(x_min=-20.0, x_max=80.0)
        self.params = MRUParameters(x0=0.0, velocity=20.0)  # Tardaría 4.0 s en llegar a 80m

    def test_initial_state_ready(self):
        """Verifica que el estado inicial sea READY con tiempos en 0."""
        ctrl = ExperimentControllerModel(self.track, self.params)
        self.assertEqual(ctrl.status, ExperimentStatus.READY)
        t_eff, t_total = ctrl.get_current_times()
        self.assertEqual(t_eff, 0.0)
        self.assertEqual(t_total, 0.0)
        self.assertEqual(len(ctrl.samples), 1)  # Muestra inicial t=0

    def test_start_and_update(self):
        """Verifica la transición a RUNNING y el avance de los cronómetros."""
        ctrl = ExperimentControllerModel(self.track, self.params)
        ctrl.start()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        time.sleep(0.05)
        state = ctrl.update()
        t_eff, t_total = ctrl.get_current_times()

        self.assertGreater(t_eff, 0.04)
        self.assertGreater(t_total, 0.04)
        self.assertAlmostEqual(state.position, self.params.velocity * t_eff, delta=0.2)

    def test_pause_and_resume_cycles(self):
        """
        Verifica que al pausar:
        1. t_eff se congele estrictamente.
        2. t_total continúe avanzando.
        3. Al reanudar, no haya saltos discontinuos de posición.
        """
        ctrl = ExperimentControllerModel(self.track, self.params)
        ctrl.start()
        time.sleep(0.05)
        ctrl.update()

        # Pausar
        ctrl.pause()
        self.assertEqual(ctrl.status, ExperimentStatus.PAUSED)
        self.assertEqual(ctrl.pause_count, 1)

        t_eff_paused_1, t_total_paused_1 = ctrl.get_current_times()
        pos_paused_1 = ctrl.current_physics_state.position

        # Esperar durante la pausa
        time.sleep(0.06)
        ctrl.update()

        t_eff_paused_2, t_total_paused_2 = ctrl.get_current_times()
        pos_paused_2 = ctrl.current_physics_state.position

        # t_eff DEBE mantenerse congelado durante la pausa
        self.assertAlmostEqual(t_eff_paused_1, t_eff_paused_2, delta=0.001)
        # La posición DEBE permanecer inalterada
        self.assertAlmostEqual(pos_paused_1, pos_paused_2, delta=0.001)
        # t_total DEBE haber crecido
        self.assertGreater(t_total_paused_2, t_total_paused_1)

        # Reanudar
        ctrl.resume()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)
        time.sleep(0.05)
        ctrl.update()

        t_eff_resumed, t_total_resumed = ctrl.get_current_times()
        # t_eff debe haber continuado desde donde quedó, sin saltar
        self.assertGreater(t_eff_resumed, t_eff_paused_1)
        # La posición debe corresponder a x0 + v * t_eff
        expected_pos = self.params.x0 + self.params.velocity * t_eff_resumed
        self.assertAlmostEqual(ctrl.current_physics_state.position, expected_pos, delta=0.2)

    def test_stop_and_summary_generation(self):
        """Verifica que finalizar detenga el cronómetro y genere un resumen correcto."""
        ctrl = ExperimentControllerModel(self.track, self.params)
        ctrl.start()
        time.sleep(0.04)
        ctrl.pause()
        time.sleep(0.04)
        ctrl.resume()
        time.sleep(0.04)
        ctrl.stop("Prueba completada")

        self.assertEqual(ctrl.status, ExperimentStatus.FINISHED)
        self.assertEqual(ctrl.termination_reason, "Prueba completada")

        summary = ctrl.generate_summary()
        self.assertEqual(summary.x0, 0.0)
        self.assertGreater(summary.t_eff, 0.05)
        self.assertGreater(summary.t_total, summary.t_eff)
        self.assertEqual(summary.pause_count, 1)
        self.assertTrue(summary.is_mru_verified)

    def test_automatic_boundary_termination(self):
        """Verifica que al alcanzar el límite de la pista se detenga automáticamente."""
        # Colocamos el vehículo muy cerca de x_max
        params = MRUParameters(x0=79.5, velocity=20.0)  # Tardará 0.025 s en llegar a 80m
        ctrl = ExperimentControllerModel(self.track, params)
        ctrl.start()

        # Esperamos tiempo suficiente para que cruce el límite
        time.sleep(0.05)
        ctrl.update()

        self.assertEqual(ctrl.status, ExperimentStatus.FINISHED)
        self.assertEqual(ctrl.current_physics_state.position, 80.0)
        self.assertIn("Alcanzó el límite superior", ctrl.termination_reason)


if __name__ == "__main__":
    unittest.main()
