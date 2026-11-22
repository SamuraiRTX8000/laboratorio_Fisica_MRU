"""
Pruebas de Integración de las Pestañas del Laboratorio Virtual (MainWindow).
"""

import unittest
import tkinter as tk
import tempfile
import time

from src.gui.main_window import MainWindow
from src.models.experiment_state import ExperimentStatus
from src.data.repository import ExperimentRepository


class TestTabsIntegration(unittest.TestCase):
    """Verifica el funcionamiento del cuaderno de pestañas, controladores activos y vistas."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = MainWindow(self.root)

        # Repositorio aislado
        self.repo = ExperimentRepository(base_dir=self.temp_dir.name)
        self.app.repository = self.repo
        self.app.controller.repository = self.repo
        self.app.mrua_controller.repository = self.repo
        self.app.free_fall_controller.repository = self.repo

    def tearDown(self):
        if self.app:
            if self.app.controller:
                self.app.controller._cancel_scheduled_frame()
            if self.app.mrua_controller:
                self.app.mrua_controller._cancel_scheduled_frame()
            if self.app.free_fall_controller:
                self.app.free_fall_controller._cancel_scheduled_frame()
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_notebook_has_four_tabs(self):
        """Verifica que el cuaderno contenga las 4 pestañas requeridas."""
        tabs = self.app.notebook.tabs()
        self.assertEqual(len(tabs), 4)

    def test_switch_tabs_and_active_controller(self):
        """Verifica el cambio de pestañas y que get_active_controller retorne el correcto."""
        # Pestaña 0: MRU
        self.app.switch_to_tab(0)
        self.assertEqual(self.app.get_active_controller(), self.app.controller)

        # Pestaña 1: MRUA
        self.app.switch_to_tab(1)
        self.assertEqual(self.app.get_active_controller(), self.app.mrua_controller)

        # Pestaña 2: Caída Libre
        self.app.switch_to_tab(2)
        self.assertEqual(self.app.get_active_controller(), self.app.free_fall_controller)

        # Pestaña 3: Solucionador
        self.app.switch_to_tab(3)
        self.assertIsNone(self.app.get_active_controller())

    def test_mrua_tab_controls(self):
        """Verifica interacción con botones en la pestaña de MRUA."""
        self.app.switch_to_tab(1)
        ctrl = self.app.mrua_controller

        self.app.mrua_control_panel.btn_start.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        for _ in range(3):
            self.root.update()
            time.sleep(0.01)

        self.app.mrua_control_panel.btn_pause.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.PAUSED)

        self.app.mrua_control_panel.btn_resume.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        self.app.mrua_control_panel.btn_reset.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.READY)

    def test_free_fall_tab_controls(self):
        """Verifica interacción con botones en la pestaña de Caída Libre."""
        self.app.switch_to_tab(2)
        ctrl = self.app.free_fall_controller

        self.app.free_fall_control_panel.btn_start.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        for _ in range(3):
            self.root.update()
            time.sleep(0.01)

        self.app.free_fall_control_panel.btn_pause.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.PAUSED)

        self.app.free_fall_control_panel.btn_resume.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.RUNNING)

        self.app.free_fall_control_panel.btn_reset.invoke()
        self.root.update()
        self.assertEqual(ctrl.status, ExperimentStatus.READY)

    def test_solver_view_integration(self):
        """Verifica que el solucionador esté incrustado y ejecute cálculos desde la GUI."""
        self.app.switch_to_tab(3)
        solver = self.app.solver_view

        # Seleccionar MRUA
        solver.scenario_var.set("MRUA")
        solver._on_scenario_changed()

        # Seleccionar velocidad final
        solver.target_var.set("v")
        solver._on_target_changed()

        # Ingresar valores: v0 = 10, a = 2, t = 5
        solver.inputs_entries["v0"][0].delete(0, tk.END)
        solver.inputs_entries["v0"][0].insert(0, "10")
        solver.inputs_entries["a"][0].delete(0, tk.END)
        solver.inputs_entries["a"][0].insert(0, "2")
        solver.inputs_entries["t"][0].delete(0, tk.END)
        solver.inputs_entries["t"][0].insert(0, "5")

        # Disparar resolución
        solver._on_solve_clicked()
        self.root.update()

        # Verificar resultado en el widget de texto
        text_content = solver.result_text.get("1.0", tk.END)
        self.assertIn("v = 20.0000 m/s", text_content)
        self.assertIn("v = v₀ + a · t", text_content)


if __name__ == "__main__":
    unittest.main()
