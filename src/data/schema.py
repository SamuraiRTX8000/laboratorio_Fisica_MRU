"""
Módulo de Definición de Esquemas de Datos para Aprendizaje Automático y Registro Científico.

Define las enumeraciones de modelos físicos, fuentes de datos, metadatos de sesión
y estructuras de registros tabulares para `experiments.csv` y `observations.csv`.
Diseñado para consumo directo por bibliotecas científicas (pandas, NumPy, scikit-learn).
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import datetime


DATASET_SCHEMA_VERSION = "1.0.0"
SOFTWARE_VERSION = "1.0.0"
PHYSICS_MODEL_VERSION = "1.0.0"


class PhysicsModel(str, Enum):
    """
    Catálogo extensible de modelos físicos cinemáticos.
    Permite etiquetado supervisado de verdad fundamental (ground truth).
    """
    MRU = "MRU"                                     # Movimiento Rectilíneo Uniforme
    MRUA = "MRUA"                                   # Movimiento Rectilíneo Uniformemente Acelerado
    MRUR = "MRUR"                                   # Movimiento Rectilíneo Uniformemente Retardado
    CAIDA_LIBRE = "CAIDA_LIBRE"                     # Caída Libre bajo gravedad constante
    MOVIMIENTO_PERSONALIZADO = "MOVIMIENTO_PERSONALIZADO"  # Modelo cinemático definido por usuario
    UNKNOWN = "UNKNOWN"                             # Modelo desconocido o no identificado

    @classmethod
    def from_string(cls, val: str) -> "PhysicsModel":
        """Convierte una cadena a PhysicsModel con fallback seguro a UNKNOWN."""
        if not val:
            return cls.UNKNOWN
        cleaned = val.strip().upper()
        for member in cls:
            if member.value == cleaned or member.name == cleaned:
                return member
        return cls.UNKNOWN


class DataSource(str, Enum):
    """Procedencia de los datos para trazabilidad y prevención de sesgos en ML."""
    IDEAL_SIMULATION = "IDEAL_SIMULATION"             # Simulación analítica determinista
    SIMULATION_WITH_NOISE = "SIMULATION_WITH_NOISE"   # Simulación con perturbaciones sintéticas
    REAL_MEASUREMENT = "REAL_MEASUREMENT"             # Medición empírica experimental
    IMPORTED_LEGACY = "IMPORTED_LEGACY"               # Migrado desde informes de versiones anteriores


@dataclass
class ExperimentRecord:
    """
    Registro maestro de un experimento cinemático finalizado (Fila en experiments.csv).
    Todos los campos numéricos utilizan unidades explícitas del Sistema Internacional (SI).
    Los campos ausentes o no aplicables al modelo deben ser None (se serializan como vacíos).
    """
    # Identificación y clasificación
    experiment_id: str
    session_id: str
    experiment_number: int
    physics_model: str
    physics_model_version: str
    software_version: str
    experiment_status: str
    data_source: str

    # Configuración del escenario
    initial_position_m: float
    track_min_m: float
    track_max_m: float
    configured_velocity_m_s: float
    configured_acceleration_m_s2: Optional[float] = None
    configured_duration_s: Optional[float] = None
    random_seed: Optional[int] = None

    # Resultados y métricas acumuladas
    final_position_m: float = 0.0
    displacement_m: float = 0.0
    distance_traveled_m: float = 0.0
    active_duration_s: float = 0.0
    wall_duration_s: float = 0.0
    pause_count: int = 0
    total_pause_duration_s: float = 0.0
    mean_velocity_active_m_s: float = 0.0
    mean_speed_active_m_s: float = 0.0
    mean_velocity_wall_m_s: Optional[float] = None
    mean_speed_wall_m_s: Optional[float] = None
    termination_reason: str = ""

    # Marcas temporales (ISO 8601)
    started_at: str = ""
    completed_at: str = ""

    def to_csv_dict(self) -> Dict[str, Any]:
        """Convierte el registro a un diccionario de valores listos para CSV (None -> '')."""
        raw = asdict(self)
        formatted = {}
        for k, v in raw.items():
            if v is None:
                formatted[k] = ""
            elif isinstance(v, float):
                formatted[k] = f"{v:.6g}"
            else:
                formatted[k] = str(v)
        return formatted


@dataclass
class ObservationRecord:
    """
    Muestra temporal de telemetría de un experimento (Fila en observations.csv).
    Permite análisis de series de tiempo, regresión de parámetros y detección de anomalías.
    """
    experiment_id: str
    session_id: str
    sample_index: int
    wall_time_s: float
    active_time_s: float
    position_m: float
    displacement_m: float
    distance_traveled_m: float
    velocity_m_s: float
    speed_m_s: float
    simulation_state: str
    physics_model: str
    acceleration_m_s2: Optional[float] = None

    def to_csv_dict(self) -> Dict[str, Any]:
        """Convierte la muestra a formato CSV limpio."""
        raw = asdict(self)
        formatted = {}
        for k, v in raw.items():
            if v is None:
                formatted[k] = ""
            elif isinstance(v, float):
                formatted[k] = f"{v:.6g}"
            else:
                formatted[k] = str(v)
        return formatted


@dataclass
class SessionMetadata:
    """Metadatos de sesión persistidos en session.json."""
    session_id: str
    dataset_schema_version: str
    software_version: str
    session_started_at: str
    session_ended_at: Optional[str]
    experiment_count: int
    observation_count: int
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Lista ordenada de columnas para asegurar consistencia estricta en pandas
EXPERIMENTS_CSV_COLUMNS = [
    "experiment_id",
    "session_id",
    "experiment_number",
    "physics_model",
    "physics_model_version",
    "software_version",
    "experiment_status",
    "data_source",
    "initial_position_m",
    "track_min_m",
    "track_max_m",
    "configured_velocity_m_s",
    "configured_acceleration_m_s2",
    "configured_duration_s",
    "random_seed",
    "final_position_m",
    "displacement_m",
    "distance_traveled_m",
    "active_duration_s",
    "wall_duration_s",
    "pause_count",
    "total_pause_duration_s",
    "mean_velocity_active_m_s",
    "mean_speed_active_m_s",
    "mean_velocity_wall_m_s",
    "mean_speed_wall_m_s",
    "termination_reason",
    "started_at",
    "completed_at"
]

OBSERVATIONS_CSV_COLUMNS = [
    "experiment_id",
    "session_id",
    "sample_index",
    "wall_time_s",
    "active_time_s",
    "position_m",
    "displacement_m",
    "distance_traveled_m",
    "velocity_m_s",
    "speed_m_s",
    "acceleration_m_s2",
    "simulation_state",
    "physics_model"
]
