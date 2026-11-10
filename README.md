# Laboratorio Virtual de Cinemática: Movimiento Rectilíneo Uniforme (MRU)

> **Herramienta Educativa y Simulador Interactivo de Física para Ingeniería de Sistemas**  
> Desarrollado con Python 3, Tkinter y Matplotlib.

---

## 1. Propósito Educativo

Este laboratorio virtual ha sido concebido para suplir la ausencia de materiales físicos de laboratorio, proporcionando a los estudiantes universitarios de **Ingeniería de Sistemas** y ciencias exactas un entorno interactivo y riguroso de experimentación tipo *sandbox*.

El simulador permite:
- Contrastar el modelo teórico de la cinemática clásica con una simulación numérica continua y visualmente intuitiva.
- Formular hipótesis sobre el impacto de la posición inicial, el sentido del movimiento y las pausas.
- Comprender la naturaleza vectorial de magnitudes como la velocidad y el desplazamiento frente a sus análogos escalares (rapidez y distancia).
- Analizar gráficas científicas en tiempo real e interpretar pendientes y áreas bajo la curva.
- Exportar telemetría real a formato CSV para su posterior procesamiento en hojas de cálculo o lenguajes de análisis de datos (Python/Pandas, R, MATLAB).

---

## 2. Fundamentos Físicos Demostrados

El laboratorio modela y explica rigurosamente los siguientes conceptos:

### 2.1. Magnitudes Físicas (Escalares vs. Vectoriales)

| Magnitud | Naturaleza | Símbolo | Unidad SI | Definición y Significado |
| :--- | :---: | :---: | :---: | :--- |
| **Tiempo total** | Escalar | $t_{\text{total}}$ | $\text{s}$ | Duración global transcurrida (tiempo de pared), incluyendo pausas. |
| **Tiempo efectivo** | Escalar | $t_{\text{eff}}$ | $\text{s}$ | Tiempo durante el cual el cuerpo estuvo en traslación efectiva. |
| **Posición** | Vectorial (1D) | $x(t)$ | $\text{m}$ | Coordenada sobre la recta orientada respecto al origen $x = 0$. |
| **Posición inicial** | Vectorial (1D) | $x_0$ | $\text{m}$ | Punto de partida del cuerpo al inicio del movimiento. |
| **Desplazamiento** | Vectorial (1D) | $\Delta x$ | $\text{m}$ | Variación de posición: $\Delta x = x(t) - x_0$. Conserva signo. |
| **Distancia recorrida**| Escalar | $d$ | $\text{m}$ | Longitud acumulada de la trayectoria: $d = \|v\| \cdot t_{\text{eff}} \ge 0$. |
| **Velocidad instantánea**| Vectorial (1D) | $v$ | $\text{m/s}$ | Razón de cambio de la posición. Su signo define el sentido (+ derecha, - izquierda). |
| **Rapidez instantánea** | Escalar | $s$ | $\text{m/s}$ | Magnitud o módulo de la velocidad: $s = \|v\| \ge 0$. |
| **Aceleración** | Vectorial (1D) | $a$ | $\text{m/s}^2$ | Razón de cambio de la velocidad. En MRU estricto: $a = 0$. |

### 2.2. Ecuación Horaria del MRU

La posición en cada instante $t_{\text{eff}}$ se calcula analíticamente mediante:

$$x(t) = x_0 + v \cdot t_{\text{eff}}$$

Durante el MRU, el cuerpo recorre **desplazamientos iguales en intervalos de tiempo iguales**:

$$\Delta x_1 = \Delta x_2 = v \cdot \Delta t$$

### 2.3. Velocidad Media Efectiva frente a Velocidad Media Global

Un aspecto didáctico central del simulador es la distinción explícita de dos convenciones temporales cuando ocurren pausas:

1. **Velocidad Media Efectiva ($v_{\text{med, eff}}$):**
   Calculada únicamente sobre los lapsos en que el móvil se traslada:
   $$v_{\text{med, eff}} = \frac{\Delta x}{t_{\text{eff}}} = v$$
   *(Coincide con la velocidad constante configurada).*

2. **Velocidad Media Global ($v_{\text{med, total}}$):**
   Calculada sobre la duración total del experimento (tiempo de pared):
   $$v_{\text{med, total}} = \frac{\Delta x}{t_{\text{total}}} = \frac{\Delta x}{t_{\text{eff}} + t_{\text{pausa}}}$$
   *(Disminuye conforme se realizan pausas, demostrando cómo los periodos de reposo afectan el promedio global).*

### 2.4. Interpretación Geométrica de las Gráficas Científicas

- **Gráfica Posición vs. Tiempo ($x-t$):**
  - Es una línea recta de ecuación $x(t) = x_0 + v \cdot t$.
  - La **pendiente** de la recta representa la velocidad:
    $$m = \frac{\Delta x}{\Delta t} = v$$
  - Durante las pausas en tiempo global, la gráfica muestra una meseta horizontal ($m = 0$).
- **Gráfica Velocidad vs. Tiempo ($v-t$):**
  - Es una recta horizontal constante a la altura $v$.
  - El **área bajo la curva** entre dos instantes $t_1$ y $t_2$ equivale al desplazamiento realizado:
    $$\Delta x = \int_{t_1}^{t_2} v \, dt = v \cdot (t_2 - t_1)$$
  - Durante las pausas, la velocidad cae a $0\text{ m/s}$.

---

## 3. Arquitectura del Software

El código sigue una estricta separación de responsabilidades basada en el patrón de arquitectura por capas (inspirado en MVC):

```
├── main.py                     # Punto de entrada de la aplicación
├── requirements.txt            # Dependencias del proyecto (matplotlib, numpy, pandas)
├── README_dataset.md           # Diccionario de datos y guía de ML para el dataset
├── data/                       # Almacenamiento persistente local de experimentos y sesiones
│   ├── active_session.json     # Puntero a la sesión experimental activa
│   └── sessions/               # Carpetas particionadas por sesión
│       └── session_<id>/       # Subdirectorio por cada sesión
│           ├── session.json    # Metadatos del ciclo de vida de la sesión
│           ├── experiments.csv # Tabla maestra (1 fila por experimento completado)
│           ├── observations.csv# Series temporales de telemetría (1 fila por muestra)
│           └── manifest.json   # Manifiesto analítico con conteos y distribuciones
├── src/
│   ├── models/                 # Capa de Dominio y Lógica Pura (Sin dependencias GUI)
│   │   ├── physics.py          # Ecuaciones cinemáticas, límites, validaciones
│   │   └── experiment_state.py # Máquina de estados, cronómetro monotónico, telemetría
│   ├── gui/                    # Capa de Presentación (Tkinter y Matplotlib)
│   │   ├── theme.py            # Paleta de colores Dark Modern y estilos TTK
│   │   ├── track_view.py       # Canvas interactivo: pista, regla, origen, vector, vehículo
│   │   ├── telemetry_panel.py  # Tarjetas métricas digitales en tiempo real
│   │   ├── plots_view.py       # Gráficas Matplotlib x-t y v-t sincronizadas
│   │   ├── control_panel.py    # Configuración, controles y gestión de datasets
│   │   ├── dialogs.py          # Modales: informe científico, guía teórica y gestor de sesiones
│   │   ├── detailed_plot_viewer.py # Visor de plano cartesiano de alta resolución
│   │   └── main_window.py      # Ventana principal, barra de estado y orquestación
│   ├── controllers/            # Capa de Coordinación (Controlador)
│   │   └── simulation_controller.py # Bucle de animación (~40 FPS) y auto-guardado seguro
│   └── data/                   # Capa de Persistencia, Datasets y Machine Learning
│       ├── schema.py           # Esquema relacional, PhysicsModel, DataSource y columnas SI
│       ├── repository.py       # Repositorio local, ciclo de vida de sesiones y validación
│       ├── consolidator.py     # Exportador de datasets (sesión e historial completo para ML)
│       ├── migrator.py         # Migración y compatibilidad con informes antiguos
│       └── exporter.py         # Generador de reportes individuales tradicionales
└── tests/                      # Banco de Pruebas Unitarias y de Integración (34 pruebas)
    ├── test_physics.py         # Pruebas del modelo analítico de MRU
    ├── test_state_machine.py   # Pruebas de cronómetros, pausas y transiciones
    ├── test_exporter.py        # Pruebas de exportación individual a CSV
    ├── test_dataset_system.py  # 15 pruebas obligatorias de datasets y persistencia
    └── test_gui_integration.py # Pruebas de interfaz, eventos, diálogos y auto-guardado
```

### Principio de Rigor Temporal y Monotónico
- **Nunca se acumula posición mediante sumas iterativas ($\Delta x \mathrel{+}= v \cdot \Delta t$)**, ya que los métodos de Euler introducen deriva numérica dependiente de los fotogramas por segundo (FPS).
- En su lugar, se captura el tiempo real de alta precisión utilizando el reloj monotónico del sistema operativo (`time.perf_counter()`), evaluando directamente la solución analítica $x(t) = x_0 + v \cdot t_{\text{eff}}$.
- Al pausar, $t_{\text{eff}}$ se congela de manera determinista; al reanudar, el móvil continúa sin saltos bruscos ni discontinuidades.

---

## 4. Requisitos del Sistema

- **Sistema Operativo:** Linux, Windows 10/11 o macOS.
- **Python:** Versión 3.10 o superior (verificado en Python 3.14).
- **Dependencias externas:**
  - `matplotlib` (versión $\ge 3.7.0$)
  - `numpy` (versión $\ge 1.24.0$)
  - `tkinter` (incluido habitualmente en la instalación estándar de Python).

---

## 5. Instalación y Ejecución

### 5.1. Clonar o descargar el proyecto

```bash
cd "/home/emmanuel/proyectos/Experimento fisica"
```

### 5.2. Crear y activar entorno virtual (Recomendado)

En Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

En Windows:
```cmd
python -m venv venv
venv\Scripts\activate
```

### 5.3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5.4. Ejecutar el laboratorio virtual

```bash
python3 main.py
```

---

## 6. Manual de Uso de la Interfaz

### 6.1. Casos Didácticos Predefinidos (Presets)
El panel superior ofrece presets rápidos para facilitar demostraciones en clase:
1. **MRU Básico hacia la derecha:** $x_0 = 0\text{ m}$, $v = +10\text{ m/s}$ sobre $[-50, 50]\text{ m}$.
2. **Posición inicial positiva:** $x_0 = +20\text{ m}$, $v = +15\text{ m/s}$.
3. **Sentido negativo hacia la izquierda:** $x_0 = +40\text{ m}$, $v = -12\text{ m/s}$.
4. **Vehículo en reposo:** $v = 0\text{ m/s}$ (demuestra ausencia de traslación).
5. **Pista métrica estándar 0 a 100m:** $x_0 = 0\text{ m}$, $v = +20\text{ m/s}$ sobre $[0, 100]\text{ m}$.

### 6.2. Configuración Manual de Parámetros
- **Límites de la pista ($x_{\min}, x_{\max}$):** Permite redimensionar la recta numérica.
- **Posición inicial ($x_0$):** Controlada mediante slider o caja de texto.
- **Velocidad ($v$):** Selección de magnitud mediante slider y sentido ("Derecha (+)" o "Izquierda (-)").
- **Validación automática:** Evita que el vehículo intente desplazarse hacia afuera de la pista o comience fuera de los límites.

### 6.3. Botones de Control de la Simulación
- `▶ INICIAR` (o tecla **Espacio**): Comienza el desplazamiento del vehículo.
- `⏸ PAUSAR` (o tecla **Espacio**): Congela el tiempo efectivo de movimiento; la posición se mantiene inalterada.
- `⏯ CONTINUAR` (o tecla **Espacio**): Reanuda el movimiento continuo.
- `⏹ FINALIZAR` (o tecla **Escape**): Detiene definitivamente el experimento y conserva los datos para análisis.
- `🔄 REINICIAR` (o atajo **Ctrl+R**): Restaura la pista y variables a su estado inicial.

### 6.4. Pista Virtual
- **Recta numérica graduada:** Con marcas métricas mayores y menores.
- **Origen $x = 0$:** Destacado con línea punteada vertical y punto cyan reflectivo.
- **Marcador $x_0$:** Banderín amarillo que señala el punto de partida.
- **Vector $\vec{v}$:** Flecha rosa sobre el vehículo orientada según el sentido del movimiento con longitud proporcional a la rapidez.
- **Vector $\Delta x$:** Segmento verde esmeralda con flecha que ilustra el desplazamiento entre $x_0$ y $x(t)$.
- **Barreras límite:** Al alcanzar el extremo de la pista, la simulación se detiene automáticamente en el borde exacto.

### 6.5. Selector de Modo de Gráfica
En la esquina superior de las gráficas de Matplotlib, el usuario puede alternar entre:
- **Tiempo Global (con pausas):** Muestra el experimento completo tal como ocurrió en el mundo real (las pausas se ven como tramos horizontales en $x-t$ y caídas a cero en $v-t$).
- **Tiempo Efectivo (MRU continuo):** Muestra únicamente el comportamiento lineal continuo del modelo ideal.

### 6.6. Visor Científico Avanzado y Ampliación de Gráficas en el Plano Cartesiano (🔍)
Al presionar el botón **"🔍 Ampliar Gráfica"** (en la esquina de las gráficas o en el panel de control, o mediante el atajo **Ctrl+G** / **F11**), se abre una ventana de gran formato diseñada para el análisis minucioso:
- **Plano Cartesiano de Alta Resolución:** Ejes X e Y con marcas mayores, menores y cuadrícula científica fina.
- **Herramientas de Navegación de Matplotlib:** Lupa de aumento rectangular (zoom libre en cualquier intervalo), paneo/arrastre para desplazarse, botón Home y exportador de imágenes en 300 DPI (PNG, PDF vectorial, SVG).
- **Anotaciones de Medidas Físicas en el Plano:**
  - **Triángulo de Pendiente:** Muestra explícitamente los catetos $\Delta t$ y $\Delta x$, calculando en el plano la pendiente de la recta $m = \frac{\Delta x}{\Delta t} = v$ (velocidad constante).
  - **Intervalos de Pausa:** Zonas sombreadas en ámbar que marcan con precisión el inicio, fin y duración de cada pausa con la indicación $m = 0$ y velocidad nula.
  - **Integral de Desplazamiento:** Área sombreada bajo la curva de velocidad que demuestra visualmente que $\text{Área} = \int v\,dt = \Delta x$.
  - **Puntos Notables:** Puntos de inicio $(0, x_0)$ y llegada $(t_f, x_f)$ con cotas y etiquetas exactas.
- **Telemetría Dinámica con Mira Telescópica (Crosshair):** Al desplazar el ratón sobre la gráfica, se proyectan líneas guía y una barra digital superior muestra en tiempo real las coordenadas exactas $(t, x, v, \text{estado})$ de la muestra más cercana.
- **Pestaña con Tabla de Puntos Notables:** Desglose cronológico de todos los eventos críticos del experimento (inicio, pausas, reanudaciones y parada final).

### 6.7. Registro Científico y Datasets para IA / Machine Learning
- **Auto-guardado Transparente:** Cada simulación finalizada (por detención del usuario o colisión en bordes) se valida físicamente y se guarda de inmediato en la sesión activa en disco local sin requerir que el usuario pulse exportar tras cada simulacro.
- **Barra de Estado Inferior:** Muestra permanentemente la sesión activa, el conteo de experimentos acumulados y el estado del guardado automático en tiempo real.
- **Botón "📦 Exportar Dataset de Sesión" (o atajo Ctrl+E):** Exporta el paquete científico consolidado de la sesión seleccionada (`experiments.csv`, `observations.csv`, `manifest.json`, `README_dataset.md`) al directorio que elija el usuario.
- **Botón "🌐 Exportar Historial Completo":** Consolida todas las sesiones experimentales históricas en un único dataset global unificado.
- **Gestor de Sesiones ("📑 Sesiones"):** Permite conmutar entre sesiones existentes, retomar sesiones anteriores y crear nuevas sesiones experimentales con notas descriptivas.
- **Migración de Informes Legados ("🔄 Migrar Informe..."):** Importa informes CSV antiguos sin alterar los archivos fuente originales y evitando duplicaciones por cálculo de hash SHA-256.
- **Exportación Individual Tradicional:** Se conserva el botón **"💾 Exportar Datos a CSV"** para generar reportes individuales aislados con cabeceras comentadas `#` cuando sea requerido.

---

## 7. Sistema de Registro Científico y Datasets para Machine Learning

### 7.1. Estructura de Almacenamiento Persistente
Los datos se almacenan en la carpeta `data/` estructurados por sesiones experimentales:

```
data/
├── active_session.json            # Guarda {"session_id": "...", "updated_at": "..."}
└── sessions/
    └── session_<session_id>/
        ├── session.json           # Metadatos del ciclo de vida de la sesión
        ├── experiments.csv        # Tabla maestra (1 fila por experimento completado)
        ├── observations.csv       # Telemetría continua (1 fila por muestra temporal)
        └── manifest.json          # Manifiesto analítico con esquema y distribución de clases
```

### 7.2. Catálogo Extensible de Modelos Físicos (`physics_model`)
El etiquetado supervisado proviene de la configuración real del simulador cinemático (verdad fundamental / ground truth):
- `MRU`: Movimiento Rectilíneo Uniforme ($x(t) = x_0 + v \cdot t_{\text{eff}}$).
- `MRUA`: Movimiento Rectilíneo Uniformemente Acelerado.
- `MRUR`: Movimiento Rectilíneo Uniformemente Retardado.
- `CAIDA_LIBRE`: Caída libre bajo aceleración gravitatoria constante.
- `MOVIMIENTO_PERSONALIZADO`: Modelo cinemático definido por el usuario.
- `UNKNOWN`: Modelo no identificado o no disponible.

### 7.3. Esquema Relacional de Datasets (v1.0.0)

#### Tabla Maestra: `experiments.csv`
Una fila por cada experimento completado. Unidades SI en el encabezado:
- **Identificación:** `experiment_id`, `session_id`, `experiment_number`, `physics_model`, `physics_model_version`, `software_version`, `experiment_status`, `data_source`.
- **Configuración:** `initial_position_m`, `track_min_m`, `track_max_m`, `configured_velocity_m_s`, `configured_acceleration_m_s2`, `configured_duration_s`, `random_seed`.
- **Resultados:** `final_position_m`, `displacement_m`, `distance_traveled_m`, `active_duration_s`, `wall_duration_s`, `pause_count`, `total_pause_duration_s`, `mean_velocity_active_m_s`, `mean_speed_active_m_s`, `mean_velocity_wall_m_s`, `mean_speed_wall_m_s`, `termination_reason`, `started_at`, `completed_at`.

#### Tabla de Series Temporales: `observations.csv`
Una fila por cada muestra de telemetría registrada:
- `experiment_id`, `session_id`, `sample_index`, `wall_time_s`, `active_time_s`, `position_m`, `displacement_m`, `distance_traveled_m`, `velocity_m_s`, `speed_m_s`, `acceleration_m_s2`, `simulation_state`, `physics_model`.

### 7.4. Carga Directa en Python y Pandas

Los archivos CSV carecen de preámbulos decorativos y pueden leerse directamente en pandas:

```python
import pandas as pd

# 1. Cargar tabla maestra de experimentos
df_experiments = pd.read_csv("experiments.csv")
print("Total experimentos:", len(df_experiments))
print(df_experiments[["experiment_id", "physics_model", "configured_velocity_m_s"]].head())

# 2. Cargar tabla de observaciones temporales
df_observations = pd.read_csv("observations.csv")
print("Total muestras telemétricas:", len(df_observations))

# 3. Merge relacional entre ambas tablas
df_dataset = df_observations.merge(
    df_experiments[["experiment_id", "physics_model", "configured_velocity_m_s"]],
    on="experiment_id",
    how="left"
)
print(df_dataset.head())
```

### 7.5. Prevención Rigurosa de Fuga de Información (Data Leakage)
> [!WARNING] Reglas Obligatorias para Modelos de Machine Learning
> 1. **Partición por Experimento (`GroupKFold` / `GroupShuffleSplit`):**  
>    **Nunca** use `train_test_split(df_observations)` fila a fila de forma puramente aleatoria. Las muestras temporales de un mismo simulacro están correlacionadas. Agrupe siempre por `groups=df_observations["experiment_id"]`.
> 2. **Partición por Sesión:**  
>    Para verificar que el modelo generalice ante distintas condiciones de experimentación, particione por `session_id`.
> 3. **Procedencia de Datos:**  
>    Utilice la columna `data_source` (`IDEAL_SIMULATION`, `SIMULATION_WITH_NOISE`, `REAL_MEASUREMENT`, `IMPORTED_LEGACY`) para evaluar robustez ante ruido o distribuciones fuera de dominio.

---

## 8. Pruebas Automatizadas y Verificación

El proyecto cuenta con una suite completa de **34 pruebas automatizadas** que validan la física, la máquina de estados, el exportador, la integración GUI y la infraestructura científica de datos para ML:

```bash
python3 -m unittest discover tests -v
```

### Resultados de Ejecución Real:
```text
test_boundary_capping_no_overshoot (test_physics.TestMRUPhysics) ... ok
test_invalid_parameters_validation (test_physics.TestMRUPhysics) ... ok
test_negative_velocity_motion (test_physics.TestMRUPhysics) ... ok
test_positive_velocity_motion (test_physics.TestMRUPhysics) ... ok
test_zero_velocity_at_rest (test_physics.TestMRUPhysics) ... ok
test_average_velocity_and_speed_calculations (test_physics.TestMRUPhysics) ... ok
test_initial_state_ready (test_state_machine.TestExperimentStateMachine) ... ok
test_start_and_update (test_state_machine.TestExperimentStateMachine) ... ok
test_pause_and_resume_cycles (test_state_machine.TestExperimentStateMachine) ... ok
test_stop_and_summary_generation (test_state_machine.TestExperimentStateMachine) ... ok
test_automatic_boundary_termination (test_state_machine.TestExperimentStateMachine) ... ok
test_csv_generation_and_export (test_exporter.TestExporter) ... ok
test_01_auto_save_completed_experiment (test_dataset_system.TestScientificDatasetSystem) ... ok
test_02_accumulation_of_experiments_without_overwriting (test_dataset_system.TestScientificDatasetSystem) ... ok
test_03_persistence_across_app_restart (test_dataset_system.TestScientificDatasetSystem) ... ok
test_04_session_association (test_dataset_system.TestScientificDatasetSystem) ... ok
test_05_unique_identifiers (test_dataset_system.TestScientificDatasetSystem) ... ok
test_06_deduplication (test_dataset_system.TestScientificDatasetSystem) ... ok
test_07_session_dataset_export (test_dataset_system.TestScientificDatasetSystem) ... ok
test_08_historical_dataset_export (test_dataset_system.TestScientificDatasetSystem) ... ok
test_09_direct_pandas_read (test_dataset_system.TestScientificDatasetSystem) ... ok
test_10_headers_and_data_types_integrity (test_dataset_system.TestScientificDatasetSystem) ... ok
test_11_missing_values_representation (test_dataset_system.TestScientificDatasetSystem) ... ok
test_12_legacy_report_migration (test_dataset_system.TestScientificDatasetSystem) ... ok
test_13_physical_consistency_validation (test_dataset_system.TestScientificDatasetSystem) ... ok
test_14_experiment_status_and_filtering (test_dataset_system.TestScientificDatasetSystem) ... ok
test_15_resilience_to_damaged_or_missing_files (test_dataset_system.TestScientificDatasetSystem) ... ok
test_initial_gui_state (test_gui_integration.TestGUIIntegration) ... ok
test_start_pause_resume_reset_cycle (test_gui_integration.TestGUIIntegration) ... ok
test_preset_selection (test_gui_integration.TestGUIIntegration) ... ok
test_dialog_creations (test_gui_integration.TestGUIIntegration) ... ok
test_detailed_plot_viewer_features (test_gui_integration.TestGUIIntegration) ... ok
test_auto_save_integration_in_gui (test_gui_integration.TestGUIIntegration) ... ok
test_session_manager_dialog_integration (test_gui_integration.TestGUIIntegration) ... ok

----------------------------------------------------------------------
Ran 34 tests in 20.529s

OK
```

---

## 9. Licencia y Créditos

Proyecto desarrollado con fines académicos y de divulgación científica para cursos de **Física General**, **Simulación Numérica** e **Inteligencia Artificial y Machine Learning** en programas de **Ingeniería de Sistemas**.
Uso libre para docencia, aprendizaje e investigación.
