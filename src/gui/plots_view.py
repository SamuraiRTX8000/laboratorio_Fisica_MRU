"""
Módulo de Visualización de Gráficas Científicas en Tiempo Real con Matplotlib.

Proporciona dos subgráficas sincronizadas:
    1. Posición vs. Tiempo: x(t) [m] frente a t [s].
       - Pendiente = velocidad (m = v).
       - Línea recta en MRU.
       - Tramos horizontales durante las pausas.
    2. Velocidad vs. Tiempo: v(t) [m/s] frente a t [s].
       - Línea horizontal a v = cte durante movimiento.
       - Velocidad v = 0 durante las pausas.
       - Área bajo la curva sombreada (representa el desplazamiento Delta x).
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .theme import Theme
from ..models.experiment_state import MeasurementSample


class PlotsView(tk.Frame):
    """Componente que integra las figuras científicas de Matplotlib en Tkinter."""

    def __init__(self, parent: tk.Widget, on_expand_plot: Optional[Callable[[], None]] = None, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        self.on_expand_plot = on_expand_plot

        # Selector de modo de tiempo para las gráficas
        self.time_mode_var = tk.StringVar(value="total")  # "total" o "eff"

        # Barra superior de controles de gráfica
        top_bar = tk.Frame(self, bg=Theme.BG_CARD)
        top_bar.pack(fill=tk.X, padx=8, pady=(4, 2))

        lbl_mode = tk.Label(
            top_bar,
            text="Eje temporal de gráficas:",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        lbl_mode.pack(side=tk.LEFT, padx=(0, 8))

        rb_total = tk.Radiobutton(
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
        )
        rb_total.pack(side=tk.LEFT, padx=6)

        rb_eff = tk.Radiobutton(
            top_bar,
            text="Tiempo Efectivo (MRU continuo)",
            variable=self.time_mode_var,
            value="eff",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.PRIMARY,
            command=self._on_mode_change,
            font=(Theme.FONT_FAMILY, 9)
        )
        rb_eff.pack(side=tk.LEFT, padx=6)

        if self.on_expand_plot:
            btn_expand = ttk.Button(
                top_bar,
                text="🔍 Ampliar Gráfica",
                style="Primary.TButton",
                command=self.on_expand_plot
            )
            btn_expand.pack(side=tk.RIGHT, padx=4)

        # Crear Figura Matplotlib con tema oscuro científico
        self.fig = Figure(figsize=(7.5, 4.2), dpi=100)
        self.fig.patch.set_facecolor(Theme.BG_CARD)
        self.fig.subplots_adjust(left=0.10, right=0.96, top=0.91, bottom=0.12, hspace=0.36)

        # Dos subgráficas: ax_pos (arriba), ax_vel (abajo)
        self.ax_pos = self.fig.add_subplot(2, 1, 1)
        self.ax_vel = self.fig.add_subplot(2, 1, 2, sharex=self.ax_pos)

        self._style_axis(self.ax_pos, "Posición vs. Tiempo: x(t)", "Posición x [m]")
        self._style_axis(self.ax_vel, "Velocidad vs. Tiempo: v(t)", "Velocidad v [m/s]", xlabel="Tiempo t [s]")

        # Canvas de Tkinter para Matplotlib
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.configure(bg=Theme.BG_CARD, highlightthickness=0)
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Caché de muestras
        self._cached_samples: List[MeasurementSample] = []
        self._configured_x0: float = 0.0
        self._configured_v: float = 0.0

        # Dibujar estado inicial vacío
        self.reset_plots()

    def _style_axis(self, ax, title: str, ylabel: str, xlabel: Optional[str] = None) -> None:
        """Aplica estilos de alto contraste y legibilidad científica."""
        ax.set_facecolor(Theme.BG_CANVAS)
        ax.set_title(title, color=Theme.TEXT_LIGHT, fontsize=10, fontweight="bold", pad=6)
        ax.set_ylabel(ylabel, color=Theme.TEXT_LIGHT, fontsize=9, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, color=Theme.TEXT_LIGHT, fontsize=9, fontweight="bold")

        ax.tick_params(colors=Theme.TEXT_MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(Theme.TRACK_BORDER)
            spine.set_linewidth(1.0)

        ax.grid(True, linestyle="--", alpha=0.25, color=Theme.TEXT_MUTED)

    def _on_mode_change(self) -> None:
        """Refresca las gráficas cuando el usuario alterna el modo de tiempo."""
        self.update_plots(self._cached_samples, self._configured_x0, self._configured_v, force=True)

    def reset_plots(self, x0: float = 0.0, v: float = 0.0) -> None:
        """Limpia los ejes y prepara las referencias iniciales."""
        self._cached_samples = []
        self._configured_x0 = x0
        self._configured_v = v

        self.ax_pos.cla()
        self.ax_vel.cla()

        self._style_axis(self.ax_pos, "Posición vs. Tiempo: x(t)", "Posición x [m]")
        self._style_axis(self.ax_vel, "Velocidad vs. Tiempo: v(t)", "Velocidad v [m/s]", xlabel="Tiempo t [s]")

        # Límites por defecto
        self.ax_pos.set_xlim(0, 10)
        margin = max(abs(x0) * 0.3, 10)
        self.ax_pos.set_ylim(x0 - margin, x0 + margin)

        v_margin = max(abs(v) * 0.5, 5)
        self.ax_vel.set_ylim(v - v_margin, v + v_margin)

        # Línea de referencia x0
        self.ax_pos.axhline(x0, color="#eab308", linestyle=":", linewidth=1.2, label=f"x₀ = {x0:.1f} m")
        self.ax_pos.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)

        # Línea de referencia v configurada
        self.ax_vel.axhline(v, color=Theme.PRIMARY, linestyle=":", linewidth=1.2, label=f"v_conf = {v:.1f} m/s")
        self.ax_vel.axhline(0, color=Theme.TEXT_MUTED, linestyle="-", linewidth=0.8, alpha=0.5)
        self.ax_vel.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)

        try:
            self.canvas_plot.draw()
        except Exception:
            pass

    def update_plots(
        self,
        samples: List[MeasurementSample],
        x0: float,
        v: float,
        force: bool = False
    ) -> None:
        """Actualiza las gráficas con las muestras registradas."""
        self._cached_samples = samples
        self._configured_x0 = x0
        self._configured_v = v

        if not samples:
            return

        use_total_time = (self.time_mode_var.get() == "total")

        times = [s.t_total if use_total_time else s.t_eff for s in samples]
        positions = [s.position for s in samples]
        velocities = [s.velocity for s in samples]

        max_t = max(times[-1], 2.0)

        # Limpiar y redibujar
        self.ax_pos.cla()
        self.ax_vel.cla()

        time_label = "Tiempo Total t [s]" if use_total_time else "Tiempo Efectivo t_eff [s]"
        title_pos = "Posición vs. Tiempo (Pendiente = Velocidad)"
        title_vel = "Velocidad vs. Tiempo (Área bajo la curva = Desplazamiento)"

        self._style_axis(self.ax_pos, title_pos, "Posición x [m]")
        self._style_axis(self.ax_vel, title_vel, "Velocidad v [m/s]", xlabel=time_label)

        # 1. Gráfica de Posición
        self.ax_pos.plot(times, positions, color=Theme.PRIMARY, linewidth=2.2, label="x(t) simulada")
        self.ax_pos.axhline(x0, color="#eab308", linestyle=":", linewidth=1.2, alpha=0.7, label=f"x₀ = {x0:.1f} m")

        # Punto actual
        if times:
            self.ax_pos.plot(times[-1], positions[-1], marker="o", markersize=6, color="#f43f5e")

        # 2. Gráfica de Velocidad
        self.ax_vel.plot(times, velocities, color=Theme.SUCCESS, linewidth=2.0, label="v(t) instantánea")
        self.ax_vel.axhline(0, color=Theme.TEXT_MUTED, linestyle="-", linewidth=0.8, alpha=0.5)
        self.ax_vel.axhline(v, color="#f59e0b", linestyle=":", linewidth=1.0, alpha=0.7, label=f"v_conf = {v:.1f} m/s")

        # Sombreado pedagógico del área bajo la curva (desplazamiento)
        if len(times) > 1:
            self.ax_vel.fill_between(times, velocities, 0, color=Theme.SUCCESS, alpha=0.15)

        # Ajuste dinámico de límites de ejes con márgenes confortables
        self.ax_pos.set_xlim(0, max_t * 1.05)
        self.ax_vel.set_xlim(0, max_t * 1.05)

        min_pos = min(min(positions), x0)
        max_pos = max(max(positions), x0)
        pos_span = max(max_pos - min_pos, 5.0)
        self.ax_pos.set_ylim(min_pos - (pos_span * 0.15), max_pos + (pos_span * 0.15))

        min_vel = min(min(velocities), v, 0.0)
        max_vel = max(max(velocities), v, 0.0)
        vel_span = max(max_vel - min_vel, 4.0)
        self.ax_vel.set_ylim(min_vel - (vel_span * 0.20), max_vel + (vel_span * 0.20))

        # Leyendas
        self.ax_pos.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)
        self.ax_vel.legend(loc="upper left", facecolor=Theme.BG_CARD, edgecolor=Theme.TRACK_BORDER, labelcolor=Theme.TEXT_LIGHT, fontsize=8)

        try:
            self.canvas_plot.draw()
        except Exception:
            pass
