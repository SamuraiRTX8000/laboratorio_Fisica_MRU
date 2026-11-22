"""
Módulo de Visualización de Gráficas Científicas de MRUA y Caída Libre.

Proporciona tres subgráficas científicas sincronizadas en tiempo real:
    1. Posición / Altura vs. Tiempo: x(t) [m] o y(t) [m].
       - Curva parabólica característica.
       - Vértice correspondiente a la velocidad nula (h_máx o punto de inversión).
    2. Velocidad vs. Tiempo: v(t) [m/s].
       - Línea recta con pendiente m = a (o -g).
       - Cruce por el eje horizontal v = 0 en el instante de detención.
    3. Aceleración vs. Tiempo: a(t) [m/s²].
       - Línea horizontal constante a = cte (o -g = cte).
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .theme import Theme
from ..models.experiment_state import MeasurementSample


class MRUAPlotsView(tk.Frame):
    """Componente con 3 subgráficas sincronizadas (x-t, v-t, a-t) para MRUA y Caída Libre."""

    def __init__(
        self,
        parent: tk.Widget,
        is_vertical: bool = False,
        on_expand_plot: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        self.is_vertical = is_vertical
        self.on_expand_plot = on_expand_plot

        self.time_mode_var = tk.StringVar(value="total")  # "total" o "eff"

        # Barra superior de controles
        top_bar = tk.Frame(self, bg=Theme.BG_CARD)
        top_bar.pack(fill=tk.X, padx=8, pady=(4, 2))

        lbl_mode = tk.Label(
            top_bar,
            text="Eje temporal:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        lbl_mode.pack(side=tk.LEFT, padx=(0, 6))

        tk.Radiobutton(
            top_bar,
            text="Tiempo Global (con pausas)",
            variable=self.time_mode_var,
            value="total",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.PRIMARY,
            command=self._on_mode_change,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(side=tk.LEFT, padx=4)

        tk.Radiobutton(
            top_bar,
            text="Tiempo Efectivo (Continuo)",
            variable=self.time_mode_var,
            value="eff",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.PRIMARY,
            command=self._on_mode_change,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(side=tk.LEFT, padx=4)

        # Crear Figura con 3 subplots
        self.fig = Figure(figsize=(7.5, 4.8), dpi=100)
        self.fig.patch.set_facecolor(Theme.BG_CARD)
        self.fig.subplots_adjust(left=0.10, right=0.96, top=0.93, bottom=0.10, hspace=0.45)

        self.ax_pos = self.fig.add_subplot(3, 1, 1)
        self.ax_vel = self.fig.add_subplot(3, 1, 2, sharex=self.ax_pos)
        self.ax_acc = self.fig.add_subplot(3, 1, 3, sharex=self.ax_pos)

        pos_title = "Altura vs. Tiempo: y(t)" if is_vertical else "Posición vs. Tiempo: x(t) [Parábola]"
        pos_ylabel = "Altura y [m]" if is_vertical else "Posición x [m]"
        vel_ylabel = "Velocidad vy [m/s]" if is_vertical else "Velocidad v [m/s]"
        acc_ylabel = "Gravedad ay [m/s²]" if is_vertical else "Aceleración a [m/s²]"

        self._style_axis(self.ax_pos, pos_title, pos_ylabel)
        self._style_axis(self.ax_vel, "Velocidad vs. Tiempo: v(t) [Línea recta]", vel_ylabel)
        self._style_axis(self.ax_acc, "Aceleración vs. Tiempo: a(t) [Constante]", acc_ylabel, xlabel="Tiempo t [s]")

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.configure(bg=Theme.BG_CARD, highlightthickness=0)
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._cached_samples: List[MeasurementSample] = []
        self._configured_x0: float = 0.0
        self._configured_v0: float = 0.0
        self._configured_a: float = 0.0

        self.reset_plots()

    def _style_axis(self, ax, title: str, ylabel: str, xlabel: Optional[str] = None) -> None:
        ax.set_facecolor(Theme.BG_CANVAS)
        ax.set_title(title, color=Theme.TEXT_LIGHT, fontsize=9, fontweight="bold", pad=4)
        ax.set_ylabel(ylabel, color=Theme.TEXT_LIGHT, fontsize=8, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, color=Theme.TEXT_LIGHT, fontsize=8, fontweight="bold")

        ax.tick_params(colors=Theme.TEXT_MUTED, labelsize=8)
        ax.grid(True, color="#334155", linestyle="--", linewidth=0.5, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color("#475569")

    def _on_mode_change(self) -> None:
        if self._cached_samples:
            self.update_plots(self._cached_samples, self._configured_x0, self._configured_v0, self._configured_a, force=True)

    def reset_plots(self, x0: float = 0.0, v0: float = 0.0, a: float = 0.0) -> None:
        """Limpia las curvas y prepara los ejes."""
        self._cached_samples.clear()
        self._configured_x0 = x0
        self._configured_v0 = v0
        self._configured_a = a

        for ax in (self.ax_pos, self.ax_vel, self.ax_acc):
            ax.cla()

        pos_title = "Altura vs. Tiempo: y(t)" if self.is_vertical else "Posición vs. Tiempo: x(t) [Parábola]"
        pos_ylabel = "Altura y [m]" if self.is_vertical else "Posición x [m]"
        vel_ylabel = "Velocidad vy [m/s]" if self.is_vertical else "Velocidad v [m/s]"
        acc_ylabel = "Gravedad ay [m/s²]" if self.is_vertical else "Aceleración a [m/s²]"

        self._style_axis(self.ax_pos, pos_title, pos_ylabel)
        self._style_axis(self.ax_vel, "Velocidad vs. Tiempo: v(t) [Línea recta]", vel_ylabel)
        self._style_axis(self.ax_acc, "Aceleración vs. Tiempo: a(t) [Constante]", acc_ylabel, xlabel="Tiempo t [s]")

        self.ax_pos.set_xlim(0, 5)
        self.ax_vel.set_xlim(0, 5)
        self.ax_acc.set_xlim(0, 5)

        self.canvas_plot.draw_idle()

    def update_plots(
        self,
        samples: List[MeasurementSample],
        x0: float,
        v0: float,
        a: float,
        force: bool = False
    ) -> None:
        """Actualiza las 3 subgráficas con las muestras telemétricas."""
        self._cached_samples = list(samples)
        self._configured_x0 = x0
        self._configured_v0 = v0
        self._configured_a = a

        if not samples:
            self.reset_plots(x0, v0, a)
            return

        use_eff = (self.time_mode_var.get() == "eff")
        t_data = [s.t_eff if use_eff else s.t_total for s in samples]
        x_data = [s.position for s in samples]
        v_data = [s.velocity for s in samples]
        a_data = [getattr(s, "acceleration", a) for s in samples]

        max_t = max(t_data) if t_data else 1.0
        x_limit = max(5.0, max_t * 1.05)

        # 1. Gráfica de Posición (Parábola)
        self.ax_pos.cla()
        pos_title = "Altura vs. Tiempo: y(t)" if self.is_vertical else "Posición vs. Tiempo: x(t) [Parábola]"
        pos_ylabel = "Altura y [m]" if self.is_vertical else "Posición x [m]"
        self._style_axis(self.ax_pos, pos_title, pos_ylabel)

        self.ax_pos.plot(t_data, x_data, color="#38bdf8", linewidth=2.0, label="Trayectoria x(t)")
        if x_data:
            self.ax_pos.plot(t_data[-1], x_data[-1], marker="o", color="#0284c7", markersize=6)
        self.ax_pos.set_xlim(0, x_limit)

        # 2. Gráfica de Velocidad (Línea con pendiente)
        self.ax_vel.cla()
        vel_ylabel = "Velocidad vy [m/s]" if self.is_vertical else "Velocidad v [m/s]"
        self._style_axis(self.ax_vel, "Velocidad vs. Tiempo: v(t)", vel_ylabel)

        # Línea de referencia v = 0
        self.ax_vel.axhline(0, color="#64748b", linestyle=":", linewidth=1)

        self.ax_vel.plot(t_data, v_data, color="#4ade80", linewidth=2.0, label="v(t)")
        if v_data:
            self.ax_vel.plot(t_data[-1], v_data[-1], marker="o", color="#16a34a", markersize=6)
        self.ax_vel.set_xlim(0, x_limit)

        # 3. Gráfica de Aceleración (Línea constante)
        self.ax_acc.cla()
        acc_ylabel = "Gravedad ay [m/s²]" if self.is_vertical else "Aceleración a [m/s²]"
        self._style_axis(self.ax_acc, "Aceleración vs. Tiempo: a(t)", acc_ylabel, xlabel="Tiempo t [s]")

        self.ax_acc.plot(t_data, a_data, color="#f59e0b", linewidth=2.0, label="a = cte")
        if a_data:
            self.ax_acc.plot(t_data[-1], a_data[-1], marker="o", color="#d97706", markersize=6)
        self.ax_acc.set_xlim(0, x_limit)

        # Márgenes en eje Y de aceleración para legibilidad
        min_a = min(a_data) if a_data else a
        max_a = max(a_data) if a_data else a
        if abs(max_a - min_a) < 1e-4:
            span = max(abs(max_a) * 0.5, 2.0)
            self.ax_acc.set_ylim(min_a - span, max_a + span)

        self.canvas_plot.draw_idle()
