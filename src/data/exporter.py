"""
Módulo de Exportación de Datos Experimentales.

Exporta las muestras reales registradas durante la simulación de MRU a formato CSV,
con metadatos científicos, unidades en el Sistema Internacional (SI) y formato limpio.
"""

import csv
import datetime
from pathlib import Path
from typing import List, Optional, Union
from ..models.experiment_state import MeasurementSample, ExperimentSummary
from ..models.physics import TrackConfig, MRUParameters, MRUAParameters, FreeFallParameters


class ExperimentDataExporter:
    """Exportador de datos experimentales a archivos CSV."""

    @staticmethod
    def generate_csv_content(
        samples: List[MeasurementSample],
        summary: ExperimentSummary,
        track: Optional[TrackConfig],
        params: Union[MRUParameters, MRUAParameters, FreeFallParameters],
        title: Optional[str] = None
    ) -> str:
        """Genera el contenido textual en formato CSV con metadatos y tabla de datos."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determinar magnitudes iniciales según el tipo de parámetros
        if isinstance(params, MRUAParameters):
            x0_val = params.x0
            v0_val = params.v0
            a_val = params.acceleration
            default_title = "Laboratorio Virtual de Cinemática - MRUA"
        elif isinstance(params, FreeFallParameters):
            x0_val = params.y0
            v0_val = params.v0
            a_val = -params.g
            default_title = "Laboratorio Virtual de Cinemática - Caída Libre"
        else:
            x0_val = params.x0
            v0_val = params.velocity
            a_val = 0.0
            default_title = "Laboratorio Virtual de Cinemática - Movimiento Rectilíneo Uniforme (MRU)"

        exp_title = title or default_title
        lines = [
            f"# ====================================================================",
            f"# {exp_title.upper()}",
            f"# METADATOS EXPERIMENTALES REGISTRADOS",
            f"# ====================================================================",
            f"# Fecha de registro: {now_str}",
        ]

        if isinstance(params, MRUAParameters):
            track_desc = f"[{track.x_min:.2f} m, {track.x_max:.2f} m] (Longitud: {track.total_length:.2f} m)" if track else "Libre"
            lines.extend([
                f"# Limites de la pista: {track_desc}",
                f"# Posicion inicial (x0): {params.x0:.4f} m",
                f"# Velocidad inicial (v0): {params.v0:.4f} m/s",
                f"# Aceleracion configurada (a): {params.acceleration:+.4f} m/s²",
                f"# Rapidez configurada (|v0|): {params.speed0:.4f} m/s",
            ])
        elif isinstance(params, FreeFallParameters):
            lines.extend([
                f"# Escenario: Caida Libre / Lanzamiento Vertical",
                f"# Altura inicial (y0): {params.y0:.4f} m",
                f"# Velocidad inicial (v0): {params.v0:.4f} m/s",
                f"# Gravedad configurada (g): {params.g:.4f} m/s²",
                f"# Rapidez configurada (|v0|): {params.speed0:.4f} m/s",
            ])
        else:
            track_desc = f"[{track.x_min:.2f} m, {track.x_max:.2f} m] (Longitud: {track.total_length:.2f} m)" if track else "[-50.00 m, 50.00 m]"
            lines.extend([
                f"# Limites de la pista: {track_desc}",
                f"# Posicion inicial (x0): {params.x0:.4f} m",
                f"# Velocidad configurada (v): {params.velocity:.4f} m/s",
                f"# Rapidez configurada (|v|): {params.speed:.4f} m/s",
            ])

        lines.extend([
            f"# Tiempo efectivo de movimiento: {summary.t_eff:.4f} s",
            f"# Tiempo total del experimento: {summary.t_total:.4f} s",
            f"# Numero de pausas: {summary.pause_count}",
            f"# Tiempo total en pausa: {summary.total_pause_duration:.4f} s",
            f"# Posicion final: {summary.x_final:.4f} m",
            f"# Desplazamiento final (Delta x): {summary.displacement:.4f} m",
            f"# Distancia final recorrida (d): {summary.distance:.4f} m",
            f"# Velocidad media efectiva: {summary.v_avg_eff:.4f} m/s",
            f"# Rapidez media efectiva: {summary.s_avg_eff:.4f} m/s",
            f"# Velocidad media global: {summary.v_avg_total:.4f} m/s",
            f"# Rapidez media global: {summary.s_avg_total:.4f} m/s",
            f"# Razon de finalizacion: {summary.termination_reason}",
            f"# Modelo fisico: {summary.motion_type}",
            f"# ====================================================================",
            f"# DATOS TELEMETRICOS DE LA SIMULACION (MUESTRAS REALES)",
            f"# ====================================================================",
        ])

        # Encabezado CSV
        headers = [
            "Muestra",
            "Tiempo_Total_s",
            "Tiempo_Efectivo_s",
            "Posicion_m",
            "Desplazamiento_m",
            "Distancia_Recorrida_m",
            "Velocidad_Instantanea_m_s",
            "Rapidez_Instantanea_m_s",
            "Aceleracion_Instantanea_m_s2",
            "Estado_Simulacion"
        ]
        lines.append(",".join(headers))

        for s in samples:
            acc_str = f"{getattr(s, 'acceleration', a_val):.4f}"
            row = [
                str(s.sample_id),
                f"{s.t_total:.4f}",
                f"{s.t_eff:.4f}",
                f"{s.position:.4f}",
                f"{s.displacement:.4f}",
                f"{s.distance:.4f}",
                f"{s.velocity:.4f}",
                f"{s.speed:.4f}",
                acc_str,
                s.status
            ]
            lines.append(",".join(row))

        return "\n".join(lines)

    @classmethod
    def export_to_file(
        cls,
        filepath: str,
        samples: List[MeasurementSample],
        summary: ExperimentSummary,
        track: Optional[TrackConfig],
        params: Union[MRUParameters, MRUAParameters, FreeFallParameters]
    ) -> Path:
        """Exporta los datos reales a un archivo CSV en disco."""
        content = cls.generate_csv_content(samples, summary, track, params)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
