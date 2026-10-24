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

    def test_detailed_plot_viewer_features(self):
        """Verifica la inicialización, cambio de vistas y medidas del Visor Detallado."""
        ctrl = self.app.controller
        ctrl.start()
        self.root.update()
        time.sleep(0.03)
        ctrl.pause()
        self.root.update()
        time.sleep(0.03)
        ctrl.resume()
        self.root.update()
        time.sleep(0.03)
        ctrl.stop("Prueba para visor detallado")
        self.root.update()

        # Abrir el Visor Detallado
        viewer = self.app.show_detailed_plot_viewer()
        self.root.update()

        # Probar cambio de modos de visualización
        from src.gui.detailed_plot_viewer import DetailedPlotViewer
        # Buscar el widget hijo DetailedPlotViewer en root
        viewers = [w for w in self.root.winfo_children() if isinstance(w, DetailedPlotViewer)]
        self.assertGreater(len(viewers), 0)
        v = viewers[0]

        # Verificar extracción de puntos notables
        notable = v._extract_notable_points()
        self.assertGreaterEqual(len(notable), 3)  # Inicio, pausa, reanudación/fin

        # Alternar vistas
        for mode in ["Solo Posición x(t)", "Solo Velocidad v(t)", "Dual: x(t) y v(t)"]:
            v.view_mode_var.set(mode)
            v._on_controls_changed()
            self.root.update()

        # Alternar checkboxes de medidas
        v.show_slope_var.set(False)
        v.show_pauses_var.set(False)
        v.show_integral_var.set(False)
        v.show_minor_grid_var.set(False)
        v._on_controls_changed()
        self.root.update()

        v.show_slope_var.set(True)
        v.show_pauses_var.set(True)
        v.show_integral_var.set(True)
        v.show_minor_grid_var.set(True)
        v._on_controls_changed()
        self.root.update()

        v.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
