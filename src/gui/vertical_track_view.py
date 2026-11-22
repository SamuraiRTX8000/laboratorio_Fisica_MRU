"""
Módulo de Visualización de Caída Libre y Lanzamiento Vertical.

Renderiza en un Canvas vertical:
- Superficie del suelo (y = 0 m).
- Torre o plataforma de lanzamiento.
- Regla vertical graduada en metros.
- Proyectil (esfera de laboratorio).
- Vector de velocidad vertical vy (flecha cian).
- Vector gravitatorio g hacia abajo (flecha naranja).
- Línea indicadora de altura máxima alcanzada (h_máx).
- Efecto visual de impacto en el suelo.
"""

import tkinter as tk
from typing import Optional
from .theme import Theme
from ..models.physics import PhysicalState


class VerticalTrackView(tk.Frame):
    """Pista vertical para experimentos de Caída Libre y Tiro Vertical."""

    def __init__(self, parent: tk.Widget, max_height: float = 60.0, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        self.max_height = max_height

        self.canvas = tk.Canvas(
            self,
            bg=Theme.BG_CANVAS,
            highlightthickness=1,
            highlightbackground=Theme.BG_CARD_LIGHT,
            height=260
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.margin_y_bottom = 40
        self.margin_y_top = 25
        self.margin_x = 70

        self.current_y = 0.0
        self.initial_y = 0.0
        self.current_velocity = 0.0
        self.gravity = 9.81
        self.h_max: Optional[float] = None
        self.is_moving = False

        self.canvas.bind("<Configure>", self._on_resize)

    def set_environment(self, max_height: float, initial_y: float, gravity: float) -> None:
        self.max_height = max(max_height, initial_y * 1.25, 20.0)
        self.initial_y = initial_y
        self.gravity = gravity
        self.redraw()

    def update_state(
        self,
        state: PhysicalState,
        initial_y: float,
        is_moving: bool,
        h_max: Optional[float] = None
    ) -> None:
        self.current_y = state.position
        self.initial_y = initial_y
        self.current_velocity = state.velocity
        self.h_max = h_max
        self.is_moving = is_moving

        # Autoescalar el eje vertical si h_max supera el rango visible
        if h_max and h_max > self.max_height:
            self.max_height = h_max * 1.15

        self.redraw()

    def _on_resize(self, event) -> None:
        self.redraw()

    def meters_to_canvas_y(self, y_m: float) -> float:
        h = max(self.canvas.winfo_height(), 200)
        usable_h = h - self.margin_y_bottom - self.margin_y_top
        fraction = max(0.0, min(1.0, y_m / self.max_height))
        return (h - self.margin_y_bottom) - (fraction * usable_h)

    def redraw(self) -> None:
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 200)

        y_ground = h - self.margin_y_bottom
        x_ruler = 70
        x_tower = 140
        x_ball = 240

        # 1. Suelo (y = 0)
        self.canvas.create_rectangle(
            0, y_ground, w, h,
            fill="#1e293b", outline="#334155", width=2
        )
        self.canvas.create_line(0, y_ground, w, y_ground, fill="#10b981", width=3)
        self.canvas.create_text(
            35, y_ground + 15,
            text="Suelo (y = 0 m)",
            fill="#10b981", font=(Theme.FONT_FAMILY, 8, "bold")
        )

        # 2. Regla vertical graduada
        self._draw_vertical_ruler(x_ruler, y_ground, h)

        # 3. Torre / Edificio de lanzamiento
        if self.initial_y > 0.5:
            y_platform = self.meters_to_canvas_y(self.initial_y)
            tower_w = 40
            self.canvas.create_rectangle(
                x_ball - 50 - tower_w, y_platform, x_ball - 30, y_ground,
                fill="#334155", outline="#475569", width=2
            )
            # Ventanillas de la torre
            curr_y_win = y_platform + 12
            while curr_y_win < y_ground - 10:
                self.canvas.create_rectangle(
                    x_ball - 45 - tower_w, curr_y_win, x_ball - 35, curr_y_win + 8,
                    fill="#1e293b", outline="#0284c7"
                )
                curr_y_win += 18

            # Plataforma horizontal
            self.canvas.create_line(
                x_ball - 60 - tower_w, y_platform, x_ball - 10, y_platform,
                fill="#38bdf8", width=3
            )
            self.canvas.create_text(
                x_ball - 35 - tower_w, y_platform - 10,
                text=f"y₀ = {self.initial_y:.1f} m",
                fill="#38bdf8", font=(Theme.FONT_FAMILY, 8, "bold")
            )

        # 4. Línea de Altura Máxima (h_max)
        if self.h_max is not None and self.h_max > self.initial_y + 0.1:
            y_hmax = self.meters_to_canvas_y(self.h_max)
            self.canvas.create_line(
                x_ball - 50, y_hmax, x_ball + 120, y_hmax,
                fill="#f59e0b", dash=(4, 3), width=2
            )
            self.canvas.create_text(
                x_ball + 65, y_hmax - 10,
                text=f"h_máx = {self.h_max:.2f} m (v=0)",
                fill="#f59e0b", font=(Theme.FONT_FAMILY, 8, "bold")
            )

        # 5. Proyectil (Esfera)
        ball_py = self.meters_to_canvas_y(self.current_y)
        radius = 11
        self.canvas.create_oval(
            x_ball - radius, ball_py - radius, x_ball + radius, ball_py + radius,
            fill="#ef4444", outline="#fca5a5", width=2
        )

        # 6. Vector de velocidad vertical vy
        v = self.current_velocity
        if abs(v) > 0.05:
            arrow_len = min(abs(v) * 2.8, 65.0)
            sign = -1 if v > 0 else 1  # -1 en canvas Y es hacia arriba!
            y_end = ball_py + (sign * arrow_len)

            self.canvas.create_line(
                x_ball, ball_py, x_ball, y_end,
                fill="#38bdf8", width=3, arrow=tk.LAST, arrowshape=(10, 12, 4)
            )
            self.canvas.create_text(
                x_ball + 45, (ball_py + y_end) / 2,
                text=f"v = {v:+.1f} m/s",
                fill="#38bdf8", font=(Theme.FONT_FAMILY, 8, "bold")
            )

        # 7. Vector de gravedad constante g hacia abajo
        x_g = x_ball + 120
        y_g_start = h * 0.35
        y_g_end = y_g_start + 45
        self.canvas.create_line(
            x_g, y_g_start, x_g, y_g_end,
            fill="#f97316", width=2, arrow=tk.LAST, arrowshape=(8, 10, 3)
        )
        self.canvas.create_text(
            x_g, y_g_end + 12,
            text=f"g = {self.gravity:.2f} m/s²",
            fill="#f97316", font=(Theme.FONT_FAMILY, 8, "bold")
        )

    def _draw_vertical_ruler(self, x_ruler: float, y_ground: float, h: float) -> None:
        y_top = self.margin_y_top
        self.canvas.create_line(x_ruler, y_ground, x_ruler, y_top, fill=Theme.TEXT_MUTED, width=2)

        step = 10.0 if self.max_height <= 100 else 20.0
        curr_y = 0.0
        while curr_y <= self.max_height:
            py = self.meters_to_canvas_y(curr_y)
            is_zero = abs(curr_y) < 1e-6
            tick_len = 10 if is_zero else 6
            color = "#10b981" if is_zero else Theme.TEXT_MUTED

            self.canvas.create_line(x_ruler - tick_len, py, x_ruler, py, fill=color, width=2 if is_zero else 1)
            self.canvas.create_text(
                x_ruler - tick_len - 14, py,
                text=f"{curr_y:.0f} m",
                fill=color, font=(Theme.FONT_FAMILY, 8)
            )
            curr_y += step
