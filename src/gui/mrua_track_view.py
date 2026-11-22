"""
Módulo de Visualización de la Pista Virtual para MRUA.

Renderiza en un Canvas interactivo:
- Recta numérica graduada con marcas métricas.
- Vehículo experimental móvil.
- Vector de velocidad instantánea v(t) (flecha cian).
- Vector de aceleración constante a (flecha ámbar/naranja).
- Indicador didáctico de estado: "Acelerando", "Frenando", "Inversión de Sentido".
- Marcador del punto de inversión de marcha (cuando v=0).
"""

import tkinter as tk
from typing import Optional
from .theme import Theme
from ..models.physics import TrackConfig, PhysicalState


class MRUATrackView(tk.Frame):
    """Pista horizontal interactiva para MRUA con vectores v y a simultáneos."""

    def __init__(self, parent: tk.Widget, track: TrackConfig, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        self.track = track

        self.canvas = tk.Canvas(
            self,
            bg=Theme.BG_CANVAS,
            highlightthickness=1,
            highlightbackground=Theme.BG_CARD_LIGHT,
            height=210
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.margin_x = 55
        self.current_x = 0.0
        self.initial_x = 0.0
        self.current_velocity = 0.0
        self.current_acceleration = 0.0
        self.turnaround_x: Optional[float] = None
        self.is_moving = False

        self.canvas.bind("<Configure>", self._on_resize)

    def set_track_config(self, track: TrackConfig) -> None:
        self.track = track
        self.redraw()

    def update_state(
        self,
        state: PhysicalState,
        x0: float,
        is_moving: bool,
        turnaround_x: Optional[float] = None
    ) -> None:
        self.current_x = state.position
        self.initial_x = x0
        self.current_velocity = state.velocity
        self.current_acceleration = state.acceleration
        self.turnaround_x = turnaround_x
        self.is_moving = is_moving
        self.redraw()

    def _on_resize(self, event) -> None:
        self.redraw()

    def meters_to_canvas_x(self, x_m: float) -> float:
        w = max(self.canvas.winfo_width(), 400)
        usable_w = w - (2 * self.margin_x)
        fraction = (x_m - self.track.x_min) / self.track.total_length
        return self.margin_x + (fraction * usable_w)

    def redraw(self) -> None:
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 210)

        y_track_center = h * 0.48
        track_height = 46
        y_track_top = y_track_center - (track_height / 2)
        y_track_bottom = y_track_center + (track_height / 2)
        y_ruler = y_track_bottom + 14

        x_start = self.margin_x
        x_end = w - self.margin_x

        # 1. Asfalto de la pista
        self.canvas.create_rectangle(
            x_start, y_track_top, x_end, y_track_bottom,
            fill=Theme.TRACK_SURFACE, outline=Theme.TRACK_BORDER, width=2
        )

        # Línea central punteada
        self.canvas.create_line(
            x_start, y_track_center, x_end, y_track_center,
            fill="#334155", dash=(8, 6), width=1
        )

        # 2. Barreras en los extremos
        self.canvas.create_rectangle(
            x_start - 6, y_track_top - 8, x_start, y_track_bottom + 8,
            fill="#ef4444", outline="#b91c1c", width=1
        )
        self.canvas.create_rectangle(
            x_end, y_track_top - 8, x_end + 6, y_track_bottom + 8,
            fill="#ef4444", outline="#b91c1c", width=1
        )

        # 3. Graduación de la recta numérica
        self._draw_ruler(w, y_ruler)

        # 4. Marcador de Posición Inicial x0
        x0_px = self.meters_to_canvas_x(self.initial_x)
        self.canvas.create_line(
            x0_px, y_track_top - 12, x0_px, y_track_bottom + 12,
            fill="#60a5fa", dash=(4, 3), width=2
        )
        self.canvas.create_text(
            x0_px, y_track_top - 18,
            text=f"x₀ = {self.initial_x:.1f} m",
            fill="#60a5fa", font=(Theme.FONT_FAMILY, 8, "bold")
        )

        # 5. Marcador de punto de inversión si existe dentro de pista
        if self.turnaround_x is not None and self.track.contains(self.turnaround_x):
            x_turn_px = self.meters_to_canvas_x(self.turnaround_x)
            self.canvas.create_line(
                x_turn_px, y_track_top - 6, x_turn_px, y_track_bottom + 6,
                fill="#f59e0b", dash=(3, 3), width=2
            )
            self.canvas.create_text(
                x_turn_px, y_track_top - 18,
                text=f"v=0 en {self.turnaround_x:.1f} m",
                fill="#f59e0b", font=(Theme.FONT_FAMILY, 7, "bold")
            )

        # 6. Dibujar Vehículo
        car_px = self.meters_to_canvas_x(self.current_x)
        self._draw_vehicle(car_px, y_track_center)

        # 7. Vectores de velocidad (cian) y aceleración (ámbar)
        self._draw_vectors(car_px, y_track_top, y_track_bottom)

    def _draw_ruler(self, w: float, y_ruler: float) -> None:
        """Dibuja la recta numérica métrica con ticks y etiquetas."""
        x_start = self.margin_x
        x_end = w - self.margin_x

        self.canvas.create_line(x_start, y_ruler, x_end, y_ruler, fill=Theme.TEXT_MUTED, width=2)

        # Paso de división inteligente
        length = self.track.total_length
        step = 10.0 if length <= 120 else (20.0 if length <= 250 else 50.0)

        curr = self.track.x_min
        while curr <= self.track.x_max + 1e-6:
            px = self.meters_to_canvas_x(curr)
            is_origin = abs(curr) < 1e-6

            tick_len = 12 if is_origin else 7
            tick_col = Theme.PRIMARY if is_origin else Theme.TEXT_MUTED
            tick_w = 3 if is_origin else 1

            self.canvas.create_line(px, y_ruler, px, y_ruler + tick_len, fill=tick_col, width=tick_w)

            label = f"{curr:+.0f} m" if not is_origin else "0 m"
            self.canvas.create_text(
                px, y_ruler + tick_len + 10,
                text=label,
                fill=tick_col,
                font=(Theme.FONT_FAMILY, 8, "bold" if is_origin else "normal")
            )
            curr += step

    def _draw_vehicle(self, cx: float, cy: float) -> None:
        """Dibuja el coche de laboratorio con ruedas y cabina."""
        body_w, body_h = 44, 20
        x1, y1 = cx - body_w / 2, cy - body_h / 2
        x2, y2 = cx + body_w / 2, cy + body_h / 2

        # Carrocería
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#0284c7", outline="#38bdf8", width=2)

        # Cabina
        cabin_w, cabin_h = 20, 10
        self.canvas.create_rectangle(
            cx - cabin_w / 2, y1 - cabin_h, cx + cabin_w / 2, y1,
            fill="#0369a1", outline="#38bdf8", width=1
        )

        # Ruedas
        rw = 5
        self.canvas.create_oval(x1 + 4, y2 - 3, x1 + 4 + (rw * 2), y2 + 5, fill="#0f172a", outline="#cbd5e1")
        self.canvas.create_oval(x2 - 4 - (rw * 2), y2 - 3, x2 - 4, y2 + 5, fill="#0f172a", outline="#cbd5e1")

    def _draw_vectors(self, cx: float, y_top: float, y_bottom: float) -> None:
        """Dibuja flechas vectoriales de velocidad (arriba) y aceleración (abajo)."""
        v = self.current_velocity
        a = self.current_acceleration

        # 1. Vector de velocidad (cian) arriba del móvil
        if abs(v) > 0.05:
            arrow_len = min(abs(v) * 4.0, 75.0)
            sign = 1 if v > 0 else -1
            end_x = cx + (sign * arrow_len)
            y_v = y_top - 8

            self.canvas.create_line(
                cx, y_v, end_x, y_v,
                fill="#38bdf8", width=3, arrow=tk.LAST, arrowshape=(10, 12, 4)
            )
            self.canvas.create_text(
                end_x + (sign * 14), y_v,
                text=f"v = {v:+.1f} m/s",
                fill="#38bdf8", font=(Theme.FONT_FAMILY, 8, "bold")
            )

        # 2. Vector de aceleración (ámbar) abajo de la pista
        if abs(a) > 0.05:
            arrow_len = min(abs(a) * 8.0, 75.0)
            sign = 1 if a > 0 else -1
            end_x = cx + (sign * arrow_len)
            y_a = y_bottom + 32

            self.canvas.create_line(
                cx, y_a, end_x, y_a,
                fill="#f59e0b", width=3, arrow=tk.LAST, arrowshape=(10, 12, 4)
            )
            self.canvas.create_text(
                end_x + (sign * 14), y_a,
                text=f"a = {a:+.1f} m/s²",
                fill="#f59e0b", font=(Theme.FONT_FAMILY, 8, "bold")
            )
