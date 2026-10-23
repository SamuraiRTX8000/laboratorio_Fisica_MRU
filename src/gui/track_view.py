"""
Módulo de Visualización de la Pista Virtual y Recta Numérica.

Implementa un Canvas interactivo con renderizado vectorial de:
- Recta numérica graduada con origen (x=0) claramente destacado.
- Límites físicos de la pista (barreras).
- Marcador de posición inicial (x0).
- Vector de desplazamiento (Delta x) entre x0 y x(t).
- Vehículo de laboratorio móvil con ruedas, cabina y detalles.
- Vector de velocidad (flecha con magnitud y sentido).
- Lecturas flotantes de telemetría sobre la pista.
"""

import tkinter as tk
from typing import Optional
from .theme import Theme
from ..models.physics import TrackConfig, PhysicalState


class TrackView(tk.Frame):
    """Componente de visualización de la pista de movimiento rectilíneo."""

    def __init__(self, parent: tk.Widget, track: TrackConfig, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        self.track = track

        # Configuración del Canvas
        self.canvas = tk.Canvas(
            self,
            bg=Theme.BG_CANVAS,
            highlightthickness=1,
            highlightbackground=Theme.BG_CARD_LIGHT,
            height=200
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Márgenes para la pista
        self.margin_x = 55
        self.margin_y_top = 35
        self.margin_y_bottom = 35

        # Estado visual actual
        self.current_x = 0.0
        self.initial_x = 0.0
        self.current_velocity = 0.0
        self.is_moving = False

        # Enlace a evento de redimensionamiento
        self.canvas.bind("<Configure>", self._on_resize)

    def set_track_config(self, track: TrackConfig) -> None:
        """Actualiza la configuración geométrica de la pista y redibuja."""
        self.track = track
        self.redraw()

    def update_state(self, state: PhysicalState, x0: float, is_moving: bool) -> None:
        """Actualiza la posición del móvil, vectores y estado dinámico."""
        self.current_x = state.position
        self.initial_x = x0
        self.current_velocity = state.velocity
        self.is_moving = is_moving
        self.redraw()

    def _on_resize(self, event) -> None:
        """Manejador para cuando el usuario cambia el tamaño de la ventana."""
        self.redraw()

    def meters_to_canvas_x(self, x_m: float) -> float:
        """Convierte una coordenada en metros a píxeles en el canvas."""
        w = max(self.canvas.winfo_width(), 400)
        usable_w = w - (2 * self.margin_x)
        fraction = (x_m - self.track.x_min) / self.track.total_length
        return self.margin_x + (fraction * usable_w)

    def redraw(self) -> None:
        """Redibuja completamente la pista, regla, origen, marcas y vehículo."""
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 200)

        # Posiciones Y clave
        y_track_center = h * 0.50
        track_height = 46
        y_track_top = y_track_center - (track_height / 2)
        y_track_bottom = y_track_center + (track_height / 2)
        y_ruler = y_track_bottom + 14

        x_start = self.margin_x
        x_end = w - self.margin_x

        # 1. Dibujar asfalto de la pista
        self.canvas.create_rectangle(
            x_start, y_track_top, x_end, y_track_bottom,
            fill=Theme.TRACK_SURFACE, outline=Theme.TRACK_BORDER, width=2
        )

        # Línea central punteada en la pista
        self.canvas.create_line(
            x_start, y_track_center, x_end, y_track_center,
            fill="#334155", dash=(8, 6), width=1
        )

        # 2. Barreras límite de la pista (x_min y x_max)
        self._draw_boundary_barrier(x_start, y_track_top, y_track_bottom, f"Límite {self.track.x_min:.0f} m", is_left=True)
        self._draw_boundary_barrier(x_end, y_track_top, y_track_bottom, f"Límite {self.track.x_max:.0f} m", is_left=False)

        # 3. Dibujar la recta numérica graduada
        self._draw_number_line(x_start, x_end, y_ruler, y_track_top, y_track_bottom)

        # 4. Dibujar vector desplazamiento (Delta x) si hay diferencia respecto a x0
        self._draw_displacement_vector(y_track_top - 12)

        # 5. Dibujar marcador de posición inicial x0
        self._draw_initial_position_marker(y_track_top, y_track_bottom)

        # 6. Dibujar vehículo en current_x
        self._draw_vehicle(y_track_center)

    def _draw_boundary_barrier(self, x: float, y_top: float, y_bottom: float, label: str, is_left: bool) -> None:
        """Dibuja un poste o barrera de seguridad con franjas en los extremos de la pista."""
        width = 10
        x1 = x - width if is_left else x
        x2 = x if is_left else x + width

        # Fondo barrera
        self.canvas.create_rectangle(
            x1, y_top - 5, x2, y_bottom + 5,
            fill="#dc2626", outline="#991b1b", width=1
        )

        # Franjas blancas reflectivas
        step = 6
        for y_stripe in range(int(y_top - 5), int(y_bottom + 5), step * 2):
            self.canvas.create_rectangle(
                x1, y_stripe, x2, min(y_stripe + step, y_bottom + 5),
                fill="#ffffff", outline=""
            )

        # Etiqueta de límite
        y_text = y_top - 14
        self.canvas.create_text(
            x, y_text,
            text=label, fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8, "bold")
        )

    def _draw_number_line(self, x_start: float, x_end: float, y_ruler: float, y_track_top: float, y_track_bottom: float) -> None:
        """Dibuja la recta numérica con subdivisiones y marcas en metros."""
        # Eje principal de la recta numérica
        self.canvas.create_line(
            x_start - 10, y_ruler, x_end + 10, y_ruler,
            fill=Theme.TEXT_MUTED, width=2, arrow=tk.LAST, arrowshape=(10, 12, 4)
        )
        # Flecha en sentido negativo
        self.canvas.create_line(
            x_start + 10, y_ruler, x_start - 10, y_ruler,
            fill=Theme.TEXT_MUTED, width=2, arrow=tk.LAST, arrowshape=(10, 12, 4)
        )

        # Indicador de sentido positivo y negativo
        self.canvas.create_text(
            x_end + 25, y_ruler,
            text="(+) x", fill=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold")
        )
        self.canvas.create_text(
            x_start - 25, y_ruler,
            text="(-) x", fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9, "bold")
        )

        # Determinar intervalo de marcas según longitud de la pista
        length = self.track.total_length
        if length <= 20:
            step_major = 2.0
            step_minor = 0.5
        elif length <= 60:
            step_major = 5.0
            step_minor = 1.0
        elif length <= 120:
            step_major = 10.0
            step_minor = 2.0
        elif length <= 250:
            step_major = 20.0
            step_minor = 5.0
        else:
            step_major = 50.0
            step_minor = 10.0

        # Dibujar marcas menores
        curr_m = self.track.x_min
        while curr_m <= self.track.x_max + 1e-6:
            cx = self.meters_to_canvas_x(curr_m)
            self.canvas.create_line(
                cx, y_ruler, cx, y_ruler + 4,
                fill=Theme.TRACK_MARK_MINOR, width=1
            )
            curr_m += step_minor

        # Dibujar marcas mayores con números
        curr_m = self.track.x_min
        # Alinear curr_m al múltiplo de step_major
        first_major = (int(curr_m / step_major)) * step_major
        if first_major < curr_m:
            first_major += step_major

        val = first_major
        while val <= self.track.x_max + 1e-6:
            cx = self.meters_to_canvas_x(val)
            self.canvas.create_line(
                cx, y_ruler, cx, y_ruler + 8,
                fill=Theme.TRACK_MARK_MAJOR, width=1.5
            )
            self.canvas.create_text(
                cx, y_ruler + 16,
                text=f"{val:.0f}m", fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)
            )
            val += step_major

        # Destacar el ORIGEN (x = 0) si está dentro del rango
        if self.track.contains(0.0):
            cx0 = self.meters_to_canvas_x(0.0)

            # Línea vertical completa de referencia para x = 0
            self.canvas.create_line(
                cx0, y_track_top - 6, cx0, y_ruler + 10,
                fill=Theme.ORIGIN_MARKER, dash=(4, 3), width=2
            )

            # Punto destacado en el eje
            self.canvas.create_oval(
                cx0 - 4, y_ruler - 4, cx0 + 4, y_ruler + 4,
                fill=Theme.ORIGIN_MARKER, outline=Theme.TEXT_LIGHT, width=1.5
            )

            # Etiqueta destacada
            self.canvas.create_text(
                cx0, y_ruler + 28,
                text="x = 0 (Origen)", fill=Theme.ORIGIN_MARKER, font=(Theme.FONT_FAMILY, 9, "bold")
            )

    def _draw_initial_position_marker(self, y_top: float, y_bottom: float) -> None:
        """Dibuja un poste/banderín que marca la posición inicial x0."""
        if not self.track.contains(self.initial_x):
            return

        cx_init = self.meters_to_canvas_x(self.initial_x)

        # Mástil del banderín
        self.canvas.create_line(
            cx_init, y_top - 20, cx_init, y_bottom,
            fill="#eab308", dash=(2, 2), width=1.5
        )

        # Banderín triangular de inicio
        self.canvas.create_polygon(
            cx_init, y_top - 20,
            cx_init + 12, y_top - 15,
            cx_init, y_top - 10,
            fill="#eab308", outline="#fef08a", width=1
        )

        # Etiqueta
        self.canvas.create_text(
            cx_init, y_top - 26,
            text=f"x₀ = {self.initial_x:.1f}m",
            fill="#fde047", font=(Theme.FONT_FAMILY, 8, "bold")
        )

    def _draw_displacement_vector(self, y_pos: float) -> None:
        """Dibuja el vector de desplazamiento Delta x entre x0 y x(t)."""
        disp = self.current_x - self.initial_x
        if abs(disp) < 0.2:
            return  # Desplazamiento mínimo imperceptible

        cx_start = self.meters_to_canvas_x(self.initial_x)
        cx_curr = self.meters_to_canvas_x(self.current_x)

        arrow_dir = tk.LAST if disp > 0 else tk.FIRST

        # Flecha de desplazamiento
        self.canvas.create_line(
            cx_start, y_pos, cx_curr, y_pos,
            fill=Theme.DISPLACEMENT_BAR, width=3, arrow=arrow_dir, arrowshape=(10, 12, 4)
        )

        # Etiqueta de magnitud y signo del desplazamiento
        mid_x = (cx_start + cx_curr) / 2
        sign_str = "+" if disp > 0 else ""
        self.canvas.create_text(
            mid_x, y_pos - 9,
            text=f"Δx = {sign_str}{disp:.2f} m",
            fill=Theme.DISPLACEMENT_BAR, font=(Theme.FONT_FAMILY, 8, "bold")
        )

    def _draw_vehicle(self, y_center: float) -> None:
        """Dibuja el vehículo cinemático con vector velocidad y lectura flotante."""
        cx = self.meters_to_canvas_x(self.current_x)

        car_w = 46
        car_h = 22
        half_w = car_w / 2
        half_h = car_h / 2

        # 1. Sombra bajo el auto
        self.canvas.create_oval(
            cx - half_w - 4, y_center + half_h - 2,
            cx + half_w + 4, y_center + half_h + 6,
            fill="#090d16", outline=""
        )

        # 2. Carrocería principal (rectángulo redondeado simulado o polígono aerodinámico)
        body_points = [
            cx - half_w, y_center + half_h - 4,
            cx - half_w, y_center - 2,
            cx - half_w + 10, y_center - half_h + 2,
            cx + half_w - 12, y_center - half_h + 2,
            cx + half_w, y_center - 2,
            cx + half_w, y_center + half_h - 4,
        ]
        self.canvas.create_polygon(
            body_points,
            fill=Theme.CAR_COLOR, outline=Theme.PRIMARY, width=1.5
        )

        # 3. Parabrisas y cabina
        windshield = [
            cx - half_w + 12, y_center - 1,
            cx - half_w + 15, y_center - half_h + 4,
            cx + half_w - 16, y_center - half_h + 4,
            cx + half_w - 12, y_center - 1,
        ]
        self.canvas.create_polygon(
            windshield,
            fill="#0284c7", outline="#bae6fd", width=1
        )

        # 4. Faros (delantero y trasero)
        headlight_color = "#fef08a" if self.current_velocity >= 0 else "#ef4444"
        taillight_color = "#ef4444" if self.current_velocity >= 0 else "#fef08a"

        # Faro derecho
        self.canvas.create_rectangle(
            cx + half_w - 3, y_center + 1, cx + half_w, y_center + 5,
            fill=headlight_color, outline=""
        )
        # Faro izquierdo
        self.canvas.create_rectangle(
            cx - half_w, y_center + 1, cx - half_w + 3, y_center + 5,
            fill=taillight_color, outline=""
        )

        # 5. Ruedas (izquierda y derecha)
        wheel_r = 7
        y_wheel = y_center + half_h - 2

        # Rueda trasera/izquierda
        self.canvas.create_oval(
            cx - half_w + 6 - wheel_r, y_wheel - wheel_r,
            cx - half_w + 6 + wheel_r, y_wheel + wheel_r,
            fill=Theme.CAR_WHEEL, outline=Theme.CAR_RIM, width=1.5
        )
        # Rueda delantera/derecha
        self.canvas.create_oval(
            cx + half_w - 6 - wheel_r, y_wheel - wheel_r,
            cx + half_w - 6 + wheel_r, y_wheel + wheel_r,
            fill=Theme.CAR_WHEEL, outline=Theme.CAR_RIM, width=1.5
        )

        # 6. Flecha del Vector Velocidad sobre el vehículo
        y_arrow = y_center - half_h - 14
        v = self.current_velocity

        if abs(v) > 1e-4 and self.is_moving:
            # Longitud proporcional a la rapidez (con límites visuales)
            arrow_len = min(max(abs(v) * 2.5, 20), 75)
            x_arrow_start = cx
            x_arrow_end = cx + (arrow_len if v > 0 else -arrow_len)

            self.canvas.create_line(
                x_arrow_start, y_arrow, x_arrow_end, y_arrow,
                fill=Theme.VECTOR_ARROW, width=3,
                arrow=tk.LAST, arrowshape=(10, 12, 4)
            )
            v_sign = "+" if v > 0 else ""
            self.canvas.create_text(
                (x_arrow_start + x_arrow_end) / 2, y_arrow - 9,
                text=f"v⃗ = {v_sign}{v:.1f} m/s",
                fill=Theme.VECTOR_ARROW, font=(Theme.FONT_FAMILY, 8, "bold")
            )
        else:
            # Vehículo detenido o v = 0
            self.canvas.create_text(
                cx, y_arrow,
                text="v⃗ = 0 m/s (Reposo)",
                fill=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8, "italic")
            )

        # 7. Etiqueta flotante de posición actual x(t)
        self.canvas.create_text(
            cx, y_center + half_h + 16,
            text=f"x = {self.current_x:.2f} m",
            fill=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 9, "bold")
        )
