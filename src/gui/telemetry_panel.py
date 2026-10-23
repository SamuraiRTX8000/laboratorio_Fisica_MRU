"""
Módulo del Panel de Telemetría y Datos en Tiempo Real.

Muestra de forma destacada y permanente las variables cinemáticas del experimento:
- Tiempo efectivo de movimiento (t_eff) y tiempo total de pared (t_total)
- Posición actual x(t) y posición inicial x0
- Desplazamiento vectorial (Delta x) y distancia escalar recorrida (d)
- Velocidad vectorial instantánea y rapidez escalar
- Estado actual de la máquina de simulación
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict
from .theme import Theme
from ..models.experiment_state import ExperimentStatus
from ..models.physics import PhysicalState


class MetricCard(tk.Frame):
    """Tarjeta visual para una magnitud física con unidad y valor destacado."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        unit: str,
        symbol: str = "",
        accent_color: str = Theme.PRIMARY,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD_LIGHT, padx=8, pady=6, **kwargs)
        self.unit = unit
        self.accent_color = accent_color

        # Borde sutil superior simulado o encabezado
        header_frame = tk.Frame(self, bg=Theme.BG_CARD_LIGHT)
        header_frame.pack(fill=tk.X)

        lbl_title = tk.Label(
            header_frame,
            text=title,
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "bold")
        )
        lbl_title.pack(side=tk.LEFT)

        if symbol:
            lbl_sym = tk.Label(
                header_frame,
                text=symbol,
                bg=Theme.BG_CARD_LIGHT,
                fg=accent_color,
                font=(Theme.FONT_FAMILY, 8, "bold")
            )
            lbl_sym.pack(side=tk.RIGHT)

        # Valor numérico principal grande
        self.lbl_value = tk.Label(
            self,
            text=f"0.00 {unit}",
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.TEXT_LIGHT,
            font=Theme.FONT_MONO
        )
        self.lbl_value.pack(anchor="w", pady=(2, 0))

    def set_value(self, value_str: str) -> None:
        """Actualiza el texto del valor con su unidad."""
        self.lbl_value.config(text=f"{value_str} {self.unit}")


class TelemetryPanel(tk.Frame):
    """Panel que organiza todas las tarjetas de métricas físicas y estado."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, padx=10, pady=8, **kwargs)

        # Encabezado con título y Badge de Estado
        header = tk.Frame(self, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, pady=(0, 8))

        lbl_header = tk.Label(
            header,
            text="TELEMETRÍA EN TIEMPO REAL",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold")
        )
        lbl_header.pack(side=tk.LEFT)

        # Badge de Estado de Simulación
        self.badge_status = tk.Label(
            header,
            text="PREPARADO",
            bg="#0284c7",
            fg=Theme.TEXT_LIGHT,
            font=Theme.FONT_BADGE,
            padx=8,
            pady=2
        )
        self.badge_status.pack(side=tk.RIGHT)

        # Contenedor Grid para las tarjetas de métricas
        grid_frame = tk.Frame(self, bg=Theme.BG_CARD)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for col in range(4):
            grid_frame.columnconfigure(col, weight=1, uniform="metric_col")

        # Fila 1: Tiempos y Posiciones
        self.card_t_eff = MetricCard(grid_frame, "Tiempo Efectivo", "s", symbol="t_eff", accent_color=Theme.PRIMARY)
        self.card_t_eff.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        self.card_t_total = MetricCard(grid_frame, "Tiempo Total", "s", symbol="t_total", accent_color=Theme.ACCENT)
        self.card_t_total.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        self.card_pos = MetricCard(grid_frame, "Posición Actual", "m", symbol="x(t)", accent_color=Theme.PRIMARY)
        self.card_pos.grid(row=0, column=2, padx=4, pady=4, sticky="nsew")

        self.card_x0 = MetricCard(grid_frame, "Posición Inicial", "m", symbol="x₀", accent_color="#eab308")
        self.card_x0.grid(row=0, column=3, padx=4, pady=4, sticky="nsew")

        # Fila 2: Desplazamiento, Distancia, Velocidad, Rapidez
        self.card_disp = MetricCard(grid_frame, "Desplazamiento", "m", symbol="Δx", accent_color=Theme.DISPLACEMENT_BAR)
        self.card_disp.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")

        self.card_dist = MetricCard(grid_frame, "Distancia Recorrida", "m", symbol="d", accent_color=Theme.SUCCESS)
        self.card_dist.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")

        self.card_vel = MetricCard(grid_frame, "Velocidad (Vector)", "m/s", symbol="v⃗", accent_color=Theme.VECTOR_ARROW)
        self.card_vel.grid(row=1, column=2, padx=4, pady=4, sticky="nsew")

        self.card_spd = MetricCard(grid_frame, "Rapidez (Escalar)", "m/s", symbol="|v|", accent_color=Theme.SUCCESS)
        self.card_spd.grid(row=1, column=3, padx=4, pady=4, sticky="nsew")

    def update_telemetry(
        self,
        state: PhysicalState,
        t_eff: float,
        t_total: float,
        x0: float,
        configured_v: float,
        status: ExperimentStatus
    ) -> None:
        """Actualiza todas las métricas en pantalla."""
        # Tiempos
        self.card_t_eff.set_value(f"{t_eff:.3f}")
        self.card_t_total.set_value(f"{t_total:.3f}")

        # Posiciones
        self.card_pos.set_value(f"{state.position:+.3f}")
        self.card_x0.set_value(f"{x0:+.3f}")

        # Desplazamiento y Distancia
        self.card_disp.set_value(f"{state.displacement:+.3f}")
        self.card_dist.set_value(f"{state.distance:.3f}")

        # Velocidad y Rapidez
        is_moving = (status == ExperimentStatus.RUNNING)
        curr_v = configured_v if is_moving else 0.0
        curr_s = abs(configured_v) if is_moving else 0.0

        self.card_vel.set_value(f"{curr_v:+.3f}")
        self.card_spd.set_value(f"{curr_s:.3f}")

        # Badge de Estado
        self.set_status(status)

    def set_status(self, status: ExperimentStatus) -> None:
        """Configura el color y texto del badge según el estado de la simulación."""
        badge_config: Dict[ExperimentStatus, tuple] = {
            ExperimentStatus.READY: ("PREPARADO", "#0284c7"),
            ExperimentStatus.RUNNING: ("EN MOVIMIENTO", "#16a34a"),
            ExperimentStatus.PAUSED: ("PAUSADO", "#d97706"),
            ExperimentStatus.FINISHED: ("FINALIZADO", "#dc2626"),
        }
        text, bg_color = badge_config.get(status, ("DESCONOCIDO", Theme.BG_CARD_LIGHT))
        self.badge_status.config(text=text, bg=bg_color)
