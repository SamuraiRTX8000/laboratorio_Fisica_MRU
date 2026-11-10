"""
Módulo del Repositorio Persistente de Experimentos Científicos.

Gestiona el almacenamiento local, ciclo de vida de sesiones, registro automático
de experimentos y observaciones sin duplicaciones, persistencia en disco y
generación de manifiestos estructurados.
"""

import os
import json
import csv
import uuid
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set

from .schema import (
    DATASET_SCHEMA_VERSION,
    SOFTWARE_VERSION,
    PHYSICS_MODEL_VERSION,
    PhysicsModel,
    DataSource,
    ExperimentRecord,
    ObservationRecord,
    SessionMetadata,
    EXPERIMENTS_CSV_COLUMNS,
    OBSERVATIONS_CSV_COLUMNS
)
from ..models.experiment_state import ExperimentSummary, MeasurementSample
from ..models.physics import TrackConfig, MRUParameters


class ExperimentRepository:
    """
    Repositorio de persistencia local para sesiones y experimentos de laboratorio.
    Garantiza almacenamiento seguro, acumulación sin sobrescritura y trazabilidad.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            # Directorio por defecto dentro de la carpeta del proyecto
            self.base_dir = Path(__file__).resolve().parent.parent.parent / "data"

        self.sessions_dir = self.base_dir / "sessions"
        self.active_session_file = self.base_dir / "active_session.json"

        # Asegurar estructura de carpetas
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Registro de deduplicación en memoria para evitar guardar el mismo experimento dos veces
        self._persisted_experiment_ids: Set[str] = set()

        # Cargar o inicializar la sesión activa
        self.active_session: SessionMetadata = self._load_or_create_active_session()

    def _generate_session_id(self) -> str:
        """Genera un identificador de sesión único cronológico y estocástico."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rand = uuid.uuid4().hex[:6]
        return f"sess_{ts}_{rand}"

    def _generate_experiment_id(self) -> str:
        """Genera un identificador de experimento único cronológico y estocástico."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rand = uuid.uuid4().hex[:6]
        return f"exp_{ts}_{rand}"

    def _load_or_create_active_session(self) -> SessionMetadata:
        """Carga la sesión activa persistida o crea una nueva si no existe."""
        if self.active_session_file.exists():
            try:
                data = json.loads(self.active_session_file.read_text(encoding="utf-8"))
                sess_id = data.get("session_id")
                sess_dir = self.sessions_dir / f"session_{sess_id}"
                sess_json = sess_dir / "session.json"

                if sess_dir.exists() and sess_json.exists():
                    sess_data = json.loads(sess_json.read_text(encoding="utf-8"))
                    # Recontar experimentos y observaciones reales desde los archivos CSV
                    exp_count, obs_count = self._count_records_in_session(sess_dir)
                    sess = SessionMetadata(
                        session_id=sess_data["session_id"],
                        dataset_schema_version=sess_data.get("dataset_schema_version", DATASET_SCHEMA_VERSION),
                        software_version=sess_data.get("software_version", SOFTWARE_VERSION),
                        session_started_at=sess_data.get("session_started_at", datetime.datetime.now().isoformat()),
                        session_ended_at=sess_data.get("session_ended_at"),
                        experiment_count=exp_count,
                        observation_count=obs_count,
                        notes=sess_data.get("notes", "")
                    )
                    self._update_manifest(sess_dir, sess)
                    return sess
            except Exception:
                # Si hubo algún error leyendo el archivo, se creará una nueva sesión segura
                pass

        return self.create_new_session()

    def create_new_session(self, notes: str = "") -> SessionMetadata:
        """Inicia y persiste una nueva sesión experimental."""
        # Si había una sesión activa previa sin fecha de término, cerrarla
        if hasattr(self, "active_session") and self.active_session:
            self._close_session(self.active_session)

        sess_id = self._generate_session_id()
        now_iso = datetime.datetime.now().isoformat()
        sess_dir = self.sessions_dir / f"session_{sess_id}"
        sess_dir.mkdir(parents=True, exist_ok=True)

        session = SessionMetadata(
            session_id=sess_id,
            dataset_schema_version=DATASET_SCHEMA_VERSION,
            software_version=SOFTWARE_VERSION,
            session_started_at=now_iso,
            session_ended_at=None,
            experiment_count=0,
            observation_count=0,
            notes=notes
        )

        # Guardar session.json
        self._atomic_save_json(sess_dir / "session.json", session.to_dict())

        # Guardar active_session.json
        self._atomic_save_json(self.active_session_file, {"session_id": sess_id, "updated_at": now_iso})

        # Inicializar archivos CSV vacíos con sus cabeceras
        self._ensure_csv_headers(sess_dir / "experiments.csv", EXPERIMENTS_CSV_COLUMNS)
        self._ensure_csv_headers(sess_dir / "observations.csv", OBSERVATIONS_CSV_COLUMNS)

        # Generar manifest inicial
        self._update_manifest(sess_dir, session)

        self.active_session = session
        return session

    def _close_session(self, session: SessionMetadata) -> None:
        """Registra la marca temporal de finalización de una sesión."""
        sess_dir = self.sessions_dir / f"session_{session.session_id}"
        if sess_dir.exists():
            session.session_ended_at = datetime.datetime.now().isoformat()
            self._atomic_save_json(sess_dir / "session.json", session.to_dict())
            self._update_manifest(sess_dir, session)

    def _ensure_csv_headers(self, file_path: Path, columns: List[str]) -> None:
        """Asegura que el archivo CSV exista y tenga la cabecera correspondiente."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)

    def _count_records_in_session(self, sess_dir: Path) -> Tuple[int, int]:
        """Cuenta el número de filas reales (menos cabecera) en los CSVs de la sesión."""
        exp_file = sess_dir / "experiments.csv"
        obs_file = sess_dir / "observations.csv"

        exp_count = 0
        if exp_file.exists():
            with open(exp_file, "r", encoding="utf-8") as f:
                exp_count = max(0, sum(1 for line in f if line.strip()) - 1)

        obs_count = 0
        if obs_file.exists():
            with open(obs_file, "r", encoding="utf-8") as f:
                obs_count = max(0, sum(1 for line in f if line.strip()) - 1)

        return exp_count, obs_count

    def _atomic_save_json(self, file_path: Path, data: dict) -> None:
        """Guarda un archivo JSON de forma atómica para prevenir corrupción de datos."""
        tmp_path = file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(file_path)

    def _update_manifest(self, sess_dir: Path, session: SessionMetadata) -> None:
        """Actualiza el manifiesto de la sesión con metadatos y distribución de clases."""
        exp_count, obs_count = self._count_records_in_session(sess_dir)
        session.experiment_count = exp_count
        session.observation_count = obs_count

        models_dist: Dict[str, int] = {}
        statuses_dist: Dict[str, int] = {}

        exp_file = sess_dir / "experiments.csv"
        if exp_file.exists() and exp_count > 0:
            with open(exp_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    m = row.get("physics_model", "UNKNOWN")
                    s = row.get("experiment_status", "UNKNOWN")
                    models_dist[m] = models_dist.get(m, 0) + 1
                    statuses_dist[s] = statuses_dist.get(s, 0) + 1

        manifest = {
            "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "software_version": SOFTWARE_VERSION,
            "session_id": session.session_id,
            "manifest_generated_at": datetime.datetime.now().isoformat(),
            "session_started_at": session.session_started_at,
            "session_ended_at": session.session_ended_at,
            "experiment_count": exp_count,
            "observation_count": obs_count,
            "physics_models_distribution": models_dist,
            "experiment_statuses_distribution": statuses_dist,
            "notes": session.notes,
            "files": {
                "experiments_csv": "experiments.csv",
                "observations_csv": "observations.csv",
                "session_json": "session.json"
            }
        }
        self._atomic_save_json(sess_dir / "manifest.json", manifest)

    def record_completed_experiment(
        self,
        summary: ExperimentSummary,
        samples: List[MeasurementSample],
        track: TrackConfig,
        params: MRUParameters,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        physics_model: PhysicsModel = PhysicsModel.MRU,
        data_source: DataSource = DataSource.IDEAL_SIMULATION,
        experiment_id_override: Optional[str] = None
    ) -> Optional[ExperimentRecord]:
        """
        Registra un experimento finalizado en la sesión activa.
        Asegura deduplicación estricta y validación previa de integridad física.
        """
        if not samples:
            return None

        # Si ya se usó este experiment_id o no se dio override, generar uno nuevo
        exp_id = experiment_id_override or self._generate_experiment_id()
        if exp_id in self._persisted_experiment_ids:
            # Ya fue guardado, evitar duplicación
            return None

        sess_dir = self.sessions_dir / f"session_{self.active_session.session_id}"
        sess_dir.mkdir(parents=True, exist_ok=True)

        exp_file = sess_dir / "experiments.csv"
        obs_file = sess_dir / "observations.csv"

        # Verificar si exp_id ya existe en experiments.csv
        if exp_file.exists():
            with open(exp_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("experiment_id") == exp_id:
                        self._persisted_experiment_ids.add(exp_id)
                        return None

        # Calcular número secuencial de experimento en la sesión
        current_exp_count, _ = self._count_records_in_session(sess_dir)
        exp_num = current_exp_count + 1

        now_iso = datetime.datetime.now().isoformat()
        start_iso = started_at or now_iso
        comp_iso = completed_at or now_iso

        # 1. Crear el registro maestro de experimento
        v_wall = summary.v_avg_total if summary.t_total > 0 else None
        s_wall = summary.s_avg_total if summary.t_total > 0 else None

        record = ExperimentRecord(
            experiment_id=exp_id,
            session_id=self.active_session.session_id,
            experiment_number=exp_num,
            physics_model=physics_model.value,
            physics_model_version=PHYSICS_MODEL_VERSION,
            software_version=SOFTWARE_VERSION,
            experiment_status="COMPLETED",
            data_source=data_source.value,
            initial_position_m=round(params.x0, 6),
            track_min_m=round(track.x_min, 6),
            track_max_m=round(track.x_max, 6),
            configured_velocity_m_s=round(params.velocity, 6),
            configured_acceleration_m_s2=None,  # No aplica en MRU (campo vacío)
            configured_duration_s=None,
            random_seed=None,
            final_position_m=round(summary.x_final, 6),
            displacement_m=round(summary.displacement, 6),
            distance_traveled_m=round(summary.distance, 6),
            active_duration_s=round(summary.t_eff, 6),
            wall_duration_s=round(summary.t_total, 6),
            pause_count=summary.pause_count,
            total_pause_duration_s=round(summary.total_pause_duration, 6),
            mean_velocity_active_m_s=round(summary.v_avg_eff, 6),
            mean_speed_active_m_s=round(summary.s_avg_eff, 6),
            mean_velocity_wall_m_s=round(v_wall, 6) if v_wall is not None else None,
            mean_speed_wall_m_s=round(s_wall, 6) if s_wall is not None else None,
            termination_reason=summary.termination_reason,
            started_at=start_iso,
            completed_at=comp_iso
        )

        # Validación de consistencia física previa a la escritura
        self._validate_physical_record(record, samples)

        # 2. Convertir muestras a ObservationRecords
        observation_records: List[ObservationRecord] = []
        for idx, s in enumerate(samples):
            obs = ObservationRecord(
                experiment_id=exp_id,
                session_id=self.active_session.session_id,
                sample_index=idx,
                wall_time_s=round(s.t_total, 6),
                active_time_s=round(s.t_eff, 6),
                position_m=round(s.position, 6),
                displacement_m=round(s.displacement, 6),
                distance_traveled_m=round(s.distance, 6),
                velocity_m_s=round(s.velocity, 6),
                speed_m_s=round(s.speed, 6),
                simulation_state=s.status,
                physics_model=physics_model.value,
                acceleration_m_s2=None  # Campo ausente para MRU
            )
            observation_records.append(obs)

        # 3. Escritura segura en experiments.csv
        self._ensure_csv_headers(exp_file, EXPERIMENTS_CSV_COLUMNS)
        with open(exp_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EXPERIMENTS_CSV_COLUMNS)
            writer.writerow(record.to_csv_dict())

        # 4. Escritura segura en observations.csv
        self._ensure_csv_headers(obs_file, OBSERVATIONS_CSV_COLUMNS)
        with open(obs_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OBSERVATIONS_CSV_COLUMNS)
            for obs in observation_records:
                writer.writerow(obs.to_csv_dict())

        # 5. Actualizar estado y manifiesto
        self._persisted_experiment_ids.add(exp_id)
        self._update_manifest(sess_dir, self.active_session)

        return record

    def _validate_physical_record(self, record: ExperimentRecord, samples: List[MeasurementSample]) -> None:
        """
        Valida que los datos sean físicamente coherentes antes de guardarlos.
        Lanza ValueError si se detectan violaciones físicas graves.
        """
        # Distancia debe ser no negativa
        if record.distance_traveled_m < -1e-6:
            raise ValueError(f"Distancia recorrida no puede ser negativa: {record.distance_traveled_m}")

        # Tiempos deben ser no negativos
        if record.active_duration_s < -1e-6 or record.wall_duration_s < -1e-6:
            raise ValueError(f"Tiempos no pueden ser negativos (t_eff={record.active_duration_s}, t_total={record.wall_duration_s})")

        # t_wall debe ser >= t_eff (dentro de tolerancia numérica)
        if record.wall_duration_s < (record.active_duration_s - 0.05):
            raise ValueError(f"Tiempo total ({record.wall_duration_s}s) no puede ser menor que tiempo activo ({record.active_duration_s}s)")

        # Desplazamiento debe coincidir con final_position - initial_position
        expected_disp = record.final_position_m - record.initial_position_m
        if abs(record.displacement_m - expected_disp) > 0.05:
            raise ValueError(f"Incoherencia en desplazamiento: disp={record.displacement_m}, pero x_f - x_0 = {expected_disp}")

        # Orden temporal de las muestras
        for i in range(1, len(samples)):
            if samples[i].t_total < samples[i - 1].t_total - 1e-6:
                raise ValueError(f"Inversión temporal detectada en muestra #{i}")

        # Coherencia con el modelo cinemático MRU: Delta x = v * t_eff
        if record.physics_model == PhysicsModel.MRU.value and record.active_duration_s > 0.05:
            expected_mru_disp = record.configured_velocity_m_s * record.active_duration_s
            if abs(record.displacement_m - expected_mru_disp) > 0.15:
                raise ValueError(
                    f"Incoherencia física con MRU: desplazamiento {record.displacement_m:.4f}m "
                    f"difiere del analítico {expected_mru_disp:.4f}m (v={record.configured_velocity_m_s}, t_eff={record.active_duration_s})"
                )

    def switch_to_session(self, session_id: str) -> SessionMetadata:
        """Cambia la sesión activa a una sesión previamente existente."""
        sess_dir = self.sessions_dir / f"session_{session_id}"
        sess_json = sess_dir / "session.json"
        if not (sess_dir.exists() and sess_json.exists()):
            raise FileNotFoundError(f"La sesión {session_id} no existe.")

        if hasattr(self, "active_session") and self.active_session and self.active_session.session_id != session_id:
            self._close_session(self.active_session)

        sess_data = json.loads(sess_json.read_text(encoding="utf-8"))
        exp_count, obs_count = self._count_records_in_session(sess_dir)
        session = SessionMetadata(
            session_id=sess_data["session_id"],
            dataset_schema_version=sess_data.get("dataset_schema_version", DATASET_SCHEMA_VERSION),
            software_version=sess_data.get("software_version", SOFTWARE_VERSION),
            session_started_at=sess_data.get("session_started_at", datetime.datetime.now().isoformat()),
            session_ended_at=sess_data.get("session_ended_at"),
            experiment_count=exp_count,
            observation_count=obs_count,
            notes=sess_data.get("notes", "")
        )
        self.active_session = session
        now_iso = datetime.datetime.now().isoformat()
        self._atomic_save_json(self.active_session_file, {"session_id": session_id, "updated_at": now_iso})
        self._update_manifest(sess_dir, session)
        return session

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retorna los metadatos y manifiesto de una sesión almacenada."""
        sess_dir = self.sessions_dir / f"session_{session_id}"
        sess_json = sess_dir / "session.json"
        manifest_json = sess_dir / "manifest.json"
        if not sess_dir.exists():
            return None
        res: Dict[str, Any] = {"session_id": session_id}
        if sess_json.exists():
            res["session"] = json.loads(sess_json.read_text(encoding="utf-8"))
        if manifest_json.exists():
            res["manifest"] = json.loads(manifest_json.read_text(encoding="utf-8"))
        exp_count, obs_count = self._count_records_in_session(sess_dir)
        res["experiment_count"] = exp_count
        res["observation_count"] = obs_count
        return res

    def list_all_sessions(self) -> List[str]:
        """Retorna la lista de identificadores de todas las sesiones almacenadas."""
        if not self.sessions_dir.exists():
            return []
        sessions = []
        for p in sorted(self.sessions_dir.glob("session_*")):
            if p.is_dir() and (p / "session.json").exists():
                sess_id = p.name.replace("session_", "")
                sessions.append(sess_id)
        return sessions

    def load_session_experiments(self, session_id: str) -> List[Dict[str, str]]:
        """Carga todas las filas de experiments.csv de una sesión dada."""
        sess_dir = self.sessions_dir / f"session_{session_id}"
        exp_file = sess_dir / "experiments.csv"
        if not exp_file.exists():
            return []
        with open(exp_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def load_session_observations(self, session_id: str) -> List[Dict[str, str]]:
        """Carga todas las filas de observations.csv de una sesión dada."""
        sess_dir = self.sessions_dir / f"session_{session_id}"
        obs_file = sess_dir / "observations.csv"
        if not obs_file.exists():
            return []
        with open(obs_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def load_all_experiments(self) -> List[Dict[str, str]]:
        """Carga todos los experimentos de todas las sesiones registradas."""
        all_exps = []
        for sess_id in self.list_all_sessions():
            all_exps.extend(self.load_session_experiments(sess_id))
        return all_exps

    def load_all_observations(self) -> List[Dict[str, str]]:
        """Carga todas las observaciones de todas las sesiones registradas."""
        all_obs = []
        for sess_id in self.list_all_sessions():
            all_obs.extend(self.load_session_observations(sess_id))
        return all_obs
