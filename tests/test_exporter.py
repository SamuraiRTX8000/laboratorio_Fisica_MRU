"""
Pruebas Unitarias para el Exportador de Datos a CSV.
"""

import unittest
import tempfile
import os
from src.models.physics import TrackConfig, MRUParameters
from src.models.experiment_state import ExperimentControllerModel
from src.data.exporter import ExperimentDataExporter


class TestExporter(unittest.TestCase):
    """Verifica que el archivo CSV generado cumpla los requerimientos de rigor."""

    def test_csv_generation_and_export(self):
        track = TrackConfig(x_min=-10.0, x_max=50.0)
        params = MRUParameters(x0=0.0, velocity=5.0)
        ctrl = ExperimentControllerModel(track, params)
        ctrl.start()
        ctrl.update()
        ctrl.pause()
        ctrl.update()
        ctrl.resume()
        ctrl.update()
        ctrl.stop("Fin de test")

        summary = ctrl.generate_summary()
        samples = ctrl.samples

        csv_text = ExperimentDataExporter.generate_csv_content(samples, summary, track, params)

        # Verificar presencia de metadatos indispensables
        self.assertIn("Posicion inicial (x0): 0.0000 m", csv_text)
        self.assertIn("Velocidad configurada (v): 5.0000 m/s", csv_text)
        self.assertIn("Numero de pausas: 1", csv_text)
        self.assertIn("Muestra,Tiempo_Total_s,Tiempo_Efectivo_s,Posicion_m", csv_text)

        # Probar escritura en archivo temporal
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_export.csv")
            out_path = ExperimentDataExporter.export_to_file(filepath, samples, summary, track, params)
            self.assertTrue(out_path.exists())
            content = out_path.read_text(encoding="utf-8")
            self.assertEqual(content, csv_text)


if __name__ == "__main__":
    unittest.main()
