"""
Pruebas de Integración para los Controladores de Simulación de MRUA y Caída Libre.
"""

import unittest
import tkinter as tk
import tempfile
import time

from src.controllers.simulation_controller import MRUASimulationController, FreeFallSimulationController
from src.gui.mrua_track_view import MRUATrackView
from src.gui.specialized_telemetry import MRUATelemetryPanel, VerticalTelemetryPanel
from src.gui.mrua_plots_view import MRUAPlotsView
from src.gui.mrua_control_panel import MRUAControlPanel
from src.gui.vertical_track_view import VerticalTrackView
from src.gui.free_fall_control_panel import FreeFallControlPanel
from src.models.physics import TrackConfig, MRUAParameters, FreeFallParameters
from src.models.experiment_state import ExperimentStatus
from src.data.repository import ExperimentRepository
from src.data.exporter import ExperimentDataExporter


class TestMRUASimulationController(unittest.TestCase):
    """Pruebas de ciclo de vida, persistencia y vistas para MRUASimulationController."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = ExperimentRepository(base_dir=self.temp_dir.name)
        self.root = tk.Tk()
        self.root.withdraw()

        self.track_cfg = TrackConfig(x_min=-100.0, x_max=100.0)
        self.params = MRUAParameters(x0=0.0, v0=1.0, acceleration=0.5)

        self.controller = None
        self.track_view = MRUATrackView(self.root, self.track_cfg)
        self.plots = MRUAPlotsView(self.root, is_vertical=False)
        self.telemetry = MRUATelemetryPanel(self.root)
        self.controls = MRUAControlPanel(
            self.root,
            on_start=lambda: self.controller.start() if self.controller else None,
            on_pause=lambda: self.controller.pause() if self.controller else None,
            on_resume=lambda: self.controller.resume() if self.controller else None,
            on_stop=lambda: self.controller.stop() if self.controller else None,
            on_reset=lambda: self.controller.reset() if self.controller else None,
            on_config_changed=lambda t, p: self.controller.on_config_changed(t, p) if self.controller else None
        )

        self.controller = MRUASimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.track_view,
                self.plots,
                self.telemetry,
                self.controls
            ),
            repository=self.repo
        )
        self.controller.on_config_changed(self.track_cfg, self.params)
        # Calentar Tkinter y matplotlib antes del cronometraje
        self.root.update()

    def tearDown(self):
        if self.controller:
            self.controller._cancel_scheduled_frame()
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_initial_state(self):
        """El controlador inicia en estado READY con parámetros de MRUA."""
        self.assertEqual(self.controller.status, ExperimentStatus.READY)
        self.assertEqual(self.controller.params.acceleration, 0.5)
        self.assertEqual(self.controller.params.v0, 1.0)

    def test_start_pause_resume_reset_cycle(self):
        """Ciclo completo: Start -> Run -> Pause -> Resume -> Reset."""
        self.controller.start()
        self.assertEqual(self.controller.status, ExperimentStatus.RUNNING)

        for _ in range(5):
            self.root.update()
            time.sleep(0.01)

        self.controller.pause()
        self.assertEqual(self.controller.status, ExperimentStatus.PAUSED)
        self.assertEqual(self.controller.model.pause_count, 1)

        self.controller.resume()
        self.assertEqual(self.controller.status, ExperimentStatus.RUNNING)

        self.controller.reset()
        self.assertEqual(self.controller.status, ExperimentStatus.READY)
        self.assertEqual(self.controller.model.current_physics_state.position, 0.0)

    def test_stop_and_repository_persistence(self):
        """Detener la simulación guarda el experimento de MRUA en el repositorio."""
        self.controller.start()
        for _ in range(5):
            self.root.update()
            time.sleep(0.01)

        self.controller.stop()
        self.assertEqual(self.controller.status, ExperimentStatus.FINISHED)

        # Cargar del repositorio
        experiments = self.repo.load_all_experiments()
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["physics_model"], "MRUA")
        self.assertAlmostEqual(float(experiments[0]["configured_acceleration_m_s2"]), 0.5)
        self.assertGreater(len(self.controller.samples), 2)

        # Exportar a CSV
        csv_text = ExperimentDataExporter.generate_csv_content(
            self.controller.samples,
            self.controller.summary,
            self.track_cfg,
            self.params
        )
        self.assertIn("Modelo fisico: MRUA", csv_text)
        self.assertIn("Aceleracion configurada (a): 0.5000 m/s^2", csv_text)
        self.assertIn("Aceleracion_Instantanea_m_s2", csv_text)


class TestFreeFallSimulationController(unittest.TestCase):
    """Pruebas de ciclo de vida y física para FreeFallSimulationController."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = ExperimentRepository(base_dir=self.temp_dir.name)
        self.root = tk.Tk()
        self.root.withdraw()

        self.params = FreeFallParameters(y0=20.0, v0=0.0, g=9.81)

        self.controller = None
        self.track_view = VerticalTrackView(self.root, max_height=30.0)
        self.plots = MRUAPlotsView(self.root, is_vertical=True)
        self.telemetry = VerticalTelemetryPanel(self.root)
        self.controls = FreeFallControlPanel(
            self.root,
            on_start=lambda: self.controller.start() if self.controller else None,
            on_pause=lambda: self.controller.pause() if self.controller else None,
            on_resume=lambda: self.controller.resume() if self.controller else None,
            on_stop=lambda: self.controller.stop() if self.controller else None,
            on_reset=lambda: self.controller.reset() if self.controller else None,
            on_config_changed=lambda p: self.controller.on_config_changed(p) if self.controller else None
        )

        self.controller = FreeFallSimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.track_view,
                self.plots,
                self.telemetry,
                self.controls
            ),
            repository=self.repo
        )
        self.controller.on_config_changed(self.params)
        self.root.update()

    def tearDown(self):
        if self.controller:
            self.controller._cancel_scheduled_frame()
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_initial_state(self):
        """Inicia en READY con parámetros de caída libre."""
        self.assertEqual(self.controller.status, ExperimentStatus.READY)
        self.assertEqual(self.controller.params.y0, 20.0)
        self.assertEqual(self.controller.params.g, 9.81)

    def test_start_and_ground_impact_auto_finish(self):
        """Una caída libre corta se inicia y al tocar el suelo cambia a FINISHED."""
        # Configurar una caída de muy poca altura y alta gravedad para impacto rápido
        self.controller.on_config_changed(FreeFallParameters(y0=0.5, v0=0.0, g=50.0))
        self.controller.start()
        self.assertEqual(self.controller.status, ExperimentStatus.RUNNING)

        # Dejar que el bucle avance hasta el impacto con el suelo
        max_wait = 2.0
        start_t = time.time()
        while self.controller.status == ExperimentStatus.RUNNING and (time.time() - start_t) < max_wait:
            self.root.update()
            time.sleep(0.02)

        self.assertEqual(self.controller.status, ExperimentStatus.FINISHED)
        self.assertTrue(self.controller.model.current_physics_state.reached_boundary)

        # Verificar persistencia como CAIDA_LIBRE en repositorio
        experiments = self.repo.load_all_experiments()
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["physics_model"], "CAIDA_LIBRE")


if __name__ == "__main__":
    unittest.main()
