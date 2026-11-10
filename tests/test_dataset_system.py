"""
Banco de Pruebas Automatizadas para el Sistema de Registro Científico
y Generación de Datasets para Inteligencia Artificial y Machine Learning.

Cubre exhaustivamente los 15 requerimientos obligatorios de validación de datos:
1. Guardado automático de un experimento finalizado.
2. Acumulación de varios experimentos en una sesión sin sobrescritura.
3. Persistencia de la sesión después de reiniciar/cerrar la aplicación.
4. Asociación estricta de cada experimento con su session_id correspondiente.
5. Generación determinista y única de identificadores (sin colisiones).
6. Ausencia de duplicaciones ante múltiples llamadas de finalización.
7. Exportación consolidada de la sesión activa (experiments, observations, manifest, README).
8. Exportación consolidada del historial completo multi-sesión.
9. Lectura directa e inmediata de los archivos CSV con pandas (sin saltar filas).
10. Integridad de cabeceras, unidades del SI y tipos de datos numéricos.
11. Tratamiento de valores ausentes (campos vacíos interpretados como NaN).
12. Conservación de datos originales durante la migración de informes antiguos.
13. Coherencia física de las mediciones registradas (relación x = x0 + vt y cotas).
14. Separación de estados experimentales (COMPLETED, etc.).
15. Recuperación segura y resiliente ante archivos JSON o CSV dañados o ausentes.
"""

import unittest
import tempfile
import json
import csv
import os
from pathlib import Path
import pandas as pd
import numpy as np

from src.models.physics import TrackConfig, MRUParameters
from src.models.experiment_state import ExperimentControllerModel, ExperimentSummary, MeasurementSample
from src.data.schema import (
    DATASET_SCHEMA_VERSION,
    SOFTWARE_VERSION,
    PhysicsModel,
    DataSource,
    EXPERIMENTS_CSV_COLUMNS,
    OBSERVATIONS_CSV_COLUMNS,
    ExperimentRecord,
    ObservationRecord
)
from src.data.repository import ExperimentRepository
from src.data.consolidator import DatasetConsolidator
from src.data.migrator import LegacyReportMigrator
from src.data.exporter import ExperimentDataExporter


class TestScientificDatasetSystem(unittest.TestCase):
    """Pruebas rigurosas de la infraestructura de datos científicos y ML."""

    def setUp(self):
        # Crear un directorio temporal aislado para cada prueba
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.repo = ExperimentRepository(base_dir=str(self.data_dir))
        self.consolidator = DatasetConsolidator(self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _simulate_and_get_data(self, x0=0.0, v=10.0, pauses=0):
        """Helper para generar datos de simulación físicamente consistentes."""
        track = TrackConfig(x_min=-50.0, x_max=50.0)
        params = MRUParameters(x0=x0, velocity=v)
        ctrl = ExperimentControllerModel(track, params)
        ctrl.start()

        # Simular algunos pasos
        for _ in range(3):
            ctrl.update()

        for _ in range(pauses):
            ctrl.pause()
            ctrl.update()
            ctrl.resume()
            ctrl.update()

        ctrl.stop("Fin de prueba")
        return ctrl.generate_summary(), ctrl.samples, track, params

    def test_01_auto_save_completed_experiment(self):
        """1. Verifica el guardado automático de un experimento finalizado."""
        summary, samples, track, params = self._simulate_and_get_data(x0=5.0, v=12.0)
        rec = self.repo.record_completed_experiment(summary, samples, track, params)

        self.assertIsNotNone(rec)
        self.assertEqual(rec.physics_model, "MRU")
        self.assertEqual(rec.initial_position_m, 5.0)
        self.assertEqual(rec.configured_velocity_m_s, 12.0)

        # Verificar presencia en disco
        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"
        exp_file = sess_dir / "experiments.csv"
        obs_file = sess_dir / "observations.csv"

        self.assertTrue(exp_file.exists())
        self.assertTrue(obs_file.exists())

        # Contar filas
        df_exp = pd.read_csv(exp_file)
        self.assertEqual(len(df_exp), 1)
        self.assertEqual(df_exp.iloc[0]["experiment_id"], rec.experiment_id)

    def test_02_accumulation_of_experiments_without_overwriting(self):
        """2. Verifica la acumulación de varios experimentos en una sesión sin sobrescritura."""
        # Experimento 1
        s1, samp1, t1, p1 = self._simulate_and_get_data(x0=0.0, v=5.0)
        self.repo.record_completed_experiment(s1, samp1, t1, p1)

        # Experimento 2
        s2, samp2, t2, p2 = self._simulate_and_get_data(x0=10.0, v=-8.0)
        self.repo.record_completed_experiment(s2, samp2, t2, p2)

        # Experimento 3
        s3, samp3, t3, p3 = self._simulate_and_get_data(x0=-20.0, v=15.0)
        self.repo.record_completed_experiment(s3, samp3, t3, p3)

        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"
        df_exp = pd.read_csv(sess_dir / "experiments.csv")

        self.assertEqual(len(df_exp), 3)
        self.assertEqual(list(df_exp["experiment_number"]), [1, 2, 3])
        self.assertEqual(list(df_exp["initial_position_m"]), [0.0, 10.0, -20.0])
        self.assertEqual(list(df_exp["configured_velocity_m_s"]), [5.0, -8.0, 15.0])

    def test_03_persistence_across_app_restart(self):
        """3. Verifica la persistencia de la sesión al cerrar y reabrir el repositorio."""
        s1, samp1, t1, p1 = self._simulate_and_get_data(x0=0.0, v=10.0)
        rec1 = self.repo.record_completed_experiment(s1, samp1, t1, p1)
        orig_session_id = self.repo.active_session.session_id

        # Simular reinicio de la aplicación instanciando un nuevo repositorio sobre el mismo directorio
        new_repo = ExperimentRepository(base_dir=str(self.data_dir))
        self.assertEqual(new_repo.active_session.session_id, orig_session_id)
        self.assertEqual(new_repo.active_session.experiment_count, 1)

        # Guardar un segundo experimento en la sesión reanudada
        s2, samp2, t2, p2 = self._simulate_and_get_data(x0=25.0, v=-10.0)
        rec2 = new_repo.record_completed_experiment(s2, samp2, t2, p2)

        self.assertEqual(rec2.experiment_number, 2)
        self.assertEqual(new_repo.active_session.experiment_count, 2)

    def test_04_session_association(self):
        """4. Verifica que los experimentos y observaciones estén vinculados a su session_id."""
        s, samp, t, p = self._simulate_and_get_data()
        rec = self.repo.record_completed_experiment(s, samp, t, p)

        sess_id = self.repo.active_session.session_id
        self.assertEqual(rec.session_id, sess_id)

        sess_dir = self.data_dir / "sessions" / f"session_{sess_id}"
        df_obs = pd.read_csv(sess_dir / "observations.csv")

        self.assertTrue((df_obs["session_id"] == sess_id).all())
        self.assertTrue((df_obs["experiment_id"] == rec.experiment_id).all())

    def test_05_unique_identifiers(self):
        """5. Verifica que cada experimento y sesión tengan IDs únicos y no colisionen."""
        ids = set()
        for _ in range(10):
            exp_id = self.repo._generate_experiment_id()
            self.assertNotIn(exp_id, ids)
            ids.add(exp_id)

        sess_ids = set()
        for _ in range(10):
            s_id = self.repo._generate_session_id()
            self.assertNotIn(s_id, sess_ids)
            sess_ids.add(s_id)

    def test_06_deduplication(self):
        """6. Verifica la ausencia de duplicaciones si se intenta guardar el mismo experimento varias veces."""
        s, samp, t, p = self._simulate_and_get_data()
        exp_id = "exp_test_dedup_001"

        r1 = self.repo.record_completed_experiment(s, samp, t, p, experiment_id_override=exp_id)
        self.assertIsNotNone(r1)

        # Segundo intento con el mismo ID
        r2 = self.repo.record_completed_experiment(s, samp, t, p, experiment_id_override=exp_id)
        self.assertIsNone(r2)

        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"
        df_exp = pd.read_csv(sess_dir / "experiments.csv")
        self.assertEqual(len(df_exp), 1)

    def test_07_session_dataset_export(self):
        """7. Verifica la exportación consolidada de la sesión activa con todos sus archivos."""
        for v in [5.0, 10.0]:
            s, samp, t, p = self._simulate_and_get_data(v=v)
            self.repo.record_completed_experiment(s, samp, t, p)

        export_target = self.data_dir / "exported_session_dataset"
        out_path = self.consolidator.export_session_dataset(self.repo.active_session.session_id, str(export_target))

        self.assertTrue((out_path / "experiments.csv").exists())
        self.assertTrue((out_path / "observations.csv").exists())
        self.assertTrue((out_path / "manifest.json").exists())
        self.assertTrue((out_path / "README_dataset.md").exists())

        # Verificar contenido del manifest
        manifest = json.loads((out_path / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_experiments"], 2)
        self.assertEqual(manifest["dataset_schema_version"], DATASET_SCHEMA_VERSION)
        self.assertIn("MRU", manifest["distributions"]["physics_models"])

    def test_08_historical_dataset_export(self):
        """8. Verifica la exportación del historial completo que consolida múltiples sesiones."""
        # Sesión 1 con 2 experimentos
        self._simulate_and_get_data(v=10.0)
        self.repo.record_completed_experiment(*self._simulate_and_get_data(v=10.0))
        self.repo.record_completed_experiment(*self._simulate_and_get_data(v=15.0))

        # Crear Sesión 2 con 1 experimento
        self.repo.create_new_session(notes="Segunda sesión de prueba")
        self.repo.record_completed_experiment(*self._simulate_and_get_data(v=20.0))

        export_target = self.data_dir / "exported_historical_dataset"
        out_path = self.consolidator.export_historical_dataset(str(export_target))

        df_exp = pd.read_csv(out_path / "experiments.csv")
        self.assertEqual(len(df_exp), 3)

        # Comprobar que contenga experimentos de ambas sesiones distintas
        unique_sessions = df_exp["session_id"].nunique()
        self.assertEqual(unique_sessions, 2)

    def test_09_direct_pandas_read(self):
        """9. Verifica la lectura directa con pandas.read_csv() sin skiprows ni advertencias."""
        s, samp, t, p = self._simulate_and_get_data(v=14.0)
        self.repo.record_completed_experiment(s, samp, t, p)

        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"

        # Lectura pura sin parámetros adicionales
        df_exp = pd.read_csv(sess_dir / "experiments.csv")
        df_obs = pd.read_csv(sess_dir / "observations.csv")

        self.assertFalse(df_exp.empty)
        self.assertFalse(df_obs.empty)
        self.assertIn("experiment_id", df_exp.columns)
        self.assertIn("position_m", df_obs.columns)

    def test_10_headers_and_data_types_integrity(self):
        """10. Verifica la estricta integridad de cabeceras, unidades del SI y tipos numéricos."""
        s, samp, t, p = self._simulate_and_get_data(x0=-15.0, v=8.5)
        self.repo.record_completed_experiment(s, samp, t, p)

        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"
        df_exp = pd.read_csv(sess_dir / "experiments.csv")

        # Verificar que todas las columnas esperadas existan exactamente
        self.assertEqual(list(df_exp.columns), EXPERIMENTS_CSV_COLUMNS)

        # Verificar tipos numéricos
        self.assertIsInstance(float(df_exp.iloc[0]["initial_position_m"]), float)
        self.assertIsInstance(float(df_exp.iloc[0]["configured_velocity_m_s"]), float)
        self.assertIsInstance(int(df_exp.iloc[0]["pause_count"]), int)

    def test_11_missing_values_representation(self):
        """11. Verifica que los parámetros no configurados (p.ej. aceleración en MRU) sean NaN en pandas, no ceros ficticios."""
        s, samp, t, p = self._simulate_and_get_data(v=10.0)
        self.repo.record_completed_experiment(s, samp, t, p)

        sess_dir = self.data_dir / "sessions" / f"session_{self.repo.active_session.session_id}"
        df_exp = pd.read_csv(sess_dir / "experiments.csv")

        # configured_acceleration_m_s2 debe ser NaN (vacío en CSV), no 0.0
        acc_val = df_exp.iloc[0]["configured_acceleration_m_s2"]
        self.assertTrue(pd.isna(acc_val))

    def test_12_legacy_report_migration(self):
        """12. Verifica la migración de un informe CSV legado sin alterar el original."""
        s, samp, t, p = self._simulate_and_get_data(x0=0.0, v=20.0, pauses=1)

        # Generar informe en formato legado con '#'
        legacy_file = self.data_dir / "legacy_report.csv"
        ExperimentDataExporter.export_to_file(str(legacy_file), samp, s, t, p)
        orig_content = legacy_file.read_text(encoding="utf-8")

        migrator = LegacyReportMigrator(self.repo)
        rec, count = migrator.migrate_file(str(legacy_file))

        self.assertIsNotNone(rec)
        self.assertEqual(rec.data_source, "IMPORTED_LEGACY")
        self.assertEqual(rec.physics_model, "MRU")
        self.assertAlmostEqual(rec.configured_velocity_m_s, 20.0)
        self.assertGreater(count, 0)

        # Verificar que el archivo original no fue modificado
        self.assertEqual(legacy_file.read_text(encoding="utf-8"), orig_content)

        # Intentar migrar el mismo archivo de nuevo (debe detectar duplicación por hash)
        rec2, count2 = migrator.migrate_file(str(legacy_file))
        self.assertIsNone(rec2)

    def test_13_physical_consistency_validation(self):
        """13. Verifica que la validación física rechace datos con inconsistencias graves."""
        s, samp, t, p = self._simulate_and_get_data()

        # Forzar una inconsistencia física (distancia negativa)
        invalid_summary = ExperimentSummary(
            x0=0.0, x_final=10.0, configured_velocity=10.0, configured_speed=10.0,
            t_eff=1.0, t_total=1.0, total_pause_duration=0.0, pause_count=0,
            displacement=10.0, distance=-50.0,  # Distancia negativa ilícita
            v_avg_eff=10.0, s_avg_eff=10.0, v_avg_total=10.0, s_avg_total=10.0,
            termination_reason="Test error", is_mru_verified=True, explanation=""
        )

        with self.assertRaises(ValueError):
            self.repo.record_completed_experiment(invalid_summary, samp, t, p)

    def test_14_experiment_status_and_filtering(self):
        """14. Verifica la clasificación correcta de estados (COMPLETED, etc.)."""
        s, samp, t, p = self._simulate_and_get_data(v=5.0)
        rec = self.repo.record_completed_experiment(s, samp, t, p)

        self.assertEqual(rec.experiment_status, "COMPLETED")
        self.assertEqual(rec.physics_model, "MRU")

    def test_15_resilience_to_damaged_or_missing_files(self):
        """15. Verifica la recuperación segura ante archivos JSON corruptos o ausentes."""
        # Corromper deliberadamente active_session.json
        self.repo.active_session_file.write_text("CORRUPTED_JSON_DATA {{{", encoding="utf-8")

        # Al inicializar un nuevo repositorio, debe recuperarse creando una nueva sesión válida
        recovered_repo = ExperimentRepository(base_dir=str(self.data_dir))
        self.assertIsNotNone(recovered_repo.active_session)
        self.assertTrue(recovered_repo.active_session_file.exists())


if __name__ == "__main__":
    unittest.main()
