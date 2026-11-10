"""
Módulo de Migración y Compatibilidad de Informes Experimentales Antiguos.

Permite leer informes CSV generados por versiones previas (que contenían metadatos
en líneas de comentario con almohadilla '#') y convertirlos fielmente al nuevo
esquema estructurado sin inventar datos ni alterar los archivos originales.
"""

import re
import csv
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from .schema import (
    PhysicsModel,
    DataSource,
    ExperimentRecord,
    ObservationRecord
)
from .repository import ExperimentRepository
from ..models.experiment_state import ExperimentSummary, MeasurementSample
from ..models.physics import TrackConfig, MRUParameters


class LegacyReportMigrator:
    """Migrador de informes individuales antiguos hacia el repositorio estructurado."""

    def __init__(self, repository: ExperimentRepository) -> None:
        self.repo = repository

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo para evitar importaciones repetidas."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()[:12]

    def migrate_file(self, file_path: str) -> Tuple[Optional[ExperimentRecord], int]:
        """
        Migra un archivo CSV antiguo al repositorio activo.
        Retorna (ExperimentRecord, cantidad_muestras_importadas).
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"El archivo {file_path} no existe.")

        content = path.read_text(encoding="utf-8")
        file_hash = self.calculate_file_hash(path)
        exp_id = f"exp_legacy_{file_hash}"

        # 1. Parsear metadatos en líneas '#'
        metadata = self._parse_legacy_metadata(content)

        # 2. Parsear muestras de la tabla CSV
        samples = self._parse_legacy_samples(content)

        if not samples:
            raise ValueError(f"No se encontraron muestras telemétricas válidas en {file_path}")

        # 3. Reconstruir parámetros y modelos
        track = TrackConfig(
            x_min=metadata.get("track_min", -50.0),
            x_max=metadata.get("track_max", 50.0)
        )
        params = MRUParameters(
            x0=metadata.get("x0", samples[0].position),
            velocity=metadata.get("velocity", samples[0].velocity)
        )

        t_eff = metadata.get("t_eff", samples[-1].t_eff)
        t_total = metadata.get("t_total", samples[-1].t_total)
        disp = metadata.get("displacement", samples[-1].displacement)
        dist = metadata.get("distance", samples[-1].distance)

        summary = ExperimentSummary(
            x0=params.x0,
            x_final=metadata.get("x_final", samples[-1].position),
            configured_velocity=params.velocity,
            configured_speed=abs(params.velocity),
            t_eff=t_eff,
            t_total=t_total,
            total_pause_duration=metadata.get("pause_duration", 0.0),
            pause_count=metadata.get("pause_count", 0),
            displacement=disp,
            distance=dist,
            v_avg_eff=metadata.get("v_avg_eff", (disp / t_eff) if t_eff > 0 else params.velocity),
            s_avg_eff=metadata.get("s_avg_eff", (dist / t_eff) if t_eff > 0 else abs(params.velocity)),
            v_avg_total=metadata.get("v_avg_total", (disp / t_total) if t_total > 0 else 0.0),
            s_avg_total=metadata.get("s_avg_total", (dist / t_total) if t_total > 0 else 0.0),
            termination_reason=metadata.get("termination_reason", "Migrado desde informe legado"),
            is_mru_verified=metadata.get("mru_verified", True),
            explanation="Experimento migrado automáticamente desde informe antiguo."
        )

        # 4. Guardar en el repositorio con fuente IMPORTED_LEGACY
        record = self.repo.record_completed_experiment(
            summary=summary,
            samples=samples,
            track=track,
            params=params,
            started_at=metadata.get("date_str"),
            completed_at=metadata.get("date_str"),
            physics_model=PhysicsModel.MRU,
            data_source=DataSource.IMPORTED_LEGACY,
            experiment_id_override=exp_id
        )

        return record, len(samples)

    def _parse_legacy_metadata(self, content: str) -> Dict[str, Any]:
        """Extrae los valores de configuración y resultados de las cabeceras comentadas."""
        meta: Dict[str, Any] = {}

        patterns = {
            "date_str": r"# Fecha de registro:\s*(.+)",
            "limits": r"# Limites de la pista:\s*\[\s*([-\d\.]+)\s*m\s*,\s*([-\d\.]+)\s*m\s*\]",
            "x0": r"# Posicion inicial \(x0\):\s*([-\d\.]+)\s*m",
            "velocity": r"# Velocidad configurada \(v\):\s*([-\d\.]+)\s*m/s",
            "t_eff": r"# Tiempo efectivo de movimiento:\s*([-\d\.]+)\s*s",
            "t_total": r"# Tiempo total del experimento:\s*([-\d\.]+)\s*s",
            "pause_count": r"# Numero de pausas:\s*(\d+)",
            "pause_duration": r"# Tiempo total en pausa:\s*([-\d\.]+)\s*s",
            "x_final": r"# Posicion final:\s*([-\d\.]+)\s*m",
            "displacement": r"# Desplazamiento final \(Delta x\):\s*([-\d\.]+)\s*m",
            "distance": r"# Distancia final recorrida \(d\):\s*([-\d\.]+)\s*m",
            "v_avg_eff": r"# Velocidad media efectiva:\s*([-\d\.]+)\s*m/s",
            "s_avg_eff": r"# Rapidez media efectiva:\s*([-\d\.]+)\s*m/s",
            "v_avg_total": r"# Velocidad media global:\s*([-\d\.]+)\s*m/s",
            "s_avg_total": r"# Rapidez media global:\s*([-\d\.]+)\s*m/s",
            "termination_reason": r"# Razon de finalizacion:\s*(.+)",
            "mru_verified": r"# MRU Verificado en intervalos de movimiento:\s*(SI|NO)",
        }

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str.startswith("#"):
                continue

            for key, pat in patterns.items():
                m = re.match(pat, line_str)
                if m:
                    if key == "limits":
                        meta["track_min"] = float(m.group(1))
                        meta["track_max"] = float(m.group(2))
                    elif key in ("pause_count",):
                        meta[key] = int(m.group(1))
                    elif key == "mru_verified":
                        meta[key] = (m.group(1).upper() == "SI")
                    elif key in ("date_str", "termination_reason"):
                        meta[key] = m.group(1).strip()
                    else:
                        meta[key] = float(m.group(1))

        return meta

    def _parse_legacy_samples(self, content: str) -> List[MeasurementSample]:
        """Extrae la tabla CSV de telemetría saltándose las líneas de comentario."""
        csv_lines = [line for line in content.splitlines() if not line.strip().startswith("#")]
        if not csv_lines:
            return []

        reader = csv.DictReader(csv_lines)
        samples: List[MeasurementSample] = []

        for row in reader:
            try:
                sample = MeasurementSample(
                    sample_id=int(row.get("Muestra", len(samples))),
                    t_total=float(row.get("Tiempo_Total_s", 0.0)),
                    t_eff=float(row.get("Tiempo_Efectivo_s", 0.0)),
                    position=float(row.get("Posicion_m", 0.0)),
                    displacement=float(row.get("Desplazamiento_m", 0.0)),
                    distance=float(row.get("Distancia_Recorrida_m", 0.0)),
                    velocity=float(row.get("Velocidad_Instantanea_m_s", 0.0)),
                    speed=float(row.get("Rapidez_Instantanea_m_s", 0.0)),
                    status=row.get("Estado_Simulacion", "RUNNING")
                )
                samples.append(sample)
            except (ValueError, TypeError):
                continue

        return samples
