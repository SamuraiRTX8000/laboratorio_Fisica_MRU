"""
Módulo de Cuadros de Diálogo: Resumen Analítico del Experimento y Guía Didáctica.

Proporciona ventanas modales diseñadas para la docencia universitaria:
1. SummaryDialog: Informe científico detallado con todas las magnitudes calculadas,
   comparación de velocidades medias (efectiva vs global), verificación de MRU y exportación.
2. TheoryGuideDialog: Guía conceptual interactiva sobre fundamentos de cinemática,
   vectores, sistema de referencia e interpretación de gráficas.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable
from .theme import Theme
from ..models.experiment_state import ExperimentSummary, MeasurementSample
from ..models.physics import TrackConfig, MRUParameters
from ..data.exporter import ExperimentDataExporter


class SummaryDialog(tk.Toplevel):
    """Ventana modal con el informe científico completo del experimento realizado."""

    def __init__(
        self,
        parent: tk.Widget,
        summary: ExperimentSummary,
        samples: list[MeasurementSample],
        track: TrackConfig,
        params: MRUParameters,
        on_export_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(parent)
        self.summary = summary
        self.samples = samples
        self.track = track
        self.params = params
        self.on_export_callback = on_export_callback

        self.title("Informe Científico y Análisis del Experimento - MRU")
        self.geometry("680x620")
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

        rows = [
            ("Límites de la pista:", f"[{self.track.x_min:.1f} m, {self.track.x_max:.1f} m] (Longitud: {self.track.total_length:.1f} m)", "Sistema de referencia"),
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

        # 2. Comprobación del Modelo de MRU y Explicación Pedagógica
        frame_analysis = tk.LabelFrame(
            scrollable_frame,
            text=" 2. Verificación Científica del Modelo MRU ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold"),
            padx=12,
            pady=10
        )
        frame_analysis.pack(fill=tk.X, pady=(0, 12))

        # Badge de verificación
        status_color = Theme.SUCCESS if self.summary.is_mru_verified else Theme.WARNING
        status_text = "✓ COMPORTAMIENTO COMPATIBLE CON MRU" if self.summary.is_mru_verified else "⚠️ DESVIACIÓN DETECTADA"

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
        self.title("Fundamentos de Cinemática - Movimiento Rectilíneo Uniforme")
        self.geometry("740x650")
        self.minsize(620, 500)
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
        tab4 = self._create_scrollable_tab(notebook, "4. Ecuación y Gráficas")
        self._populate_tab4(tab4)

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
