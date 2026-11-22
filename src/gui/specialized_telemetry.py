"""
Módulos de Paneles de Telemetría Especializados para MRUA y Caída Libre.
"""

import tkinter as tk
from typing import Dict, Optional
from .theme import Theme
from .telemetry_panel import MetricCard
from ..models.experiment_state import ExperimentStatus
from ..models.physics import PhysicalState


class MRUATelemetryPanel(tk.Frame):
    """Panel de telemetría digital de alta resolución para MRUA con tarjeta de aceleración."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, padx=10, pady=8, **kwargs)

        # Encabezado con título y Badge de Estado
        header = tk.Frame(self, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            header,
            text="TELEMETRÍA MRUA EN TIEMPO REAL",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(side=tk.LEFT)

        self.lbl_motion_indicator = tk.Label(
            header,
            text="ESTADO: EN ESPERA",
            bg=Theme.BG_CARD,
            fg="#f59e0b",
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        self.lbl_motion_indicator.pack(side=tk.LEFT, padx=20)

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

        # Cuadrícula de tarjetas métricas (2 filas x 5 columnas)
        grid_frame = tk.Frame(self, bg=Theme.BG_CARD)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for col in range(5):
            grid_frame.columnconfigure(col, weight=1, uniform="mrua_metric_col")

        # Fila 1: Tiempos, Posición, Origen y Aceleración
        self.card_t_eff = MetricCard(grid_frame, "Tiempo Efectivo", "s", symbol="t_eff", accent_color=Theme.PRIMARY)
        self.card_t_eff.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")

        self.card_t_total = MetricCard(grid_frame, "Tiempo Total", "s", symbol="t_total", accent_color=Theme.ACCENT)
        self.card_t_total.grid(row=0, column=1, padx=3, pady=3, sticky="nsew")

        self.card_pos = MetricCard(grid_frame, "Posición Actual", "m", symbol="x(t)", accent_color=Theme.PRIMARY)
        self.card_pos.grid(row=0, column=2, padx=3, pady=3, sticky="nsew")

        self.card_x0 = MetricCard(grid_frame, "Posición Inicial", "m", symbol="x₀", accent_color="#eab308")
        self.card_x0.grid(row=0, column=3, padx=3, pady=3, sticky="nsew")

        self.card_acc = MetricCard(grid_frame, "Aceleración", "m/s²", symbol="a", accent_color="#f59e0b")
        self.card_acc.grid(row=0, column=4, padx=3, pady=3, sticky="nsew")

        # Fila 2: Desplazamiento, Distancia, Velocidad Vectorial, Rapidez y Dinámica
        self.card_disp = MetricCard(grid_frame, "Desplazamiento", "m", symbol="Δx", accent_color=Theme.DISPLACEMENT_BAR)
        self.card_disp.grid(row=1, column=0, padx=3, pady=3, sticky="nsew")

        self.card_dist = MetricCard(grid_frame, "Distancia Recorrida", "m", symbol="d", accent_color=Theme.SUCCESS)
        self.card_dist.grid(row=1, column=1, padx=3, pady=3, sticky="nsew")

        self.card_vel = MetricCard(grid_frame, "Velocidad Instantánea", "m/s", symbol="v(t)", accent_color=Theme.VECTOR_ARROW)
        self.card_vel.grid(row=1, column=2, padx=3, pady=3, sticky="nsew")

        self.card_spd = MetricCard(grid_frame, "Rapidez Instantánea", "m/s", symbol="|v|", accent_color=Theme.SUCCESS)
        self.card_spd.grid(row=1, column=3, padx=3, pady=3, sticky="nsew")

        self.card_v_avg = MetricCard(grid_frame, "Velocidad Media", "m/s", symbol="v_med", accent_color="#38bdf8")
        self.card_v_avg.grid(row=1, column=4, padx=3, pady=3, sticky="nsew")

    def update_telemetry(
        self,
        state: PhysicalState,
        t_eff: float,
        t_total: float,
        x0: float,
        v0: float,
        acceleration: float,
        status: ExperimentStatus
    ) -> None:
        self.card_t_eff.set_value(f"{t_eff:.3f}")
        self.card_t_total.set_value(f"{t_total:.3f}")
        self.card_pos.set_value(f"{state.position:+.3f}")
        self.card_x0.set_value(f"{x0:+.3f}")
        self.card_acc.set_value(f"{acceleration:+.3f}")

        self.card_disp.set_value(f"{state.displacement:+.3f}")
        self.card_dist.set_value(f"{state.distance:.3f}")
        self.card_vel.set_value(f"{state.velocity:+.3f}")
        self.card_spd.set_value(f"{state.speed:.3f}")

        v_avg = (state.displacement / t_eff) if t_eff > 1e-4 else v0
        self.card_v_avg.set_value(f"{v_avg:+.3f}")

        # Indicador de estado dinámico
        if status == ExperimentStatus.RUNNING:
            v = state.velocity
            a = acceleration
            if abs(v) < 0.05:
                self.lbl_motion_indicator.config(text="ESTADO: EN DETENCIÓN MOMENTÁNEA (v ≈ 0)", fg="#facc15")
            elif (v * a) > 0.05:
                self.lbl_motion_indicator.config(text="ESTADO: ACELERANDO (RAPIDEZ EN AUMENTO)", fg="#22c55e")
            elif (v * a) < -0.05:
                self.lbl_motion_indicator.config(text="ESTADO: FRENANDO / DESACELERANDO (HACIA v = 0)", fg="#f97316")
            else:
                self.lbl_motion_indicator.config(text="ESTADO: VELOCIDAD CONSTANTE (a = 0)", fg="#38bdf8")
        elif status == ExperimentStatus.PAUSED:
            self.lbl_motion_indicator.config(text="ESTADO: PAUSADO TEMPORALMENTE", fg="#d97706")
        elif status == ExperimentStatus.FINISHED:
            self.lbl_motion_indicator.config(text="ESTADO: SIMULACIÓN FINALIZADA", fg="#dc2626")
        else:
            self.lbl_motion_indicator.config(text="ESTADO: PREPARADO PARA INICIAR", fg="#0284c7")

        self.set_status(status)

    def set_status(self, status: ExperimentStatus) -> None:
        badge_config = {
            ExperimentStatus.READY: ("PREPARADO", "#0284c7"),
            ExperimentStatus.RUNNING: ("EN MOVIMIENTO", "#16a34a"),
            ExperimentStatus.PAUSED: ("PAUSADO", "#d97706"),
            ExperimentStatus.FINISHED: ("FINALIZADO", "#dc2626"),
        }
        text, bg_color = badge_config.get(status, ("DESCONOCIDO", Theme.BG_CARD_LIGHT))
        self.badge_status.config(text=text, bg=bg_color)


class VerticalTelemetryPanel(tk.Frame):
    """Panel de telemetría digital para Caída Libre y Tiro Vertical."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, padx=10, pady=8, **kwargs)

        header = tk.Frame(self, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            header,
            text="TELEMETRÍA VERTICAL EN TIEMPO REAL (CAÍDA LIBRE)",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(side=tk.LEFT)

        self.lbl_motion_indicator = tk.Label(
            header,
            text="ESTADO: EN ESPERA",
            bg=Theme.BG_CARD,
            fg="#f59e0b",
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        self.lbl_motion_indicator.pack(side=tk.LEFT, padx=20)

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

        grid_frame = tk.Frame(self, bg=Theme.BG_CARD)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for col in range(5):
            grid_frame.columnconfigure(col, weight=1, uniform="vert_metric_col")

        # Fila 1: Tiempos, Altura Actual, Altura Inicial, Altura Máxima
        self.card_t_eff = MetricCard(grid_frame, "Tiempo Transcurrido", "s", symbol="t", accent_color=Theme.PRIMARY)
        self.card_t_eff.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")

        self.card_y = MetricCard(grid_frame, "Altura Actual", "m", symbol="y(t)", accent_color=Theme.PRIMARY)
        self.card_y.grid(row=0, column=1, padx=3, pady=3, sticky="nsew")

        self.card_y0 = MetricCard(grid_frame, "Altura Inicial", "m", symbol="y₀", accent_color="#eab308")
        self.card_y0.grid(row=0, column=2, padx=3, pady=3, sticky="nsew")

        self.card_hmax = MetricCard(grid_frame, "Altura Máxima", "m", symbol="h_máx", accent_color="#f59e0b")
        self.card_hmax.grid(row=0, column=3, padx=3, pady=3, sticky="nsew")

        self.card_g = MetricCard(grid_frame, "Aceleración Gravedad", "m/s²", symbol="g", accent_color="#f97316")
        self.card_g.grid(row=0, column=4, padx=3, pady=3, sticky="nsew")

        # Fila 2: Desplazamiento Vertical, Distancia, Velocidad Vertical, Rapidez, Impacto
        self.card_dy = MetricCard(grid_frame, "Desplazamiento Vertical", "m", symbol="Δy", accent_color=Theme.DISPLACEMENT_BAR)
        self.card_dy.grid(row=1, column=0, padx=3, pady=3, sticky="nsew")

        self.card_dist = MetricCard(grid_frame, "Distancia Recorrida", "m", symbol="d", accent_color=Theme.SUCCESS)
        self.card_dist.grid(row=1, column=1, padx=3, pady=3, sticky="nsew")

        self.card_vel = MetricCard(grid_frame, "Velocidad Vertical", "m/s", symbol="vy", accent_color=Theme.VECTOR_ARROW)
        self.card_vel.grid(row=1, column=2, padx=3, pady=3, sticky="nsew")

        self.card_spd = MetricCard(grid_frame, "Rapidez", "m/s", symbol="|vy|", accent_color=Theme.SUCCESS)
        self.card_spd.grid(row=1, column=3, padx=3, pady=3, sticky="nsew")

        self.card_impact = MetricCard(grid_frame, "Tiempo hasta Impacto", "s", symbol="t_imp", accent_color="#ef4444")
        self.card_impact.grid(row=1, column=4, padx=3, pady=3, sticky="nsew")

    def update_telemetry(
        self,
        state: PhysicalState,
        t_eff: float,
        t_total: float,
        y0: float,
        v0: float,
        g: float,
        h_max: float,
        t_impact: float,
        status: ExperimentStatus
    ) -> None:
        self.card_t_eff.set_value(f"{t_eff:.3f}")
        self.card_y.set_value(f"{state.position:+.3f}")
        self.card_y0.set_value(f"{y0:.3f}")
        self.card_hmax.set_value(f"{h_max:.3f}")
        self.card_g.set_value(f"{g:.2f}")

        self.card_dy.set_value(f"{state.displacement:+.3f}")
        self.card_dist.set_value(f"{state.distance:.3f}")
        self.card_vel.set_value(f"{state.velocity:+.3f}")
        self.card_spd.set_value(f"{state.speed:.3f}")

        remaining_time = max(0.0, t_impact - t_eff)
        self.card_impact.set_value(f"{remaining_time:.2f}")

        # Indicador de estado dinámico
        if status == ExperimentStatus.RUNNING:
            vy = state.velocity
            if abs(vy) < 0.1:
                self.lbl_motion_indicator.config(text="ESTADO: EN CÚSPIDE (vy = 0 m/s)", fg="#facc15")
            elif vy > 0.1:
                self.lbl_motion_indicator.config(text="ESTADO: ASCENDIENDO (SUBIDA)", fg="#22c55e")
            else:
                self.lbl_motion_indicator.config(text="ESTADO: DESCENDIENDO (CAÍDA ACELERADA)", fg="#ef4444")
        elif status == ExperimentStatus.PAUSED:
            self.lbl_motion_indicator.config(text="ESTADO: PAUSADO TEMPORALMENTE", fg="#d97706")
        elif status == ExperimentStatus.FINISHED:
            self.lbl_motion_indicator.config(text="ESTADO: IMPACTO EN EL SUELO (y = 0)", fg="#dc2626")
        else:
            self.lbl_motion_indicator.config(text="ESTADO: PREPARADO PARA LANZAR", fg="#0284c7")

        self.set_status(status)

    def set_status(self, status: ExperimentStatus) -> None:
        badge_config = {
            ExperimentStatus.READY: ("PREPARADO", "#0284c7"),
            ExperimentStatus.RUNNING: ("EN MOVIMIENTO", "#16a34a"),
            ExperimentStatus.PAUSED: ("PAUSADO", "#d97706"),
            ExperimentStatus.FINISHED: ("FINALIZADO", "#dc2626"),
        }
        text, bg_color = badge_config.get(status, ("DESCONOCIDO", Theme.BG_CARD_LIGHT))
        self.badge_status.config(text=text, bg=bg_color)
