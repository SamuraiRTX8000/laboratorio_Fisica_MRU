"""
Módulo de Consolidación y Exportación de Datasets para Machine Learning.

Genera paquetes de datos estructurados, limpios y directamente consumibles por
`pandas.read_csv()`, tanto a nivel de sesión individual como de historial consolidado completo.
Incluye manifiesto JSON y guía de uso para proyectos de Inteligencia Artificial (README_dataset.md).
"""

import os
import json
import csv
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .schema import (
    DATASET_SCHEMA_VERSION,
    SOFTWARE_VERSION,
    EXPERIMENTS_CSV_COLUMNS,
    OBSERVATIONS_CSV_COLUMNS
)
from .repository import ExperimentRepository


class DatasetConsolidator:
    """Consolidador y exportador de datasets científicos para Machine Learning."""

    def __init__(self, repository: ExperimentRepository) -> None:
        self.repo = repository

    def export_session_dataset(self, session_id: str, target_dir: str) -> Path:
        """
        Exporta el dataset completo de una sesión específica a la carpeta seleccionada por el usuario.
        Genera:
            - experiments.csv
            - observations.csv
            - manifest.json
            - README_dataset.md
        """
        out_path = Path(target_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        exps = self.repo.load_session_experiments(session_id)
        obs = self.repo.load_session_observations(session_id)

        # 1. Escribir experiments.csv
        exp_file = out_path / "experiments.csv"
        self._write_csv_table(exp_file, EXPERIMENTS_CSV_COLUMNS, exps)

        # 2. Escribir observations.csv
        obs_file = out_path / "observations.csv"
        self._write_csv_table(obs_file, OBSERVATIONS_CSV_COLUMNS, obs)

        # 3. Generar manifest.json
        manifest_file = out_path / "manifest.json"
        manifest_data = self._create_manifest(
            scope="SESSION",
            session_id=session_id,
            experiments=exps,
            observations=obs
        )
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # 4. Generar README_dataset.md
        readme_file = out_path / "README_dataset.md"
        readme_content = self.generate_dataset_readme(
            scope="Sesión Experimental",
            session_id=session_id,
            exp_count=len(exps),
            obs_count=len(obs)
        )
        readme_file.write_text(readme_content, encoding="utf-8")

        return out_path

    def export_historical_dataset(self, target_dir: str) -> Path:
        """
        Exporta el historial completo acumulado de todas las sesiones registradas.
        Genera un dataset consolidado unificado con todos los experimentos y observaciones.
        """
        out_path = Path(target_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        all_exps = self.repo.load_all_experiments()
        all_obs = self.repo.load_all_observations()

        # 1. Escribir experiments.csv consolidado
        exp_file = out_path / "experiments.csv"
        self._write_csv_table(exp_file, EXPERIMENTS_CSV_COLUMNS, all_exps)

        # 2. Escribir observations.csv consolidado
        obs_file = out_path / "observations.csv"
        self._write_csv_table(obs_file, OBSERVATIONS_CSV_COLUMNS, all_obs)

        # 3. Generar manifest.json
        manifest_file = out_path / "manifest.json"
        manifest_data = self._create_manifest(
            scope="HISTORICAL_ALL_SESSIONS",
            session_id="ALL_SESSIONS_CONSOLIDATED",
            experiments=all_exps,
            observations=all_obs
        )
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # 4. Generar README_dataset.md
        readme_file = out_path / "README_dataset.md"
        readme_content = self.generate_dataset_readme(
            scope="Historial Completo Multi-Sesión",
            session_id="TODAS LAS SESIONES",
            exp_count=len(all_exps),
            obs_count=len(all_obs)
        )
        readme_file.write_text(readme_content, encoding="utf-8")

        return out_path

    def _write_csv_table(self, file_path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
        """Escribe una tabla CSV limpia con cabecera en fila 0, sin líneas de comentario."""
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                filtered_row = {k: r.get(k, "") for k in fieldnames}
                writer.writerow(filtered_row)

    def _create_manifest(
        self,
        scope: str,
        session_id: str,
        experiments: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crea el diccionario de metadatos analíticos para manifest.json."""
        models_dist: Dict[str, int] = {}
        statuses_dist: Dict[str, int] = {}
        sources_dist: Dict[str, int] = {}

        for e in experiments:
            m = e.get("physics_model", "UNKNOWN")
            s = e.get("experiment_status", "UNKNOWN")
            src = e.get("data_source", "UNKNOWN")
            models_dist[m] = models_dist.get(m, 0) + 1
            statuses_dist[s] = statuses_dist.get(s, 0) + 1
            sources_dist[src] = sources_dist.get(src, 0) + 1

        return {
            "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "software_version": SOFTWARE_VERSION,
            "scope": scope,
            "session_id": session_id,
            "exported_at": datetime.datetime.now().isoformat(),
            "total_experiments": len(experiments),
            "total_observations": len(observations),
            "distributions": {
                "physics_models": models_dist,
                "experiment_statuses": statuses_dist,
                "data_sources": sources_dist
            },
            "schema_columns": {
                "experiments": EXPERIMENTS_CSV_COLUMNS,
                "observations": OBSERVATIONS_CSV_COLUMNS
            },
            "files": {
                "experiments_csv": "experiments.csv",
                "observations_csv": "observations.csv",
                "manifest_json": "manifest.json",
                "documentation": "README_dataset.md"
            }
        }

    def generate_dataset_readme(self, scope: str, session_id: str, exp_count: int, obs_count: int) -> str:
        """Genera el contenido exhaustivo de README_dataset.md."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# Dataset Científico de Cinemática para Inteligencia Artificial y Machine Learning

> **Laboratorio Virtual de Física — Esquema de Dataset v{DATASET_SCHEMA_VERSION}**  
> **Fecha de Exportación:** {now_str}  
> **Alcance:** {scope}  
> **Identificador de Sesión:** `{session_id}`  
> **Total de Experimentos:** {exp_count}  
> **Total de Observaciones Telemétricas:** {obs_count}

---

## 1. Descripción General del Dataset

Este dataset contiene registros empíricos y analíticos de simulaciones físicas cinemáticas generadas por el **Laboratorio Virtual de Cinemática**.

El dataset se encuentra completamente normalizado en dos tablas relacionales en formato CSV:
1. `experiments.csv`: Tabla maestra con una fila por cada experimento o simulacro completado.
2. `observations.csv`: Tabla de series temporales de alta resolución con una fila por cada muestra telemétrica.

Ambas tablas se relacionan biunívocamente mediante la clave foránea `experiment_id`.

Los archivos CSV están estructurados conforme a los estándares de Machine Learning:
- **Sin comentarios iniciales:** Cabecera de columnas directamente en la primera línea.
- **Carga directa en Python:** Compatibilidad inmediata con `pandas.read_csv()`.
- **Codificación:** UTF-8 con saltos de línea estándar.
- **Valores ausentes:** Representados como cadenas vacías (`""`) que se interpretan automáticamente como `NaN` en pandas.
- **Unidades explícitas:** Cada columna numérica incluye su unidad de medida del Sistema Internacional en el nombre (p.ej., `_m`, `_s`, `_m_s`, `_m_s2`).

---

## 2. Instrucciones de Carga en Python y Pandas

```python
import pandas as pd

# Cargar tabla maestra de experimentos
df_experiments = pd.read_csv("experiments.csv")
print(f"Experimentos cargados: {{len(df_experiments)}}")
print(df_experiments.info())

# Cargar tabla de observaciones temporales
df_observations = pd.read_csv("observations.csv")
print(f"Observaciones cargadas: {{len(df_observations)}}")
print(df_observations.head())

# Unir observaciones con la configuración de su experimento (Merge relacional)
df_merged = df_observations.merge(
    df_experiments[["experiment_id", "physics_model", "configured_velocity_m_s"]],
    on="experiment_id",
    how="left"
)
```

---

## 3. Diccionario de Datos

### 3.1. Tabla `experiments.csv` (1 fila por experimento)

| Columna | Tipo | Unidad SI | Descripción |
| :--- | :---: | :---: | :--- |
| `experiment_id` | `string` | — | Identificador único del experimento (`exp_YYYYMMDD_HHMMSS_xxxx`). |
| `session_id` | `string` | — | Identificador de la sesión a la que pertenece. |
| `experiment_number` | `integer`| — | Número secuencial del experimento en la sesión (1, 2, 3...). |
| `physics_model` | `string` | — | Etiqueta del modelo físico real (`MRU`, `MRUA`, etc.). |
| `physics_model_version` | `string` | — | Versión del modelo físico cinemático utilizado. |
| `software_version` | `string` | — | Versión de la aplicación que generó la simulación. |
| `experiment_status` | `string` | — | Estado final (`COMPLETED`, etc.). |
| `data_source` | `string` | — | Procedencia (`IDEAL_SIMULATION`, `SIMULATION_WITH_NOISE`, `REAL_MEASUREMENT`, `IMPORTED_LEGACY`). |
| `initial_position_m`| `float`  | m | Posición inicial x0 configurada en el sistema de referencia. |
| `track_min_m` | `float`  | m | Límite inferior de la recta numérica x_min. |
| `track_max_m` | `float`  | m | Límite superior de la recta numérica x_max. |
| `configured_velocity_m_s` | `float` | m/s | Velocidad constante vectorial configurada v. |
| `configured_acceleration_m_s2` | `float` | m/s² | Aceleración configurada (vacío para MRU donde a = 0 no es parámetro). |
| `configured_duration_s` | `float` | s | Duración prefijada si correspondiese (vacío si es libre). |
| `random_seed` | `integer`| — | Semilla estocástica si hubiese ruido sintético (vacío para simulación determinista). |
| `final_position_m` | `float` | m | Posición final donde se detuvo el cuerpo. |
| `displacement_m` | `float` | m | Desplazamiento neto: Delta x = x_final - x0. |
| `distance_traveled_m` | `float` | m | Distancia total acumulada: d = |v| * t_eff >= 0. |
| `active_duration_s` | `float` | s | Tiempo efectivo de movimiento t_eff (sin pausas). |
| `wall_duration_s` | `float` | s | Tiempo de pared total t_total desde inicio hasta parada. |
| `pause_count` | `integer`| — | Cantidad total de intervenciones de pausa realizadas. |
| `total_pause_duration_s` | `float` | s | Tiempo acumulado en reposo por pausas. |
| `mean_velocity_active_m_s` | `float` | m/s | Velocidad media efectiva: Delta x / t_eff. |
| `mean_speed_active_m_s` | `float` | m/s | Rapidez media efectiva: d / t_eff. |
| `mean_velocity_wall_m_s` | `float` | m/s | Velocidad media global: Delta x / t_total. |
| `mean_speed_wall_m_s` | `float` | m/s | Rapidez media global: d / t_total. |
| `termination_reason` | `string` | — | Causa de finalización (Límite alcanzado, detenido por usuario, etc.). |
| `started_at` | `string` | — | Fecha y hora de inicio (formato ISO 8601). |
| `completed_at` | `string` | — | Fecha y hora de conclusión (formato ISO 8601). |

### 3.2. Tabla `observations.csv` (Series de tiempo de telemetría)

| Columna | Tipo | Unidad SI | Descripción |
| :--- | :---: | :---: | :--- |
| `experiment_id` | `string` | — | Clave foránea hacia `experiments.csv`. |
| `session_id` | `string` | — | Identificador de la sesión. |
| `sample_index` | `integer`| — | Índice secuencial de la muestra en el experimento (0, 1, 2, ...). |
| `wall_time_s` | `float` | s | Tiempo transcurrido de pared t_total en el instante de muestreo. |
| `active_time_s` | `float` | s | Tiempo efectivo de movimiento t_eff en ese instante. |
| `position_m` | `float` | m | Coordenada instantánea x(t) sobre la recta. |
| `displacement_m` | `float` | m | Desplazamiento acumulado hasta ese instante: x(t) - x0. |
| `distance_traveled_m` | `float` | m | Distancia escalar acumulada. |
| `velocity_m_s` | `float` | m/s | Velocidad instantánea (0 durante pausas). |
| `speed_m_s` | `float` | m/s | Rapidez instantánea (0 durante pausas). |
| `acceleration_m_s2` | `float` | m/s² | Aceleración instantánea (vacío en MRU ideal). |
| `simulation_state` | `string` | — | Estado del simulador (`RUNNING`, `PAUSED`, `FINISHED`). |
| `physics_model` | `string` | — | Etiqueta del modelo (`MRU`). |

---

## 4. Casos de Uso en Inteligencia Artificial y Machine Learning

Este dataset ha sido diseñado para servir de base en múltiples problemas de aprendizaje automático:

### 4.1. Clasificación Supervisada de Modelos Físicos
- **Objetivo:** Clasificar el tipo de movimiento (`physics_model`) a partir de secuencias de telemetría.
- **Entradas:** Características extraídas de la serie temporal (derivadas numéricas, aceleración media, varianza de velocidad).
- **Etiqueta Target:** `physics_model` (e.g. `MRU` vs `MRUA`).

### 4.2. Regresión de Parámetros Cinemáticos
- **Objetivo:** Predecir los parámetros físicos latentes del escenario a partir de mediciones ruidosas.
- **Variables Target:** `configured_velocity_m_s` y `initial_position_m`.

### 4.3. Detección de Anomalías e Interrupciones
- **Objetivo:** Identificar intervalos de pausa o comportamiento atípico utilizando los residuos del modelo de predicción de posición: x(t) - (x0 + v * t).

### 4.4. Predicción de Trayectorias (Modelos Secuenciales / LSTM / Transformers)
- **Objetivo:** Predecir las siguientes $k$ posiciones de un móvil dada una ventana de observación pasada.

---

## 5. Prevención Rigurosa de Fuga de Información (Data Leakage)

> [!WARNING] Reglas Obligatorias para la Partición de Datos (Train / Val / Test)
> 1. **Partición por Experimento (`GroupKFold` / `GroupShuffleSplit`):**  
>    **NUNCA** divida las observaciones de forma puramente aleatoria fila a fila (`train_test_split(df_observations)`). Dado que las muestras de un mismo experimento están correlacionadas temporalmente, hacerlo produciría una fuga masiva de información donde el modelo memorizaría la trayectoria.
>    - **Correcto:** Dividir agrupando estrictamente por `experiment_id`:
>      ```python
>      from sklearn.model_selection import GroupShuffleSplit
>      gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
>      train_idx, test_idx = next(gss.split(df_observations, groups=df_observations["experiment_id"]))
>      train_obs = df_observations.iloc[train_idx]
>      test_obs = df_observations.iloc[test_idx]
>      ```
> 2. **Partición por Sesión:**  
>    Para evaluar la capacidad de generalización ante condiciones de experimentador diferentes, realice la partición a nivel de `session_id`.
> 3. **Procedencia de Datos:**  
>    Utilice la columna `data_source` para entrenar preferentemente sobre datos sintéticos e idealizados y evaluar sobre datos reales o con ruido añadido.
"""
