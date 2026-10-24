"""
Módulo del Visor Científico Avanzado de Gráficas Cinemáticas en Detalle.

Proporciona una ventana de gran formato dedicada a la inspección analítica profunda
de las gráficas en el plano cartesiano (X, Y):
- Visualización ampliada de alta resolución con barra de herramientas de navegación
  (zoom rectangular, desplazamiento/pan, restablecer vista, guardar figura en alta definición).
- Anotaciones geométricas de rigor en el plano:
    * Triángulo de cálculo de pendiente (m = Delta x / Delta t = v).
    * Regiones de pausa sombreadas con indicación de duración e inmovilidad.
    * Área sombreada bajo la curva v(t) representando el desplazamiento Delta x.
    * Coordenadas exactas en puntos inicial, final y de transición.
- Telemetría dinámica al mover el cursor (hover) con cruz de mira (crosshair).
- Pestaña con tabla de puntos notables del experimento.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional, Tuple
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

from .theme import Theme
from ..models.experiment_state import MeasurementSample, ExperimentSummary
from ..models.physics import TrackConfig, MRUParameters


class DetailedPlotViewer(tk.Toplevel):
    """Ventana de inspección detallada y ampliación de gráficas cinemáticas."""

    def __init__(
        self,
        parent: tk.Widget,
        samples: List[MeasurementSample],
        summary: ExperimentSummary,
        track: TrackConfig,
        params: MRUParameters
    ) -> None:
        super().__init__(parent)
        self.samples = samples
        self.summary = summary
        self.track = track
        self.params = params

        self.title("Visor Científico Avanzado: Plano Cinemático en Detalle (MRU)")
        self.geometry("1180x820")
        self.minsize(980, 680)
        self.configure(bg=Theme.BG_DARK)
        self.transient(parent)

        # Variables de configuración visual
        self.view_mode_var = tk.StringVar(value="dual")      # "dual", "pos", "vel"
        self.time_mode_var = tk.StringVar(value="total")     # "total" o "eff"
        self.show_slope_var = tk.BooleanVar(value=True)      # Mostrar triángulo de pendiente
        self.show_pauses_var = tk.BooleanVar(value=True)     # Sombrear pausas
        self.show_integral_var = tk.BooleanVar(value=True)   # Sombrear área bajo la curva
        self.show_minor_grid_var = tk.BooleanVar(value=True) # Cuadrícula fina
        self.show_crosshair_var = tk.BooleanVar(value=True)  # Cruz de mira interactiva

        # Referencias a elementos de cursor y líneas guía
        self._crosshair_vlines = []
        self._crosshair_hlines = []

        self._build_ui()
        self._plot_graphs()

    def _build_ui(self) -> None:
        """Construye la estructura de la ventana."""
        # --- ENCABEZADO SUPERIOR ---
        header_frame = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=8)
        header_frame.pack(fill=tk.X)

        title_box = tk.Frame(header_frame, bg=Theme.BG_CARD)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="🔍 ANÁLISIS DETALLADO DEL PLANO CINEMÁTICO (MRU)",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 12, "bold")
        ).pack(anchor="w")

        info_text = (
            f"x₀ = {self.summary.x0:+.2f} m  |  v_conf = {self.summary.configured_velocity:+.2f} m/s  |  "
            f"x_final = {self.summary.x_final:+.2f} m  |  Δx = {self.summary.displacement:+.2f} m  |  "
            f"t_eff = {self.summary.t_eff:.2f} s  |  t_total = {self.summary.t_total:.2f} s  |  "
            f"Pausas: {self.summary.pause_count}"
        )
        tk.Label(
            title_box,
            text=info_text,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", pady=(2, 0))

        # Botón de guardar figura
        btn_save = ttk.Button(
            header_frame,
            text="💾 Exportar Gráfica en Alta Resolución",
            style="Primary.TButton",
            command=self._export_figure_dialog
        )
        btn_save.pack(side=tk.RIGHT, padx=4)

        # --- BANNER DE TELEMETRÍA DINÁMICA DEL CURSOR ---
        self.cursor_banner = tk.Frame(self, bg=Theme.BG_CANVAS, padx=14, pady=6, highlightthickness=1, highlightbackground=Theme.TRACK_BORDER)
        self.cursor_banner.pack(fill=tk.X, padx=10, pady=(6, 2))

        self.lbl_cursor_status = tk.Label(
            self.cursor_banner,
            text="📍 Posicione el cursor sobre la gráfica para inspeccionar coordenadas con precisión micrométrica...",
            bg=Theme.BG_CANVAS,
            fg=Theme.PRIMARY,
            font=Theme.FONT_MONO
        )
        self.lbl_cursor_status.pack(side=tk.LEFT)

        # --- BARRA DE OPCIONES Y CONTROLES DEL VISOR ---
        ctrl_bar = tk.Frame(self, bg=Theme.BG_CARD, padx=10, pady=6)
        ctrl_bar.pack(fill=tk.X, padx=10, pady=4)

        # Selector de vista de planos
        tk.Label(ctrl_bar, text="Plano:", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))

        cmb_view = ttk.Combobox(
            ctrl_bar,
            textvariable=self.view_mode_var,
            values=["Dual: x(t) y v(t)", "Solo Posición x(t)", "Solo Velocidad v(t)"],
            state="readonly",
            width=18
        )
        cmb_view.current(0)
        cmb_view.pack(side=tk.LEFT, padx=(0, 12))
        cmb_view.bind("<<ComboboxSelected>>", lambda e: self._on_controls_changed())

        # Selector de eje de tiempo
        tk.Label(ctrl_bar, text="Eje Temporal:", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        rb_tot = tk.Radiobutton(
            ctrl_bar, text="Tiempo Global (con pausas)", variable=self.time_mode_var, value="total",
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        rb_tot.pack(side=tk.LEFT, padx=2)

        rb_eff = tk.Radiobutton(
            ctrl_bar, text="Tiempo Efectivo (solo MRU)", variable=self.time_mode_var, value="eff",
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        rb_eff.pack(side=tk.LEFT, padx=2)

        # Separador visual
        tk.Frame(ctrl_bar, width=1, height=20, bg=Theme.TRACK_BORDER).pack(side=tk.LEFT, padx=8)

        # Checkboxes didácticos
        chk_slope = tk.Checkbutton(
            ctrl_bar, text="Pendiente / Medidas", variable=self.show_slope_var,
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        chk_slope.pack(side=tk.LEFT, padx=4)

        chk_pauses = tk.Checkbutton(
            ctrl_bar, text="Zonas de Pausa", variable=self.show_pauses_var,
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        chk_pauses.pack(side=tk.LEFT, padx=4)

        chk_int = tk.Checkbutton(
            ctrl_bar, text="Área Integral", variable=self.show_integral_var,
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        chk_int.pack(side=tk.LEFT, padx=4)

        chk_grid = tk.Checkbutton(
            ctrl_bar, text="Malla Fina", variable=self.show_minor_grid_var,
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        chk_grid.pack(side=tk.LEFT, padx=4)

        chk_cross = tk.Checkbutton(
            ctrl_bar, text="Mira del Cursor", variable=self.show_crosshair_var,
            bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, activeforeground=Theme.PRIMARY,
            command=self._on_controls_changed, font=(Theme.FONT_FAMILY, 8)
        )
        chk_cross.pack(side=tk.LEFT, padx=4)

        # --- NOTEBOOK CON PESTAÑAS (GRÁFICA Y TABLA DE PUNTOS) ---
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # Pestaña 1: Gráficas en el plano cartesiano
        tab_plot = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(tab_plot, text=" 📈 Plano Cartesiano y Medidas ")
        self._build_plot_tab(tab_plot)

        # Pestaña 2: Tabla de Puntos Notables
        tab_table = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(tab_table, text=" 📋 Tabla de Puntos Notables del Experimento ")
        self._build_table_tab(tab_table)

    def _build_plot_tab(self, parent: tk.Frame) -> None:
        """Construye el lienzo Matplotlib y la barra de navegación dentro de la pestaña."""
        # Figura Matplotlib de gran tamaño
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor(Theme.BG_CARD)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(bg=Theme.BG_CARD)
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Barra de herramientas de navegación oficial de Matplotlib (Zoom, Pan, Save)
        toolbar_frame = tk.Frame(parent, bg=Theme.BG_CARD)
        toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.configure(background=Theme.BG_CARD)
        for child in self.toolbar.winfo_children():
            try:
                child.configure(background=Theme.BG_CARD)
            except Exception:
                pass
        self.toolbar.update()

        # Conectar eventos interactivos de mouse
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _build_table_tab(self, parent: tk.Frame) -> None:
        """Construye la tabla interactiva de puntos y medidas notables."""
        container = tk.Frame(parent, bg=Theme.BG_CARD, padx=12, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        columns = ("#", "Tipo de Evento", "t_total (s)", "t_eff (s)", "Posición x (m)", "Δx (m)", "Distancia d (m)", "Velocidad v (m/s)", "Rapidez |v| (m/s)")
        tree = ttk.Treeview(container, columns=columns, show="headings", height=18)

        col_widths = {
            "#": 45,
            "Tipo de Evento": 180,
            "t_total (s)": 90,
            "t_eff (s)": 90,
            "Posición x (m)": 110,
            "Δx (m)": 90,
            "Distancia d (m)": 110,
            "Velocidad v (m/s)": 120,
            "Rapidez |v| (m/s)": 120,
        }
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), anchor="center")

        scroll_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)
        scroll_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscrollcommand=scroll_x.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Poblar con eventos clave
        notable_events = self._extract_notable_points()
        for idx, ev in enumerate(notable_events, start=1):
            tree.insert("", tk.END, values=(
                idx,
                ev["event"],
                f"{ev['t_total']:.3f}",
                f"{ev['t_eff']:.3f}",
                f"{ev['position']:+.3f}",
                f"{ev['displacement']:+.3f}",
                f"{ev['distance']:.3f}",
                f"{ev['velocity']:+.3f}",
                f"{ev['speed']:.3f}"
            ))

    def _extract_notable_points(self) -> List[dict]:
        """Extrae los instantes críticos: inicio, inicio/fin de cada pausa y punto final."""
        if not self.samples:
            return []

        events = []
        # Punto 1: Inicio
        s0 = self.samples[0]
        events.append({
            "event": "Inicio del Experimento",
            "t_total": s0.t_total,
            "t_eff": s0.t_eff,
            "position": s0.position,
            "displacement": s0.displacement,
            "distance": s0.distance,
            "velocity": s0.velocity,
            "speed": s0.speed
        })

        # Detectar transiciones de pausa
        in_pause = False
        pause_num = 0
        for i in range(1, len(self.samples)):
            prev = self.samples[i - 1]
            curr = self.samples[i]

            if curr.status == "PAUSADO" and not in_pause:
                in_pause = True
                pause_num += 1
                events.append({
                    "event": f"Inicio de Pausa #{pause_num}",
                    "t_total": curr.t_total,
                    "t_eff": curr.t_eff,
                    "position": curr.position,
                    "displacement": curr.displacement,
                    "distance": curr.distance,
                    "velocity": 0.0,
                    "speed": 0.0
                })
            elif curr.status == "EN MOVIMIENTO" and in_pause:
                in_pause = False
                events.append({
                    "event": f"Reanudación tras Pausa #{pause_num}",
                    "t_total": curr.t_total,
                    "t_eff": curr.t_eff,
                    "position": curr.position,
                    "displacement": curr.displacement,
                    "distance": curr.distance,
                    "velocity": curr.velocity,
                    "speed": curr.speed
                })

        # Punto Final
        sf = self.samples[-1]
        events.append({
            "event": f"Final del Experimento ({self.summary.termination_reason[:25]}...)",
            "t_total": sf.t_total,
            "t_eff": sf.t_eff,
            "position": sf.position,
            "displacement": sf.displacement,
            "distance": sf.distance,
            "velocity": sf.velocity,
            "speed": sf.speed
        })

        return events

    def _on_controls_changed(self) -> None:
        """Refresca la gráfica cuando el usuario cambia cualquier parámetro visual."""
        self._plot_graphs()

    def _plot_graphs(self) -> None:
        """Dibuja las gráficas en alta resolución con todas las medidas físicas."""
        self.fig.clf()
        self._crosshair_vlines.clear()
        self._crosshair_hlines.clear()

        if not self.samples:
            ax = self.fig.add_subplot(1, 1, 1)
            ax.set_facecolor(Theme.BG_CANVAS)
            ax.text(0.5, 0.5, "No hay muestras experimentales registradas aún.",
                    color=Theme.TEXT_MUTED, ha="center", va="center", fontsize=12)
            self.canvas.draw()
            return

        use_total = (self.time_mode_var.get() == "total")
        view_mode = self.view_mode_var.get()

        times = np.array([s.t_total if use_total else s.t_eff for s in self.samples])
        positions = np.array([s.position for s in self.samples])
        velocities = np.array([s.velocity for s in self.samples])
        statuses = [s.status for s in self.samples]

        time_axis_label = "Tiempo Total de Observación t [segundos]" if use_total else "Tiempo Efectivo de Traslación t_eff [segundos]"

        # Detectar pausas en el arreglo de tiempos
        pause_intervals = self._find_pause_intervals(times, statuses) if use_total else []

        # Determinar disposición de subgráficas
        if "Dual" in view_mode:
            self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.10, hspace=0.38)
            ax_pos = self.fig.add_subplot(2, 1, 1)
            ax_vel = self.fig.add_subplot(2, 1, 2, sharex=ax_pos)
            self._render_position_plane(ax_pos, times, positions, pause_intervals, xlabel=None)
            self._render_velocity_plane(ax_vel, times, velocities, pause_intervals, xlabel=time_axis_label)
            self.axes_list = [ax_pos, ax_vel]
        elif "Posición" in view_mode:
            self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.11)
            ax_pos = self.fig.add_subplot(1, 1, 1)
            self._render_position_plane(ax_pos, times, positions, pause_intervals, xlabel=time_axis_label)
            self.axes_list = [ax_pos]
        else:  # Solo Velocidad
            self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.11)
            ax_vel = self.fig.add_subplot(1, 1, 1)
            self._render_velocity_plane(ax_vel, times, velocities, pause_intervals, xlabel=time_axis_label)
            self.axes_list = [ax_vel]

        self.canvas.draw()

    def _render_position_plane(
        self,
        ax,
        times: np.ndarray,
        positions: np.ndarray,
        pause_intervals: List[Tuple[float, float, float]],
        xlabel: Optional[str]
    ) -> None:
        """Renderiza el plano Posición vs. Tiempo con cotas, pendiente y anotaciones."""
        self._apply_axis_styling(ax, "PLANO POSICIÓN vs. TIEMPO: x(t) [Pendiente = Velocidad]", "Posición x [m]", xlabel)

        # 1. Curva principal x(t)
        ax.plot(times, positions, color=Theme.PRIMARY, linewidth=2.8, label="Posición x(t)", zorder=4)

        # 2. Puntos notables (Inicio y Fin)
        t0, x0 = times[0], positions[0]
        tf, xf = times[-1], positions[-1]

        ax.scatter([t0], [x0], color="#eab308", s=60, zorder=6, edgecolors="#ffffff", linewidth=1.5)
        ax.annotate(
            f"Punto Inicial\n(t={t0:.2f}s, x₀={x0:+.2f}m)",
            xy=(t0, x0), xytext=(t0 + 0.3, x0 + (5 if xf >= x0 else -10)),
            color="#fef08a", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc=Theme.BG_CARD, ec="#eab308", lw=1.2),
            arrowprops=dict(arrowstyle="->", color="#eab308", lw=1.2)
        )

        ax.scatter([tf], [xf], color="#f43f5e", s=60, zorder=6, edgecolors="#ffffff", linewidth=1.5)
        ax.annotate(
            f"Punto Final\n(t={tf:.2f}s, x_f={xf:+.2f}m)\nΔx={xf - x0:+.2f}m",
            xy=(tf, xf), xytext=(tf - (times[-1] * 0.18), xf + (5 if xf <= x0 else -12)),
            color="#fecdd3", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc=Theme.BG_CARD, ec="#f43f5e", lw=1.2),
            arrowprops=dict(arrowstyle="->", color="#f43f5e", lw=1.2)
        )

        # 3. Línea de referencia origen x = 0 y posición inicial
        ax.axhline(0, color="#64748b", linestyle="-", linewidth=1.0, alpha=0.6, label="Origen (x = 0)")
        ax.axhline(x0, color="#eab308", linestyle=":", linewidth=1.2, alpha=0.7, label=f"Ref x₀ = {x0:+.1f}m")

        # 4. Zonas de pausa sombreadas
        if self.show_pauses_var.get() and pause_intervals:
            for idx, (t_start, t_end, dur) in enumerate(pause_intervals, start=1):
                ax.axvspan(t_start, t_end, color="#f59e0b", alpha=0.20, zorder=2)
                mid_t = (t_start + t_end) / 2
                ax.text(
                    mid_t, ax.get_ylim()[0] + 2,
                    f"[Pausa #{idx}]\nΔt={dur:.2f}s\n(m = 0)",
                    color="#fde047", fontsize=7, fontweight="bold", ha="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=Theme.BG_CARD, ec="#d97706", alpha=0.85)
                )

        # 5. Triángulo de cálculo de pendiente (m = Delta x / Delta t = v)
        if self.show_slope_var.get() and len(times) > 1 and abs(self.params.velocity) > 1e-4:
            self._draw_slope_triangle(ax, times, positions)

        ax.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)

    def _render_velocity_plane(
        self,
        ax,
        times: np.ndarray,
        velocities: np.ndarray,
        pause_intervals: List[Tuple[float, float, float]],
        xlabel: Optional[str]
    ) -> None:
        """Renderiza el plano Velocidad vs. Tiempo con cotas, integral de área y pausas."""
        self._apply_axis_styling(ax, "PLANO VELOCIDAD vs. TIEMPO: v(t) [Área bajo la curva = Desplazamiento Δx]", "Velocidad v [m/s]", xlabel)

        # 1. Curva principal v(t)
        ax.plot(times, velocities, color=Theme.SUCCESS, linewidth=2.6, label="Velocidad v(t)", zorder=4)

        # 2. Línea cero y línea v_configurada
        ax.axhline(0, color="#64748b", linestyle="-", linewidth=1.0, alpha=0.6)
        v_conf = self.params.velocity
        ax.axhline(v_conf, color="#f59e0b", linestyle=":", linewidth=1.2, alpha=0.8, label=f"v_conf = {v_conf:+.1f} m/s")

        # 3. Área bajo la curva sombreada (Integral)
        if self.show_integral_var.get() and len(times) > 1:
            ax.fill_between(times, velocities, 0, color=Theme.SUCCESS, alpha=0.20, hatch="//", label="Área = Desplazamiento Δx", zorder=3)
            # Anotación explicativa de la integral
            mid_idx = len(times) // 2
            t_mid = times[mid_idx]
            v_mid = velocities[mid_idx]
            ax.annotate(
                f"Área = ∫ v dt = Δx\nΔx = {self.summary.displacement:+.2f} m",
                xy=(t_mid, v_mid / 2 if abs(v_mid) > 1e-3 else v_conf / 2),
                xytext=(t_mid + 0.3, (v_conf * 0.7) if abs(v_conf) > 1e-3 else 2.0),
                color="#86efac", fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc=Theme.BG_CARD, ec=Theme.SUCCESS, lw=1.2),
                arrowprops=dict(arrowstyle="->", color=Theme.SUCCESS, lw=1.2)
            )

        # 4. Zonas de pausa sombreadas
        if self.show_pauses_var.get() and pause_intervals:
            for idx, (t_start, t_end, dur) in enumerate(pause_intervals, start=1):
                ax.axvspan(t_start, t_end, color="#f59e0b", alpha=0.20, zorder=2)
                mid_t = (t_start + t_end) / 2
                ax.text(
                    mid_t, 0, f"v = 0 m/s\n({dur:.2f}s)",
                    color="#fde047", fontsize=7, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=Theme.BG_CARD, ec="#d97706", alpha=0.85)
                )

        ax.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)

    def _draw_slope_triangle(self, ax, times: np.ndarray, positions: np.ndarray) -> None:
        """Dibuja en el plano un triángulo pedagógico para ilustrar la pendiente de la recta."""
        # Buscar un segmento representativo continuo sin pausas
        valid_indices = []
        for i, s in enumerate(self.samples):
            if s.status == "EN MOVIMIENTO":
                valid_indices.append(i)

        if len(valid_indices) < 5:
            return

        # Tomar 2 puntos separados en el segmento
        i1 = valid_indices[int(len(valid_indices) * 0.25)]
        i2 = valid_indices[int(len(valid_indices) * 0.75)]

        t1, x1 = times[i1], positions[i1]
        t2, x2 = times[i2], positions[i2]

        dt = t2 - t1
        dx = x2 - x1

        if dt <= 0.1 or abs(dx) < 0.1:
            return

        # Vértices del triángulo: (t1, x1) -> (t2, x1) -> (t2, x2)
        # Cateto horizontal: dt
        ax.plot([t1, t2], [x1, x1], color="#a855f7", linestyle="--", linewidth=1.5, zorder=5)
        ax.text((t1 + t2) / 2, x1 - (abs(dx) * 0.08 if dx > 0 else -abs(dx) * 0.08),
                f"Δt = {dt:.2f} s", color="#d8b4fe", fontsize=8, fontweight="bold", ha="center")

        # Cateto vertical: dx
        ax.plot([t2, t2], [x1, x2], color="#a855f7", linestyle="--", linewidth=1.5, zorder=5)
        ax.text(t2 + (times[-1] * 0.02), (x1 + x2) / 2,
                f"Δx = {dx:+.2f} m", color="#d8b4fe", fontsize=8, fontweight="bold", va="center")

        # Hipotenusa resaltada
        ax.plot([t1, t2], [x1, x2], color="#c084fc", linewidth=2.2, zorder=5)

        # Cuadro de fórmula de la pendiente
        slope_val = dx / dt
        ax.annotate(
            f"Pendiente m = Δx / Δt\nm = {dx:+.2f} / {dt:.2f} = {slope_val:+.2f} m/s\n(Velocidad constante)",
            xy=((t1 + t2) / 2, (x1 + x2) / 2),
            xytext=((t1 + t2) / 2 - (times[-1] * 0.15), (x1 + x2) / 2 + (dx * 0.25)),
            color="#f3e8ff", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="#581c87", ec="#a855f7", lw=1.2),
            arrowprops=dict(arrowstyle="->", color="#c084fc", lw=1.2)
        )

    def _apply_axis_styling(self, ax, title: str, ylabel: str, xlabel: Optional[str]) -> None:
        """Aplica una cuadrícula de alta resolución con subdivisiones mayores y menores."""
        ax.set_facecolor(Theme.BG_CANVAS)
        ax.set_title(title, color=Theme.TEXT_LIGHT, fontsize=10, fontweight="bold", pad=8)
        ax.set_ylabel(ylabel, color=Theme.TEXT_LIGHT, fontsize=9, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, color=Theme.TEXT_LIGHT, fontsize=9, fontweight="bold")

        ax.tick_params(colors=Theme.TEXT_MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(Theme.TRACK_BORDER)
            spine.set_linewidth(1.2)

        # Cuadrícula mayor principal
        ax.grid(True, which="major", linestyle="-", alpha=0.30, color="#94a3b8")

        # Cuadrícula fina menor si está activada
        if self.show_minor_grid_var.get():
            ax.minorticks_on()
            ax.grid(True, which="minor", linestyle=":", alpha=0.15, color="#64748b")
        else:
            ax.minorticks_off()

    def _find_pause_intervals(self, times: np.ndarray, statuses: List[str]) -> List[Tuple[float, float, float]]:
        """Identifica los rangos [t_inicio, t_fin] de cada pausa registrada."""
        intervals = []
        in_pause = False
        t_start = 0.0

        for t, st in zip(times, statuses):
            if st == "PAUSADO" and not in_pause:
                in_pause = True
                t_start = t
            elif st == "EN MOVIMIENTO" and in_pause:
                in_pause = False
                intervals.append((t_start, t, t - t_start))

        if in_pause and len(times) > 0:
            intervals.append((t_start, times[-1], times[-1] - t_start))

        return intervals

    def _on_mouse_move(self, event) -> None:
        """Manejador interactivo de coordenadas al deslizar el puntero sobre los ejes."""
        if not event.inaxes or not self.samples:
            return

        t_cursor = event.xdata
        if t_cursor is None or t_cursor < 0:
            return

        use_total = (self.time_mode_var.get() == "total")
        times = [s.t_total if use_total else s.t_eff for s in self.samples]

        # Encontrar la muestra más próxima a t_cursor
        diffs = [abs(t - t_cursor) for t in times]
        closest_idx = int(np.argmin(diffs))
        s_match = self.samples[closest_idx]

        # Actualizar banner de telemetría de alta resolución
        status_color = "#22c55e" if s_match.status == "EN MOVIMIENTO" else "#f59e0b"
        self.lbl_cursor_status.config(
            text=(
                f"⏱ t = {t_cursor:.3f} s  |  "
                f"📍 Posición x = {s_match.position:+.3f} m  |  "
                f"⚡ Velocidad v = {s_match.velocity:+.3f} m/s  |  "
                f"🏃 Rapidez = {s_match.speed:.3f} m/s  |  "
                f"Δx = {s_match.displacement:+.3f} m  |  "
                f"Estado: {s_match.status}"
            ),
            fg=status_color
        )

        # Dibujar líneas de mira telescópica (crosshair)
        if self.show_crosshair_var.get() and hasattr(self, "axes_list"):
            # Limpiar líneas previas
            for l in self._crosshair_vlines:
                try:
                    l.remove()
                except Exception:
                    pass
            for l in self._crosshair_hlines:
                try:
                    l.remove()
                except Exception:
                    pass
            self._crosshair_vlines.clear()
            self._crosshair_hlines.clear()

            # Trazar línea vertical sincronizada en todos los ejes
            for ax in self.axes_list:
                vl = ax.axvline(t_cursor, color="#ec4899", linestyle="--", linewidth=0.9, alpha=0.7)
                self._crosshair_vlines.append(vl)

            # Trazar línea horizontal en el eje bajo el cursor
            hl = event.inaxes.axhline(event.ydata, color="#ec4899", linestyle="--", linewidth=0.9, alpha=0.7)
            self._crosshair_hlines.append(hl)

            self.canvas.draw_idle()

    def _export_figure_dialog(self) -> None:
        """Exporta la gráfica en formato de alta definición (PNG, PDF o SVG)."""
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar Gráfica Científica en Alta Resolución",
            defaultextension=".png",
            filetypes=[
                ("Imagen PNG de Alta Definición", "*.png"),
                ("Documento PDF Vectorial", "*.pdf"),
                ("Gráfico SVG Vectorial", "*.svg"),
                ("Todos los archivos", "*.*")
            ],
            initialfile=f"plano_mru_v{int(self.params.velocity)}_hd.png"
        )
        if filepath:
            try:
                self.fig.savefig(filepath, dpi=300, facecolor=self.fig.get_facecolor(), bbox_inches="tight")
                messagebox.showinfo("Exportación Exitosa", f"Gráfica guardada en alta resolución (300 DPI):\n{filepath}", parent=self)
            except Exception as e:
                messagebox.showerror("Error al Guardar", f"No se pudo guardar la imagen:\n{str(e)}", parent=self)
