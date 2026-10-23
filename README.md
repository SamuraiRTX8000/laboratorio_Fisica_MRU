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
├── requirements.txt            # Dependencias del proyecto
├── src/
│   ├── models/                 # Capa de Dominio y Lógica Pura (Sin dependencias GUI)
│   │   ├── physics.py          # Ecuaciones cinemáticas, límites, validaciones
│   │   └── experiment_state.py # Máquina de estados, cronómetro monotónico, telemetría
│   ├── gui/                    # Capa de Presentación (Tkinter y Matplotlib)
│   │   ├── theme.py            # Paleta de colores Dark Modern y estilos TTK
│   │   ├── track_view.py       # Canvas interactivo: pista, regla, origen, vector, vehículo
│   │   ├── telemetry_panel.py  # Tarjetas métricas digitales en tiempo real
│   │   ├── plots_view.py       # Gráficas Matplotlib x-t y v-t sincronizadas
│   │   ├── control_panel.py    # Controles de mando, presets y validación de entradas
│   │   ├── dialogs.py          # Modales de informe científico y guía teórica
│   │   └── main_window.py      # Ventana principal e integración de componentes
│   ├── controllers/            # Capa de Coordinación (Controlador)
│   │   └── simulation_controller.py # Bucle de animación (~40 FPS) y sincronización
│   └── data/                   # Capa de Persistencia y Exportación
│       └── exporter.py         # Generador de reportes CSV con metadatos del SI
└── tests/                      # Banco de Pruebas Unitarias y de Integración
    ├── test_physics.py         # Pruebas del modelo analítico de MRU
    ├── test_state_machine.py   # Pruebas de cronómetros, pausas y transiciones
    ├── test_exporter.py        # Pruebas de exportación a CSV
    └── test_gui_integration.py # Pruebas de interfaz, eventos y diálogos
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

### 6.6. Exportación a CSV e Informe Científico
- El botón **"Ver Informe Científico"** despliega un resumen completo con tabla comparativa de magnitudes, verificación del modelo MRU y comentarios pedagógicos.
- El botón **"Exportar Datos a CSV"** guarda un archivo con las muestras reales registradas durante la simulación con metadatos científicos e intervalos de tiempo.

---

## 7. Pruebas Automatizadas y Verificación

El proyecto cuenta con una suite completa de pruebas unitarias y de integración que verifican la exactitud matemática y temporal:

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
test_initial_gui_state (test_gui_integration.TestGUIIntegration) ... ok
test_start_pause_resume_reset_cycle (test_gui_integration.TestGUIIntegration) ... ok
test_preset_selection (test_gui_integration.TestGUIIntegration) ... ok
test_dialog_creations (test_gui_integration.TestGUIIntegration) ... ok

----------------------------------------------------------------------
Ran 16 tests in 8.173s

OK
```

### Escenarios Críticos Verificados:
1. **Velocidad Positiva:** Desplazamiento correcto hacia la derecha respetando la ecuación horaria.
2. **Velocidad Negativa:** Desplazamiento hacia la izquierda con signo negativo en $\Delta x$ y distancia positiva $d$.
3. **Velocidad Nula ($v = 0$):** Vehículo en reposo estricto, sin avance ni deriva.
4. **Pausa Determinista:** El tiempo efectivo se congela completamente mientras el tiempo de pared avanza. Al reanudar no existen discontinuidades.
5. **Detección de Límite sin Desbordamiento:** Detención exacta al alcanzar $x_{\min}$ o $x_{\max}$ sin traspasar la pista ni alterar la velocidad configurada.
6. **Validación de Entradas:** Rechazo de configuraciones con $x_0$ fuera de pista o sentidos que colisionen inmediatamente.
7. **Exportador CSV:** Registro verificado de cabeceras de metadatos, columnas SI y datos numéricos empíricos.
8. **Integración GUI:** Apertura de ventanas modales, enlace de eventos de teclado y ciclos completos de vida de simulación.

---

## 8. Licencia y Créditos

Proyecto desarrollado con fines académicos y de divulgación científica para cursos de **Física General** y **Simulación Numérica** en programas de **Ingeniería de Sistemas**.
Uso libre para docencia, aprendizaje e investigación.
