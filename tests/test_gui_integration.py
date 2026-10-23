"""
Pruebas de Integración de la Interfaz Gráfica y el Controlador de Simulación.
"""

import unittest
import tkinter as tk
import time
from src.gui.main_window import MainWindow
from src.models.experiment_state import ExperimentStatus
from src.models.physics import TrackConfig, MRUParameters


class TestGUIIntegration(unittest.TestCase):
    """Verifica la correcta integración de todos los componentes de la interfaz."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Ocultar para pruebas sin parpadeo
        self.app = MainWindow(self.root)

    def tearDown(self):
        if self.app and self.app.controller:
            self.app.controller._cancel_scheduled_frame()
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self.root.destroy()

    def test_initial_gui_state(self):
        """Verifica que los componentes se inicialicen en estado READY."""
        ctrl = self.app.controller
        self.assertIsNotNone(ctrl)
        self.assertEqual(ctrl.status, ExperimentStatus.READY)
        self.assertEqual(str(self.app.control_panel.btn_start.cget("state")), "normal")
        self.assertEqual(str(self.app.control_panel.btn_pause.cget("state")), "disabled")

    def test_start_pause_resume_reset_cycle(self):
        """Ejecuta un ciclo completo de interacción en la interfaz."""
        ctrl = self.app.controller

        # 1. Iniciar
        self.app.control_panel.btn_start.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        # 2. Dejar avanzar unos pasos de animación
        for _ in range(5):
            self.root.update()
            time.sleep(0.01)

        # 3. Pausar
        self.app.control_panel.btn_pause.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.PAUSED)
        self.assertEqual(ctrl.model.pause_count, 1)

        # 4. Continuar
        self.app.control_panel.btn_resume.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        for _ in range(5):
            self.root.update()
            time.sleep(0.01)

        # 5. Finalizar
        self.app.control_panel.btn_stop.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.FINISHED)

        # 6. Reiniciar
        self.app.control_panel.btn_reset.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.READY)

    def test_preset_selection(self):
        """Verifica que cambiar de preset actualice el modelo y la vista."""
        self.app.control_panel.preset_var.set("3. Sentido negativo hacia la izquierda (x0=+40, v=-12 m/s)")
        self.app.control_panel._on_preset_selected()
        self.root.update()

        self.assertAlmostEqual(self.app.controller.params.x0, 40.0)
        self.assertAlmostEqual(self.app.controller.params.velocity, -12.0)
        self.assertEqual(self.app.controller.params.direction_sign, -1)

    def test_dialog_creations(self):
        """Verifica que los diálogos de informe y teoría se creen sin excepciones."""
        # Diálogo de teoría
        theory_dlg = self.app.show_theory_dialog
        theory_dlg()
        self.root.update()

        # Simular experimento y abrir resumen
        self.app.controller.start()
        self.root.update()
        time.sleep(0.02)
        self.app.controller.stop("Test finalizado")
        self.root.update()

        summary_dlg = self.app.show_summary_dialog
        summary_dlg()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
