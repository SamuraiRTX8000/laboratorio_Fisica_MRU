"""
Módulo de Cuadros de Diálogo: Resumen Analítico del Experimento y Guía Didáctica.

Proporciona ventanas modales diseñadas para la docencia universitaria:
1. SummaryDialog: Informe científico detallado con todas las magnitudes calculadas,
   comparación de velocidades medias (efectiva vs global), verificación de MRU y exportación.
2. TheoryGuideDialog: Guía conceptual interactiva sobre fundamentos de cinemática,
   vectores, sistema de referencia e interpretación de gráficas.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import Optional, Callable, Dict, Any, List, Union
from .theme import Theme
from ..models.experiment_state import ExperimentSummary, MeasurementSample
from ..models.physics import TrackConfig, MRUParameters, MRUAParameters, FreeFallParameters
from ..data.exporter import ExperimentDataExporter


class SummaryDialog(tk.Toplevel):
    """Ventana modal con el informe científico completo del experimento realizado."""

    def __init__(
        self,
        parent: tk.Widget,
        summary: ExperimentSummary,
        samples: list[MeasurementSample],
        track: Optional[TrackConfig],
        params: Union[MRUParameters, MRUAParameters, FreeFallParameters],
        on_export_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(parent)
        self.summary = summary
        self.samples = samples
        self.track = track
        self.params = params
        self.on_export_callback = on_export_callback

        mtype = getattr(self.summary, "motion_type", "MRU")
        self.title(f"Informe Científico y Análisis del Experimento - {mtype}")
        self.geometry("700x640")
        self.minsize(580, 520)
        self.configure(bg=Theme.BG_DARK)
        self.transient(parent)
        try:
            self.grab_set()
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la vista del informe."""
        # Encabezado
        header_frame = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=12)
        header_frame.pack(fill=tk.X)

        tk.Label(
            header_frame,
            text="REPORTE DE RESULTADOS EXPERIMENTALES",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 13, "bold")
        ).pack(anchor="w")

        tk.Label(
            header_frame,
            text=f"Razón de finalización: {self.summary.termination_reason}",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", pady=(2, 0))

        # Contenedor con Scroll para el cuerpo del informe
        body_container = tk.Frame(self, bg=Theme.BG_DARK)
        body_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        canvas = tk.Canvas(body_container, bg=Theme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Theme.BG_DARK)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. Tabla de Magnitudes Cinemáticas
        frame_table = tk.LabelFrame(
            scrollable_frame,
            text=" 1. Magnitudes Físicas Registradas ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold"),
            padx=12,
            pady=10
        )
        frame_table.pack(fill=tk.X, pady=(0, 12))

        mtype = getattr(self.summary, "motion_type", "MRU")
        if mtype == "CAIDA_LIBRE":
            rows = [
                ("Sistema de referencia vertical:", "Suelo en y = 0 m (Sentido +y ascendente)", "Convención física universal"),
                ("Altura inicial (y₀):", f"{self.summary.x0:+.4f} m", "Punto de lanzamiento"),
                ("Altura final (y_final):", f"{self.summary.x_final:+.4f} m", "Punto final de la trayectoria"),
                ("Desplazamiento vertical (Δy):", f"{self.summary.displacement:+.4f} m", "Δy = y_final - y₀ (con signo)"),
                ("Distancia total recorrida (d):", f"{self.summary.distance:.4f} m", "Suma de tramos ascendente y descendente"),
                ("Velocidad inicial vertical (v₀):", f"{self.summary.configured_velocity:+.4f} m/s", "Con signo (+ arriba, - abajo)"),
                ("Aceleración de gravedad (ay):", f"{self.summary.configured_acceleration:+.4f} m/s²", "ay = -g (constante hacia abajo)"),
                ("Tiempo efectivo de vuelo (t_eff):", f"{self.summary.t_eff:.4f} s", "Duración en el aire"),
                ("Tiempo total del experimento (t_total):", f"{self.summary.t_total:.4f} s", "Tiempo de pared (incluye pausas)"),
                ("Número de pausas:", f"{self.summary.pause_count}", f"Tiempo acumulado en pausa: {self.summary.total_pause_duration:.2f} s"),
                ("Velocidad media efectiva:", f"{self.summary.v_avg_eff:+.4f} m/s", "Δy / t_eff"),
                ("Rapidez media efectiva:", f"{self.summary.s_avg_eff:.4f} m/s", "d / t_eff"),
                ("Muestras telemétricas capturadas:", f"{len(self.samples)} muestras", "Registro empírico en tiempo real"),
            ]
        elif mtype == "MRUA":
            track_str = f"[{self.track.x_min:.1f} m, {self.track.x_max:.1f} m]" if self.track else "Pista numérica"
            v_final_calc = self.summary.configured_velocity + (self.summary.configured_acceleration * self.summary.t_eff)
            rows = [
                ("Límites de la pista:", track_str, "Sistema de referencia"),
                ("Posición inicial (x₀):", f"{self.summary.x0:+.4f} m", "Punto de partida"),
                ("Posición final (x_final):", f"{self.summary.x_final:+.4f} m", "Punto de llegada"),
                ("Desplazamiento vectorial (Δx):", f"{self.summary.displacement:+.4f} m", "Δx = x_final - x₀ (con signo)"),
                ("Distancia recorrida (d):", f"{self.summary.distance:.4f} m", "Longitud total de trayectoria recorrida"),
                ("Velocidad inicial (v₀):", f"{self.summary.configured_velocity:+.4f} m/s", "Velocidad al inicio de la simulación"),
                ("Aceleración constante (a):", f"{self.summary.configured_acceleration:+.4f} m/s²", "Tasa de cambio de velocidad a = cte"),
                ("Velocidad final instantánea:", f"{v_final_calc:+.4f} m/s", "v = v₀ + a · t_eff"),
                ("Tiempo efectivo de movimiento (t_eff):", f"{self.summary.t_eff:.4f} s", "Cronómetro activo de traslación"),
                ("Tiempo total del experimento (t_total):", f"{self.summary.t_total:.4f} s", "Tiempo de pared (incluye pausas)"),
                ("Número de pausas:", f"{self.summary.pause_count}", f"Tiempo acumulado en pausa: {self.summary.total_pause_duration:.2f} s"),
                ("Velocidad media efectiva:", f"{self.summary.v_avg_eff:+.4f} m/s", "Δx / t_eff"),
                ("Velocidad media teórica:", f"{(self.summary.configured_velocity + v_final_calc)/2.0:+.4f} m/s", "v_med = (v₀ + v) / 2"),
                ("Rapidez media efectiva:", f"{self.summary.s_avg_eff:.4f} m/s", "d / t_eff"),
                ("Muestras telemétricas capturadas:", f"{len(self.samples)} muestras", "Registro empírico en tiempo real"),
            ]
        else:
            track_str = f"[{self.track.x_min:.1f} m, {self.track.x_max:.1f} m] (Longitud: {self.track.total_length:.1f} m)" if self.track else "[-50.0 m, 50.0 m]"
            rows = [
                ("Límites de la pista:", track_str, "Sistema de referencia"),
                ("Posición inicial (x₀):", f"{self.summary.x0:+.4f} m", "Punto de partida"),
                ("Posición final (x_final):", f"{self.summary.x_final:+.4f} m", "Punto de llegada"),
                ("Desplazamiento vectorial (Δx):", f"{self.summary.displacement:+.4f} m", "Δx = x_final - x₀ (con signo)"),
                ("Distancia recorrida (d):", f"{self.summary.distance:.4f} m", "Longitud de la trayectoria (escalar)"),
                ("Velocidad configurada (v):", f"{self.summary.configured_velocity:+.4f} m/s", "Constante durante el movimiento"),
                ("Rapidez configurada (|v|):", f"{self.summary.configured_speed:.4f} m/s", "Magnitud de la velocidad"),
                ("Tiempo efectivo de movimiento (t_eff):", f"{self.summary.t_eff:.4f} s", "Cronómetro activo de traslación"),
                ("Tiempo total del experimento (t_total):", f"{self.summary.t_total:.4f} s", "Tiempo de pared (incluye pausas)"),
                ("Número de pausas:", f"{self.summary.pause_count}", f"Tiempo acumulado en pausa: {self.summary.total_pause_duration:.2f} s"),
                ("Velocidad media efectiva:", f"{self.summary.v_avg_eff:+.4f} m/s", "Δx / t_eff (coincide con v en MRU)"),
                ("Rapidez media efectiva:", f"{self.summary.s_avg_eff:.4f} m/s", "d / t_eff"),
                ("Velocidad media global (con pausas):", f"{self.summary.v_avg_total:+.4f} m/s", "Δx / t_total (afectada por pausas)"),
                ("Rapidez media global (con pausas):", f"{self.summary.s_avg_total:.4f} m/s", "d / t_total"),
                ("Muestras telemétricas capturadas:", f"{len(self.samples)} muestras", "Registro empírico en tiempo real"),
            ]

        for i, (col1, col2, col3) in enumerate(rows):
            bg_row = Theme.BG_CARD if i % 2 == 0 else Theme.BG_CARD_LIGHT
            r_frame = tk.Frame(frame_table, bg=bg_row, padx=6, pady=3)
            r_frame.pack(fill=tk.X)

            tk.Label(r_frame, text=col1, bg=bg_row, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9), width=32, anchor="w").pack(side=tk.LEFT)
            tk.Label(r_frame, text=col2, bg=bg_row, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 9, "bold"), width=22, anchor="w").pack(side=tk.LEFT)
            tk.Label(r_frame, text=col3, bg=bg_row, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 8, "italic"), anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 2. Comprobación del Modelo Científico y Explicación Pedagógica
        frame_analysis = tk.LabelFrame(
            scrollable_frame,
            text=f" 2. Verificación Científica del Modelo ({mtype}) ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold"),
            padx=12,
            pady=10
        )
        frame_analysis.pack(fill=tk.X, pady=(0, 12))

        # Badge de verificación
        status_color = Theme.SUCCESS if self.summary.is_mru_verified else Theme.WARNING
        status_text = f"✓ COMPORTAMIENTO COMPATIBLE CON {mtype}" if self.summary.is_mru_verified else "⚠️ DESVIACIÓN DETECTADA"

        tk.Label(
            frame_analysis,
            text=status_text,
            bg=status_color,
            fg=Theme.TEXT_DARK,
            font=Theme.FONT_BADGE,
            padx=8,
            pady=3
        ).pack(anchor="w", pady=(0, 6))

        # Texto de explicación física
        lbl_expl = tk.Label(
            frame_analysis,
            text=self.summary.explanation,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 9),
            wraplength=600,
            justify=tk.LEFT
        )
        lbl_expl.pack(fill=tk.X, pady=(0, 6))

        # 3. Botones inferiores
        bottom_bar = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=10)
        bottom_bar.pack(fill=tk.X)

        btn_export = ttk.Button(
            bottom_bar,
            text="💾  Exportar este Experimento a CSV",
            style="Primary.TButton",
            command=self._export_csv
        )
        btn_export.pack(side=tk.LEFT)

        btn_close = ttk.Button(
            bottom_bar,
            text="Cerrar",
            style="Secondary.TButton",
            command=self.destroy
        )
        btn_close.pack(side=tk.RIGHT)

    def _export_csv(self) -> None:
        """Abre un diálogo de guardado y exporta los datos."""
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar Datos Experimentales de MRU",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile=f"experimento_mru_v{int(self.params.velocity)}.csv"
        )
        if filepath:
            try:
                ExperimentDataExporter.export_to_file(
                    filepath,
                    self.samples,
                    self.summary,
                    self.track,
                    self.params
                )
                messagebox.showinfo(
                    "Exportación Exitosa",
                    f"Datos exportados correctamente en:\n{filepath}",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror(
                    "Error al Exportar",
                    f"Ocurrió un error al guardar el archivo:\n{str(e)}",
                    parent=self
                )


class TheoryGuideDialog(tk.Toplevel):
    """Ventana interactiva con los fundamentos teóricos y didácticos de cinemática."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("Guía Teórica de Cinemática - MRU, MRUA y Caída Libre")
        self.geometry("820x680")
        self.minsize(680, 520)
        self.configure(bg=Theme.BG_DARK)
        self.transient(parent)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construye las pestañas de teoría."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Pestaña 1: Magnitudes y Vectores
        tab1 = self._create_scrollable_tab(notebook, "1. Magnitudes Físicas")
        self._populate_tab1(tab1)

        # Pestaña 2: Sistema de Referencia y Origen
        tab2 = self._create_scrollable_tab(notebook, "2. Sistema de Referencia")
        self._populate_tab2(tab2)

        # Pestaña 3: Velocidad vs Rapidez
        tab3 = self._create_scrollable_tab(notebook, "3. Velocidad y Rapidez")
        self._populate_tab3(tab3)

        # Pestaña 4: Ecuación MRU y Gráficas
        tab4 = self._create_scrollable_tab(notebook, "4. MRU y Gráficas")
        self._populate_tab4(tab4)

        # Pestaña 5: MRUA y Aceleración
        tab5 = self._create_scrollable_tab(notebook, "5. MRUA y Aceleración")
        self._populate_tab5(tab5)

        # Pestaña 6: Caída Libre y Gravedad
        tab6 = self._create_scrollable_tab(notebook, "6. Caída Libre y Gravedad")
        self._populate_tab6(tab6)

        # Pestaña 7: Catálogo de Ecuaciones y Despejes
        tab7 = self._create_scrollable_tab(notebook, "7. Ecuaciones y Despejes")
        self._populate_tab7(tab7)

        # Botón de cierre inferior
        btn_close = ttk.Button(self, text="Cerrar Guía", style="Secondary.TButton", command=self.destroy)
        btn_close.pack(pady=(0, 10))

    def _create_scrollable_tab(self, notebook: ttk.Notebook, tab_title: str) -> tk.Frame:
        """Crea un contenedor con scrollbar para el texto formativo y lo añade al notebook."""
        container = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(container, text=tab_title)

        canvas = tk.Canvas(container, bg=Theme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Theme.BG_CARD, padx=16, pady=14)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        return scrollable_frame

    def _populate_tab1(self, parent: tk.Frame) -> None:
        """Contenido sobre magnitudes físicas, escalares y vectoriales."""
        self._add_heading(parent, "Magnitudes Físicas en Cinemática")
        self._add_paragraph(
            parent,
            "En física, una magnitud es cualquier propiedad susceptible de ser medida cuantitativamente. "
            "En el estudio del movimiento rectilíneo distinguimos dos clases fundamentales de magnitudes:"
        )

        self._add_subheading(parent, "Magnitudes Escalares vs. Vectoriales")
        self._add_bullet(
            parent,
            "Magnitud Escalar:",
            "Queda completamente determinada por un número real y su correspondiente unidad de medida. "
            "No posee dirección ni sentido. Ejemplos: El tiempo t [s], la distancia recorrida d [m], y la rapidez s [m/s]."
        )
        self._add_bullet(
            parent,
            "Magnitud Vectorial:",
            "Requiere para su definición completa una magnitud (o módulo), una dirección y un sentido. "
            "En el movimiento unidimensional sobre una recta, el sentido se representa algebraicamente mediante el signo (+ o -). "
            "Ejemplos: La posición x(t) [m], el desplazamiento Δx [m], y la velocidad v [m/s]."
        )

        self._add_subheading(parent, "Unidades del Sistema Internacional (SI)")
        self._add_paragraph(
            parent,
            "Para garantizar la coherencia física de todas las fórmulas cinemáticas:\n"
            "• Longitud / Posición / Distancia: metro [m]\n"
            "• Tiempo: segundo [s]\n"
            "• Velocidad / Rapidez: metros por segundo [m/s]\n"
            "• Aceleración: metros por segundo al cuadrado [m/s²]"
        )

    def _populate_tab2(self, parent: tk.Frame) -> None:
        """Contenido sobre sistema de referencia y posición."""
        self._add_heading(parent, "Movimiento y Sistema de Referencia")
        self._add_paragraph(
            parent,
            "El movimiento no es una propiedad intrínseca de los cuerpos, sino un concepto relativo: "
            "un cuerpo se mueve respecto a un observador o marco de referencia cuando su posición cambia a lo largo del tiempo."
        )

        self._add_subheading(parent, "La Recta Numérica y el Origen (x = 0)")
        self._add_paragraph(
            parent,
            "En este simulador se utiliza una recta orientada en una dimensión:\n"
            "• Origen (x = 0): Punto arbitrario pero fundamental elegido como referencia cero.\n"
            "• Sentido Positivo (+): Hacia la derecha del origen (valores x > 0).\n"
            "• Sentido Negativo (-): Hacia la izquierda del origen (valores x < 0)."
        )

        self._add_subheading(parent, "Posición frente a Desplazamiento")
        self._add_bullet(
            parent,
            "Posición (x):",
            "Coordenada métrica donde se localiza el cuerpo en un instante dado respecto al origen x=0."
        )
        self._add_bullet(
            parent,
            "Desplazamiento (Δx):",
            "Cambio de posición experimentado entre dos instantes: Δx = x(t) - x₀. "
            "Depende exclusivamente de las posiciones inicial y final, no de la trayectoria intermedia."
        )
        self._add_bullet(
            parent,
            "Distancia (d):",
            "Longitud total de la trayectoria recorrida. Es siempre un escalar positivo (d ≥ 0)."
        )

    def _populate_tab3(self, parent: tk.Frame) -> None:
        """Contenido sobre velocidad y rapidez."""
        self._add_heading(parent, "Diferencia Crucial: Rapidez vs. Velocidad")

        self._add_subheading(parent, "Rapidez Media (Escalar)")
        self._add_formula_box(parent, "s_med = d / Δt", "d: distancia recorrida [m]  |  Δt: tiempo transcurrido [s]")
        self._add_paragraph(
            parent,
            "La rapidez media indica con qué presteza avanza el móvil a lo largo del camino, "
            "sin importar hacia dónde se dirige. Al ser el cociente de dos magnitudes estrictamente positivas, "
            "la rapidez jamás es negativa (s ≥ 0)."
        )

        self._add_subheading(parent, "Velocidad Media (Vectorial)")
        self._add_formula_box(parent, "v_med = Δx / Δt = (x - x₀) / Δt", "Δx: desplazamiento [m]  |  Δt: tiempo [s]")
        self._add_paragraph(
            parent,
            "La velocidad media informa tanto sobre la tasa de cambio de posición como sobre el sentido del avance:\n"
            "• Si v > 0: El cuerpo se desplaza en sentido positivo (hacia la derecha).\n"
            "• Si v < 0: El cuerpo se desplaza en sentido negativo (hacia la izquierda).\n"
            "• Si v = 0: El cuerpo está en reposo o regresó a su posición inicial en el intervalo."
        )

        self._add_subheading(parent, "Impacto de las Pausas en la Velocidad Media")
        self._add_paragraph(
            parent,
            "Si un vehículo se detiene (pausa), durante ese periodo su velocidad instantánea es 0 m/s. "
            "Al calcular la velocidad media considerando el tiempo de pared total (t_total), el valor medio disminuye, "
            "mientras que respecto al tiempo efectivo de movimiento (t_eff), la velocidad media coincide exactamente con la configurada."
        )

    def _populate_tab4(self, parent: tk.Frame) -> None:
        """Contenido sobre la ecuación del MRU y las gráficas."""
        self._add_heading(parent, "Movimiento Rectilíneo Uniforme (MRU)")
        self._add_paragraph(
            parent,
            "El MRU se define como aquel movimiento en el cual la velocidad del móvil permanece "
            "estrictamente constante en magnitud y dirección a lo largo de toda su trayectoria. "
            "Consecuentemente, la aceleración es nula (a = 0 m/s²)."
        )

        self._add_formula_box(parent, "x(t) = x₀ + v · t", "Ecuación Horaria de la Posición en el MRU")

        self._add_subheading(parent, "Propiedad Fundamental:")
        self._add_paragraph(
            parent,
            "En intervalos iguales de tiempo, el cuerpo experimenta desplazamientos exactamente iguales:\n"
            "Δx₁ = Δx₂ = v · Δt"
        )

        self._add_subheading(parent, "Interpretación de las Gráficas Científicas")
        self._add_bullet(
            parent,
            "Gráfica Posición - Tiempo [x(t)]:",
            "Es una función lineal recta. La pendiente geométrica de la recta representa la velocidad: "
            "pendiente m = Δx / Δt = v. Una pendiente mayor indica mayor rapidez. Una recta horizontal "
            "representa reposo (v = 0), como ocurre durante las pausas del simulador."
        )
        self._add_bullet(
            parent,
            "Gráfica Velocidad - Tiempo [v(t)]:",
            "Es una línea recta horizontal constante a la altura v. "
            "El área geométrica comprendida bajo la recta entre dos instantes de tiempo t₁ y t₂ "
            "equivale exactamente al desplazamiento realizado: Área = v · Δt = Δx."
        )

    def _populate_tab5(self, parent: tk.Frame) -> None:
        """Contenido sobre Movimiento Rectilíneo Uniformemente Acelerado (MRUA)."""
        self._add_heading(parent, "Movimiento Uniformemente Acelerado (MRUA)")
        self._add_paragraph(
            parent,
            "El MRUA es aquel movimiento rectilíneo en el cual la aceleración permanece constante "
            "a lo largo de todo el intervalo (a = constante ≠ 0). Por ende, la velocidad cambia a un ritmo "
            "fijo y predecible en cada segundo de movimiento."
        )

        self._add_subheading(parent, "Concepto y Ecuación de la Aceleración")
        self._add_formula_box(parent, "a = Δv / Δt = (v - v₀) / t", "Aceleración Constante [m/s²]")
        self._add_paragraph(
            parent,
            "La aceleración es una magnitud vectorial que cuantifica la rapidez y el sentido con que varía "
            "la velocidad. Sus unidades fundamentales en el SI son metros por segundo al cuadrado [m/s²]."
        )

        self._add_subheading(parent, "Signo de la Aceleración vs. Rapidez (¡Distinción Fundamental!)")
        self._add_bullet(
            parent,
            "Aceleración Positiva (a > 0):",
            "Apunta en el sentido positivo (+x). Si la velocidad es positiva (v > 0), el móvil acelera "
            "(aumenta su rapidez). Pero si la velocidad es negativa (v < 0), la aceleración positiva "
            "hace que el móvil frene hasta detenerse y luego comience a avanzar hacia la derecha."
        )
        self._add_bullet(
            parent,
            "Aceleración Negativa (a < 0):",
            "Apunta en el sentido negativo (-x). No significa necesariamente 'frenar'. "
            "Si v > 0, el móvil desacelera hasta detenerse. Pero si v < 0, ¡el móvil aumenta su rapidez "
            "hacia la izquierda! Regla física: Si 'v' y 'a' tienen el mismo signo, el cuerpo gana rapidez; "
            "si tienen signos opuestos, pierde rapidez."
        )
        self._add_bullet(
            parent,
            "Frenado e Inversión de Sentido:",
            "Si un móvil posee velocidad inicial hacia adelante (v₀ > 0) y aceleración opuesta (a < 0), "
            "su velocidad desciende linealmente hasta anularse por completo (v = 0) en el instante "
            "t_inv = -v₀ / a. Si la aceleración persiste, el cuerpo comienza a retroceder, aumentando su "
            "rapidez en sentido contrario."
        )

        self._add_subheading(parent, "Gráficas Características del MRUA")
        self._add_bullet(
            parent,
            "Posición vs. Tiempo [x-t]:",
            "Es una curva parabólica: x(t) = x₀ + v₀·t + ½·a·t². La concavidad apunta hacia arriba si a > 0 "
            "y hacia abajo si a < 0. El vértice de la parábola representa el instante en que v = 0."
        )
        self._add_bullet(
            parent,
            "Velocidad vs. Tiempo [v-t]:",
            "Es una línea recta con pendiente m = a. Cruza el eje horizontal v = 0 en el instante de inversión."
        )
        self._add_bullet(
            parent,
            "Aceleración vs. Tiempo [a-t]:",
            "Es una recta horizontal constante. El área bajo esta recta entre t₁ y t₂ representa el cambio total "
            "de velocidad: Área = a · Δt = Δv."
        )

    def _populate_tab6(self, parent: tk.Frame) -> None:
        """Contenido sobre Caída Libre y Lanzamiento Vertical."""
        self._add_heading(parent, "Caída Libre y Lanzamiento Vertical")
        self._add_paragraph(
            parent,
            "La caída libre y el lanzamiento vertical son aplicaciones directas del MRUA en una dimensión vertical, "
            "donde la aceleración constante es provocada por la atracción gravitatoria del planeta (g)."
        )

        self._add_subheading(parent, "Convención de Signos Física Universal")
        self._add_bullet(
            parent,
            "Eje Vertical (+y hacia arriba):",
            "El origen y = 0 m se sitúa en la superficie del suelo. Posiciones por encima del suelo son y > 0."
        )
        self._add_bullet(
            parent,
            "Vector Gravedad (a = -g):",
            "La aceleración gravitatoria siempre apunta hacia el centro del planeta (hacia abajo). Por tanto, "
            "en las ecuaciones cartesianas con eje ascendente, a = -g (donde g = 9.81 m/s² en la Tierra, "
            "1.62 m/s² en la Luna y 3.71 m/s² en Marte)."
        )

        self._add_subheading(parent, "Ecuaciones Horarias Verticales")
        self._add_formula_box(parent, "y(t) = y₀ + v₀ · t - ½ · g · t²", "Posición / Altura [m]")
        self._add_formula_box(parent, "v(t) = v₀ - g · t", "Velocidad Vertical Instantánea [m/s]")
        self._add_formula_box(parent, "v² = v₀² - 2 · g · (y - y₀)", "Ecuación de Torricelli Vertical")

        self._add_subheading(parent, "Puntos Notables del Lanzamiento Vertical")
        self._add_bullet(
            parent,
            "Altura Máxima (h_máx):",
            "Se alcanza cuando la velocidad vertical se anula momentáneamente (vy = 0). "
            "Fórmula: h_máx = y₀ + v₀² / (2 · g)."
        )
        self._add_bullet(
            parent,
            "Tiempo de Subida (t_subida):",
            "Tiempo necesario para que la gravedad frene el ascenso: t_subida = v₀ / g."
        )
        self._add_bullet(
            parent,
            "Tiempo de Vuelo Simétrico:",
            "Tiempo para regresar a la altura de disparo (y = y₀): t_vuelo = 2 · v₀ / g."
        )
        self._add_bullet(
            parent,
            "Impacto contra el Suelo (y = 0):",
            "Se resuelve haciendo y = 0: t_impacto = (v₀ + √(v₀² + 2·g·y₀)) / g. "
            "La velocidad en ese instante apunta hacia abajo: v_impacto = -√(v₀² + 2·g·y₀)."
        )

    def _populate_tab7(self, parent: tk.Frame) -> None:
        """Catálogo didáctico de ecuaciones y estrategias de despeje."""
        self._add_heading(parent, "Estrategia para Resolver Problemas de Cinemática")
        self._add_paragraph(
            parent,
            "Todo problema de cinemática con aceleración constante involucra cinco variables fundamentales:\n"
            "• v₀ : Velocidad inicial\n"
            "• v  : Velocidad final\n"
            "• a  : Aceleración constante\n"
            "• t  : Tiempo transcurrido\n"
            "• Δx : Desplazamiento\n\n"
            "Cada ecuación fundamental relaciona exactamente cuatro de estas variables, omitiendo una de ellas. "
            "La clave para resolver cualquier ejercicio consiste en identificar cuál variable no interviene en el enunciado:"
        )

        self._add_subheading(parent, "Cuadro de Selección de Ecuaciones")
        self._add_bullet(
            parent,
            "Sin Desplazamiento (no se conoce ni se busca Δx):",
            "Usa: v = v₀ + a · t   ⇒   Despejes: v₀ = v - a·t  |  a = (v - v₀)/t  |  t = (v - v₀)/a"
        )
        self._add_bullet(
            parent,
            "Sin Tiempo (no se conoce ni se busca t):",
            "Usa Torricelli: v² = v₀² + 2 · a · Δx   ⇒   v = ±√(v₀² + 2aΔx)  |  Δx = (v² - v₀²)/(2a)"
        )
        self._add_bullet(
            parent,
            "Sin Velocidad Final (no se conoce ni se busca v):",
            "Usa: Δx = v₀ · t + ½ · a · t²   ⇒   x = x₀ + v₀·t + ½·a·t²"
        )
        self._add_bullet(
            parent,
            "Sin Aceleración (no se conoce ni se busca a):",
            "Usa Velocidad Media: Δx = ½ · (v₀ + v) · t   ⇒   v_med = (v₀ + v) / 2"
        )

        self._add_subheading(parent, "Resolución de la Ecuación Cuadrática del Tiempo")
        self._add_formula_box(parent, "½ · a · t² + v₀ · t - Δx = 0", "Forma estándar A·t² + B·t + C = 0")
        self._add_paragraph(
            parent,
            "Al despejar el tiempo 't' conociendo Δx, v₀ y 'a', se obtiene una ecuación de segundo grado. "
            "Sus soluciones se analizan físicamente según el discriminante Δ = B² - 4AC:\n"
            "• Si Δ < 0: Raíces complejas. El cuerpo nunca alcanza esa coordenada con esa aceleración.\n"
            "• Una raíz positiva y una negativa: Se descarta la raíz negativa (corresponde a instantes anteriores a t = 0).\n"
            "• Dos raíces positivas: Ocurre en frenado y retroceso. La menor es el tiempo de ida; la mayor es el tiempo en que vuelve a cruzar esa posición tras invertir su marcha."
        )

    def _add_heading(self, parent: tk.Frame, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 12, "bold")
        ).pack(anchor="w", pady=(4, 6))

    def _add_subheading(self, parent: tk.Frame, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(anchor="w", pady=(8, 4))

    def _add_paragraph(self, parent: tk.Frame, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9),
            wraplength=640,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(2, 4))

    def _add_bullet(self, parent: tk.Frame, title: str, content: str) -> None:
        frame = tk.Frame(parent, bg=Theme.BG_CARD)
        frame.pack(fill=tk.X, pady=3)

        tk.Label(
            frame,
            text="• " + title,
            bg=Theme.BG_CARD,
            fg=Theme.ACCENT,
            font=(Theme.FONT_FAMILY, 9, "bold")
        ).pack(anchor="w")

        tk.Label(
            frame,
            text=content,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9),
            wraplength=620,
            justify=tk.LEFT
        ).pack(anchor="w", padx=(14, 0))

    def _add_formula_box(self, parent: tk.Frame, formula: str, subtitle: str) -> None:
        box = tk.Frame(parent, bg=Theme.BG_CARD_LIGHT, padx=12, pady=8)
        box.pack(fill=tk.X, pady=6)

        tk.Label(
            box,
            text=formula,
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.PRIMARY,
            font=Theme.FONT_MONO_LARGE
        ).pack(anchor="center")

        tk.Label(
            box,
            text=subtitle,
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "italic")
        ).pack(anchor="center", pady=(2, 0))


class SessionManagerDialog(tk.Toplevel):
    """
    Diálogo para gestionar, visualizar y conmutar sesiones experimentales almacenadas.
    Permite retomar sesiones previas, consultar historial y crear nuevas sesiones.
    """

    def __init__(
        self,
        parent: tk.Widget,
        repository,
        on_session_switched: Optional[Callable[[Any], None]] = None,
        on_export_session_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.on_session_switched = on_session_switched
        self.on_export_session_callback = on_export_session_callback

        self.title("Gestor de Sesiones Experimentales Científicas")
        self.geometry("800x480")
        self.minsize(680, 380)
        self.configure(bg=Theme.BG_DARK)
        self.transient(parent)
        try:
            self.grab_set()
        except Exception:
            pass

        self._build_ui()
        self._load_sessions_list()

    def _build_ui(self) -> None:
        """Construye los componentes de la interfaz de sesiones."""
        # Encabezado
        header = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=12)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="HISTORIAL Y GESTIÓN DE SESIONES EXPERIMENTALES",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 12, "bold")
        ).pack(anchor="w")

        self.lbl_active_info = tk.Label(
            header,
            text=f"Sesión Activa Actual: {self.repository.active_session.session_id}",
            bg=Theme.BG_CARD,
            fg=Theme.SUCCESS,
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        self.lbl_active_info.pack(anchor="w", pady=(2, 0))

        # Contenedor central con tabla Treeview
        tree_frame = tk.Frame(self, bg=Theme.BG_DARK, padx=16, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("session_id", "status", "started_at", "exp_count", "obs_count", "notes")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        self.tree.heading("session_id", text="ID de Sesión")
        self.tree.heading("status", text="Estado")
        self.tree.heading("started_at", text="Fecha de Inicio")
        self.tree.heading("exp_count", text="Experimentos")
        self.tree.heading("obs_count", text="Observaciones")
        self.tree.heading("notes", text="Notas")

        self.tree.column("session_id", width=180, anchor="w")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("started_at", width=140, anchor="center")
        self.tree.column("exp_count", width=90, anchor="center")
        self.tree.column("obs_count", width=100, anchor="center")
        self.tree.column("notes", width=160, anchor="w")

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Botonera inferior
        btn_bar = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=10)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_activate = ttk.Button(
            btn_bar,
            text="✓ Retomar / Activar Sesión",
            style="Primary.TButton",
            command=self._on_activate_selected
        )
        btn_activate.pack(side=tk.LEFT, padx=(0, 6))

        btn_export = ttk.Button(
            btn_bar,
            text="📦 Exportar Dataset de Esta Sesión",
            style="Secondary.TButton",
            command=self._on_export_selected
        )
        btn_export.pack(side=tk.LEFT, padx=(0, 6))

        btn_new = ttk.Button(
            btn_bar,
            text="➕ Iniciar Nueva Sesión",
            style="Success.TButton",
            command=self._on_create_new_session
        )
        btn_new.pack(side=tk.LEFT, padx=(0, 6))

        btn_close = ttk.Button(
            btn_bar,
            text="Cerrar",
            style="Secondary.TButton",
            command=self.destroy
        )
        btn_close.pack(side=tk.RIGHT)

    def _load_sessions_list(self) -> None:
        """Carga y visualiza todas las sesiones en el Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        sessions = self.repository.list_all_sessions()
        active_id = self.repository.active_session.session_id

        for s_id in reversed(sessions):
            meta = self.repository.get_session_metadata(s_id)
            if not meta:
                continue

            sess_info = meta.get("session", {})
            is_active = (s_id == active_id)
            status_str = "● ACTIVA" if is_active else "Archivada"
            started_raw = sess_info.get("session_started_at", "")
            started_clean = started_raw[:19].replace("T", " ") if started_raw else "—"
            exp_c = meta.get("experiment_count", 0)
            obs_c = meta.get("observation_count", 0)
            notes_str = sess_info.get("notes", "")

            item_id = self.tree.insert(
                "",
                "end",
                values=(s_id, status_str, started_clean, exp_c, obs_c, notes_str)
            )
            if is_active:
                self.tree.selection_set(item_id)

    def _on_activate_selected(self) -> None:
        """Cambia la sesión activa a la seleccionada en la tabla."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Seleccione una sesión de la lista para activar.", parent=self)
            return

        values = self.tree.item(selected[0], "values")
        sess_id = values[0]
        if sess_id == self.repository.active_session.session_id:
            messagebox.showinfo("Información", f"La sesión {sess_id} ya es la sesión activa actual.", parent=self)
            return

        try:
            sess = self.repository.switch_to_session(sess_id)
            self.lbl_active_info.config(text=f"Sesión Activa Actual: {sess.session_id}")
            self._load_sessions_list()
            if self.on_session_switched:
                self.on_session_switched(sess)
            messagebox.showinfo(
                "Sesión Activada",
                f"Se ha retomado exitosamente la sesión:\n{sess_id}\n\n"
                f"Experimentos registrados: {sess.experiment_count}\n"
                f"Observaciones acumuladas: {sess.observation_count}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cambiar de sesión:\n{str(e)}", parent=self)

    def _on_export_selected(self) -> None:
        """Dispara la exportación de la sesión seleccionada."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Seleccione una sesión para exportar.", parent=self)
            return
        values = self.tree.item(selected[0], "values")
        sess_id = values[0]
        if self.on_export_session_callback:
            self.on_export_session_callback(sess_id)

    def _on_create_new_session(self) -> None:
        """Crea una nueva sesión solicitando notas opcionales."""
        notes = simpledialog.askstring(
            "Nueva Sesión Experimental",
            "Ingrese una descripción o notas para la nueva sesión (opcional):",
            parent=self
        )
        if notes is not None:
            sess = self.repository.create_new_session(notes=notes)
            self.lbl_active_info.config(text=f"Sesión Activa Actual: {sess.session_id}")
            self._load_sessions_list()
            if self.on_session_switched:
                self.on_session_switched(sess)
            messagebox.showinfo(
                "Nueva Sesión Creada",
                f"Se ha iniciado la nueva sesión:\n{sess.session_id}",
                parent=self
            )
