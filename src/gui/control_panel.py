"""
Módulo del Panel de Control y Configuración del Experimento.

Permite:
- Configurar límites de la pista (x_min, x_max), posición inicial (x0) y velocidad (v).
- Seleccionar presets pedagógicos rápidos.
- Validar las entradas antes del inicio del experimento.
- Controlar la simulación: Iniciar, Pausar, Continuar, Finalizar y Reiniciar.
- Acceder a informes analíticos, exportación a CSV y guía teórica.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from .theme import Theme
from ..models.physics import TrackConfig, MRUParameters
from ..models.experiment_state import ExperimentStatus


class ControlPanel(tk.Frame):
    """Panel lateral de configuración de parámetros y botones de mando."""

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_stop: Callable[[], None],
        on_reset: Callable[[], None],
        on_config_changed: Callable[[TrackConfig, MRUParameters], None],
        on_show_summary: Callable[[], None],
        on_export_csv: Callable[[], None],
        on_show_theory: Callable[[], None],
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, padx=12, pady=12, **kwargs)

        self.on_start = on_start
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_stop = on_stop
        self.on_reset = on_reset
        self.on_config_changed = on_config_changed
        self.on_show_summary = on_show_summary
        self.on_export_csv = on_export_csv
        self.on_show_theory = on_show_theory

        # Variables de control
        self.preset_var = tk.StringVar(value="Personalizado")
        self.track_min_var = tk.DoubleVar(value=-50.0)
        self.track_max_var = tk.DoubleVar(value=50.0)
        self.x0_var = tk.DoubleVar(value=0.0)
        self.v_var = tk.DoubleVar(value=10.0)
        self.direction_var = tk.StringVar(value="+")  # "+" o "-"
        self.speed_mag_var = tk.DoubleVar(value=10.0)
        self.sim_speed_var = tk.StringVar(value="1.0x (Tiempo Real)")

        self._initialized = False
        self._build_ui()
        self._initialized = True
        self._sync_velocity_from_mag()

    def _build_ui(self) -> None:
        """Construye las secciones del panel de configuración."""
        # --- SECCIÓN 1: PRESETS DIDÁCTICOS ---
        sec_presets = tk.LabelFrame(
            self,
            text=" 1. Casos Didácticos Predefinidos ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=6
        )
        sec_presets.pack(fill=tk.X, pady=(0, 10))

        presets_list = [
            "1. MRU Básico hacia la derecha (x0=0, v=+10 m/s)",
            "2. Posición inicial positiva (x0=+20, v=+15 m/s)",
            "3. Sentido negativo hacia la izquierda (x0=+40, v=-12 m/s)",
            "4. Vehículo en reposo (v = 0 m/s)",
            "5. Pista métrica estándar 0 a 100m (x0=0, v=+20 m/s)",
            "Personalizado"
        ]
        self.cmb_presets = ttk.Combobox(
            sec_presets,
            textvariable=self.preset_var,
            values=presets_list,
            state="readonly"
        )
        self.cmb_presets.pack(fill=tk.X, pady=2)
        self.cmb_presets.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # --- SECCIÓN 2: PARÁMETROS DEL EXPERIMENTO ---
        self.sec_params = tk.LabelFrame(
            self,
            text=" 2. Configuración de Parámetros ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=6
        )
        self.sec_params.pack(fill=tk.X, pady=(0, 10))

        # Límites de la pista
        lbl_track = tk.Label(
            self.sec_params,
            text="Límites de la pista [x_min, x_max] (m):",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 8, "bold")
        )
        lbl_track.pack(anchor="w")

        frame_limits = tk.Frame(self.sec_params, bg=Theme.BG_CARD)
        frame_limits.pack(fill=tk.X, pady=(2, 6))

        tk.Label(frame_limits, text="Min:", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)
        self.ent_xmin = ttk.Entry(frame_limits, textvariable=self.track_min_var, width=6)
        self.ent_xmin.pack(side=tk.LEFT, padx=(2, 8))

        tk.Label(frame_limits, text="Max:", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)
        self.ent_xmax = ttk.Entry(frame_limits, textvariable=self.track_max_var, width=6)
        self.ent_xmax.pack(side=tk.LEFT, padx=(2, 4))

        btn_apply_track = ttk.Button(frame_limits, text="Fijar", width=5, command=self._apply_track_limits)
        btn_apply_track.pack(side=tk.RIGHT)

        # Posición inicial x0
        lbl_x0 = tk.Label(
            self.sec_params,
            text="Posición inicial x₀ (m):",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 8, "bold")
        )
        lbl_x0.pack(anchor="w")

        frame_x0 = tk.Frame(self.sec_params, bg=Theme.BG_CARD)
        frame_x0.pack(fill=tk.X, pady=(2, 6))

        self.scale_x0 = ttk.Scale(
            frame_x0,
            from_=self.track_min_var.get(),
            to=self.track_max_var.get(),
            variable=self.x0_var,
            orient=tk.HORIZONTAL,
            command=self._on_slider_x0_change
        )
        self.scale_x0.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.spin_x0 = ttk.Spinbox(
            frame_x0,
            from_=self.track_min_var.get(),
            to=self.track_max_var.get(),
            textvariable=self.x0_var,
            width=6,
            command=self._on_spin_x0_change
        )
        self.spin_x0.pack(side=tk.RIGHT)
        self.spin_x0.bind("<Return>", lambda e: self._on_spin_x0_change())

        # Velocidad constante (Magnitud y Sentido)
        lbl_v = tk.Label(
            self.sec_params,
            text="Velocidad constante v (m/s):",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 8, "bold")
        )
        lbl_v.pack(anchor="w")

        # Sentido (+ / -)
        frame_dir = tk.Frame(self.sec_params, bg=Theme.BG_CARD)
        frame_dir.pack(fill=tk.X, pady=(2, 4))

        tk.Label(frame_dir, text="Sentido:", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)

        rb_pos = tk.Radiobutton(
            frame_dir,
            text="Derecha (+)",
            variable=self.direction_var,
            value="+",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.PRIMARY,
            command=self._sync_velocity_from_mag,
            font=(Theme.FONT_FAMILY, 8)
        )
        rb_pos.pack(side=tk.LEFT, padx=4)

        rb_neg = tk.Radiobutton(
            frame_dir,
            text="Izquierda (-)",
            variable=self.direction_var,
            value="-",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.PRIMARY,
            command=self._sync_velocity_from_mag,
            font=(Theme.FONT_FAMILY, 8)
        )
        rb_neg.pack(side=tk.LEFT, padx=4)

        # Magnitud de rapidez
        frame_v = tk.Frame(self.sec_params, bg=Theme.BG_CARD)
        frame_v.pack(fill=tk.X, pady=(2, 6))

        self.scale_v = ttk.Scale(
            frame_v,
            from_=0.0,
            to=50.0,
            variable=self.speed_mag_var,
            orient=tk.HORIZONTAL,
            command=self._on_slider_v_change
        )
        self.scale_v.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.spin_v = ttk.Spinbox(
            frame_v,
            from_=0.0,
            to=100.0,
            textvariable=self.speed_mag_var,
            width=6,
            command=self._on_spin_v_change
        )
        self.spin_v.pack(side=tk.RIGHT)
        self.spin_v.bind("<Return>", lambda e: self._on_spin_v_change())

        # Indicador de velocidad resultante
        self.lbl_v_result = tk.Label(
            self.sec_params,
            text="v = +10.00 m/s  (|v| = 10.00 m/s)",
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 8, "bold"),
            pady=3
        )
        self.lbl_v_result.pack(fill=tk.X, pady=(2, 4))

        # Mensaje de advertencia o validación
        self.lbl_validation = tk.Label(
            self.sec_params,
            text="Configuración válida lista.",
            bg=Theme.BG_CARD,
            fg=Theme.SUCCESS,
            font=(Theme.FONT_FAMILY, 8),
            wraplength=260,
            justify=tk.LEFT
        )
        self.lbl_validation.pack(fill=tk.X, pady=(2, 0))

        # --- SECCIÓN 3: CONTROLES DEL EXPERIMENTO ---
        sec_controls = tk.LabelFrame(
            self,
            text=" 3. Controles del Experimento ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=8
        )
        sec_controls.pack(fill=tk.X, pady=(0, 10))

        # Fila 1: Iniciar y Pausar
        btn_row1 = tk.Frame(sec_controls, bg=Theme.BG_CARD)
        btn_row1.pack(fill=tk.X, pady=(0, 4))

        self.btn_start = ttk.Button(
            btn_row1,
            text="▶  INICIAR",
            style="Success.TButton",
            command=self.on_start
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self.btn_pause = ttk.Button(
            btn_row1,
            text="⏸  PAUSAR",
            style="Warning.TButton",
            command=self.on_pause,
            state=tk.DISABLED
        )
        self.btn_pause.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        # Fila 2: Continuar y Finalizar
        btn_row2 = tk.Frame(sec_controls, bg=Theme.BG_CARD)
        btn_row2.pack(fill=tk.X, pady=(0, 4))

        self.btn_resume = ttk.Button(
            btn_row2,
            text="⏯  CONTINUAR",
            style="Primary.TButton",
            command=self.on_resume,
            state=tk.DISABLED
        )
        self.btn_resume.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self.btn_stop = ttk.Button(
            btn_row2,
            text="⏹  FINALIZAR",
            style="Danger.TButton",
            command=self.on_stop,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        # Fila 3: Reiniciar
        self.btn_reset = ttk.Button(
            sec_controls,
            text="🔄  REINICIAR EXPERIMENTO",
            style="Secondary.TButton",
            command=self.on_reset
        )
        self.btn_reset.pack(fill=tk.X, pady=(2, 0))

        # --- SECCIÓN 4: HERRAMIENTAS Y RESULTADOS ---
        sec_tools = tk.LabelFrame(
            self,
            text=" 4. Análisis y Herramientas ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=6
        )
        sec_tools.pack(fill=tk.X, pady=(0, 0))

        self.btn_summary = ttk.Button(
            sec_tools,
            text="📊  Ver Informe Científico",
            style="Secondary.TButton",
            command=self.on_show_summary
        )
        self.btn_summary.pack(fill=tk.X, pady=2)

        self.btn_export = ttk.Button(
            sec_tools,
            text="💾  Exportar Datos a CSV",
            style="Secondary.TButton",
            command=self.on_export_csv
        )
        self.btn_export.pack(fill=tk.X, pady=2)

        self.btn_theory = ttk.Button(
            sec_tools,
            text="📘  Guía Didáctica de Cinemática",
            style="Secondary.TButton",
            command=self.on_show_theory
        )
        self.btn_theory.pack(fill=tk.X, pady=2)

    def _on_preset_selected(self, event=None) -> None:
        """Aplica la configuración del preset didáctico seleccionado."""
        val = self.preset_var.get()
        if "1. MRU Básico" in val:
            self._apply_preset_values(-50.0, 50.0, 0.0, 10.0, "+")
        elif "2. Posición inicial positiva" in val:
            self._apply_preset_values(-50.0, 50.0, 20.0, 15.0, "+")
        elif "3. Sentido negativo" in val:
            self._apply_preset_values(-50.0, 50.0, 40.0, 12.0, "-")
        elif "4. Vehículo en reposo" in val:
            self._apply_preset_values(-50.0, 50.0, 0.0, 0.0, "+")
        elif "5. Pista métrica estándar" in val:
            self._apply_preset_values(0.0, 100.0, 0.0, 20.0, "+")

    def _apply_preset_values(self, x_min: float, x_max: float, x0: float, speed: float, direction: str) -> None:
        """Aplica un lote de valores y notifica el cambio."""
        self.track_min_var.set(x_min)
        self.track_max_var.set(x_max)
        self._update_scale_ranges(x_min, x_max)
        self.x0_var.set(x0)
        self.speed_mag_var.set(speed)
        self.direction_var.set(direction)
        self._sync_velocity_from_mag()
        self._validate_and_emit_change()

    def _apply_track_limits(self) -> None:
        """Valida y actualiza los límites de la pista ingresados manualmente."""
        try:
            xmin = float(self.track_min_var.get())
            xmax = float(self.track_max_var.get())
            if xmin >= xmax:
                messagebox.showerror("Error de Validación", "x_min debe ser estrictamente menor que x_max.")
                return
            self._update_scale_ranges(xmin, xmax)
            # Asegurar que x0 esté dentro
            if self.x0_var.get() < xmin:
                self.x0_var.set(xmin)
            elif self.x0_var.get() > xmax:
                self.x0_var.set(xmax)
            self._validate_and_emit_change()
        except ValueError:
            messagebox.showerror("Error", "Los límites deben ser valores numéricos válidos.")

    def _update_scale_ranges(self, xmin: float, xmax: float) -> None:
        """Actualiza el rango del slider de x0."""
        self.scale_x0.configure(from_=xmin, to=xmax)
        self.spin_x0.configure(from_=xmin, to=xmax)

    def _on_slider_x0_change(self, val: str) -> None:
        """Al mover el slider de x0."""
        self.preset_var.set("Personalizado")
        self._validate_and_emit_change()

    def _on_spin_x0_change(self) -> None:
        """Al cambiar el spinbox de x0."""
        self.preset_var.set("Personalizado")
        self._validate_and_emit_change()

    def _on_slider_v_change(self, val: str) -> None:
        """Al mover el slider de velocidad."""
        self.preset_var.set("Personalizado")
        self._sync_velocity_from_mag()
        self._validate_and_emit_change()

    def _on_spin_v_change(self) -> None:
        """Al cambiar el spinbox de velocidad."""
        self.preset_var.set("Personalizado")
        self._sync_velocity_from_mag()
        self._validate_and_emit_change()

    def _sync_velocity_from_mag(self) -> None:
        """Calcula la velocidad con signo a partir de la rapidez y el sentido."""
        mag = abs(self.speed_mag_var.get())
        sign = 1.0 if self.direction_var.get() == "+" else -1.0
        v = mag * sign
        self.v_var.set(v)

        sign_str = "+" if v >= 0 else ""
        self.lbl_v_result.config(text=f"v = {sign_str}{v:.2f} m/s  (|v| = {mag:.2f} m/s)")
        self._validate_and_emit_change()

    def _validate_and_emit_change(self) -> None:
        """Verifica la consistencia física de la configuración y notifica al controlador."""
        try:
            xmin = self.track_min_var.get()
            xmax = self.track_max_var.get()
            x0 = self.x0_var.get()
            v = self.v_var.get()

            track = TrackConfig(x_min=xmin, x_max=xmax)
            params = MRUParameters(x0=x0, velocity=v)

            # Validación de límites
            if not track.contains(x0):
                self.lbl_validation.config(text=f"⚠️ x₀ ({x0:.1f}m) está fuera de la pista [{xmin}, {xmax}]", fg=Theme.DANGER)
                self.btn_start.configure(state=tk.DISABLED)
                return

            if v > 0 and abs(x0 - xmax) < 1e-4:
                self.lbl_validation.config(text="⚠️ Ya está en el límite derecho; no puede avanzar hacia la derecha.", fg=Theme.DANGER)
                self.btn_start.configure(state=tk.DISABLED)
                return

            if v < 0 and abs(x0 - xmin) < 1e-4:
                self.lbl_validation.config(text="⚠️ Ya está en el límite izquierdo; no puede avanzar hacia la izquierda.", fg=Theme.DANGER)
                self.btn_start.configure(state=tk.DISABLED)
                return

            if abs(v) < 1e-6:
                self.lbl_validation.config(text="ℹ️ Velocidad nula: el móvil permanecerá en reposo (MRU con v=0).", fg=Theme.PRIMARY)
            else:
                self.lbl_validation.config(text="✓ Configuración físicamente válida.", fg=Theme.SUCCESS)

            self.btn_start.configure(state=tk.NORMAL)
            if self._initialized and self.on_config_changed:
                self.on_config_changed(track, params)

        except Exception as e:
            self.lbl_validation.config(text=f"⚠️ {str(e)}", fg=Theme.DANGER)
            self.btn_start.configure(state=tk.DISABLED)

    def set_simulation_state(self, status: ExperimentStatus) -> None:
        """Actualiza la disponibilidad de botones y controles según el estado del simulador."""
        if status == ExperimentStatus.READY:
            self.btn_start.configure(state=tk.NORMAL)
            self.btn_pause.configure(state=tk.DISABLED)
            self.btn_resume.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.DISABLED)
            self.btn_reset.configure(state=tk.NORMAL)
            self._set_inputs_enabled(True)

        elif status == ExperimentStatus.RUNNING:
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_pause.configure(state=tk.NORMAL)
            self.btn_resume.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.NORMAL)
            self.btn_reset.configure(state=tk.DISABLED)
            self._set_inputs_enabled(False)

        elif status == ExperimentStatus.PAUSED:
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_pause.configure(state=tk.DISABLED)
            self.btn_resume.configure(state=tk.NORMAL)
            self.btn_stop.configure(state=tk.NORMAL)
            self.btn_reset.configure(state=tk.NORMAL)
            self._set_inputs_enabled(False)

        elif status == ExperimentStatus.FINISHED:
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_pause.configure(state=tk.DISABLED)
            self.btn_resume.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.DISABLED)
            self.btn_reset.configure(state=tk.NORMAL)
            self._set_inputs_enabled(False)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita los controles de configuración."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.cmb_presets.configure(state="readonly" if enabled else tk.DISABLED)
        self.ent_xmin.configure(state=state)
        self.ent_xmax.configure(state=state)
        self.scale_x0.configure(state=state)
        self.spin_x0.configure(state=state)
        self.scale_v.configure(state=state)
        self.spin_v.configure(state=state)

    def get_current_config(self) -> tuple[TrackConfig, MRUParameters]:
        """Obtiene la configuración actual instanciada."""
        track = TrackConfig(x_min=self.track_min_var.get(), x_max=self.track_max_var.get())
        params = MRUParameters(x0=self.x0_var.get(), velocity=self.v_var.get())
        return track, params
