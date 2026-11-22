"""
Módulo del Panel de Control y Configuración para MRUA.

Permite:
- Selección de presets pedagógicos:
    1. Aceleración positiva desde el reposo (v0=0, a>0).
    2. Aceleración positiva con velocidad inicial (v0>0, a>0).
    3. Aceleración negativa con velocidad positiva (frenado hasta detenerse).
    4. Frenado y cambio de sentido (frena, se detiene e invierte su sentido).
    5. Aceleración nula (equivalente a MRU).
- Configuración de x0, v0, a, límites de pista y unidades.
- Controles de simulación: Iniciar, Pausar, Reanudar, Detener y Reiniciar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, Tuple
from .theme import Theme
from ..models.physics import TrackConfig, MRUAParameters
from ..models.experiment_state import ExperimentStatus
from ..models.units import UnitConverter


class MRUAControlPanel(tk.Frame):
    """Panel de configuración de parámetros cinemáticos para MRUA."""

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_stop: Callable[[], None],
        on_reset: Callable[[], None],
        on_config_changed: Callable[[TrackConfig, MRUAParameters], None],
        on_show_summary: Optional[Callable[[], None]] = None,
        on_show_theory: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, padx=12, pady=10, **kwargs)

        self.on_start = on_start
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_stop = on_stop
        self.on_reset = on_reset
        self.on_config_changed = on_config_changed
        self.on_show_summary = on_show_summary
        self.on_show_theory = on_show_theory

        # Variables de control
        self.preset_var = tk.StringVar(value="1. Aceleración positiva desde el reposo (v₀=0, a=+2 m/s²)")
        self.track_min_var = tk.DoubleVar(value=-50.0)
        self.track_max_var = tk.DoubleVar(value=50.0)
        self.x0_var = tk.DoubleVar(value=0.0)
        self.v0_var = tk.DoubleVar(value=0.0)
        self.a_var = tk.DoubleVar(value=2.0)
        self.duration_var = tk.StringVar(value="")  # Vacío = sin límite de tiempo (hasta barrera)

        # Unidades seleccionadas
        self.x0_unit_var = tk.StringVar(value="m")
        self.v0_unit_var = tk.StringVar(value="m/s")
        self.a_unit_var = tk.StringVar(value="m/s²")

        self._build_ui()
        self._apply_preset(self.preset_var.get())

    def _build_ui(self) -> None:
        # --- SECCIÓN 1: PRESETS DIDÁCTICOS ---
        sec_presets = tk.LabelFrame(
            self,
            text=" 1. Casos Didácticos Predefinidos (MRUA) ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=6
        )
        sec_presets.pack(fill=tk.X, pady=(0, 8))

        presets_list = [
            "1. Aceleración positiva desde el reposo (v₀=0, a=+2 m/s²)",
            "2. Aceleración positiva con avance previo (v₀=+5 m/s, a=+3 m/s²)",
            "3. Desaceleración / Frenado (v₀=+20 m/s, a=-2.5 m/s²)",
            "4. Frenado y cambio de sentido (v₀=+16 m/s, a=-4 m/s²)",
            "5. Movimiento en sentido negativo acelerado (v₀=-5 m/s, a=-2 m/s²)",
            "6. Aceleración nula a=0 (Degenera a MRU)",
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

        # --- SECCIÓN 2: PARÁMETROS CINEMÁTICOS ---
        sec_params = tk.LabelFrame(
            self,
            text=" 2. Configuración de Parámetros ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=6
        )
        sec_params.pack(fill=tk.X, pady=(0, 8))

        # Límites de la pista
        tk.Label(
            sec_params,
            text="Límites de pista [x_mín, x_máx] (m):",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "bold")
        ).pack(anchor="w")

        f_limits = tk.Frame(sec_params, bg=Theme.BG_CARD)
        f_limits.pack(fill=tk.X, pady=(1, 6))

        tk.Label(f_limits, text="Min:", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)
        self.ent_min = ttk.Entry(f_limits, textvariable=self.track_min_var, width=6)
        self.ent_min.pack(side=tk.LEFT, padx=3)

        tk.Label(f_limits, text="Max:", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT, padx=(6, 0))
        self.ent_max = ttk.Entry(f_limits, textvariable=self.track_max_var, width=6)
        self.ent_max.pack(side=tk.LEFT, padx=3)

        # Posición inicial x0
        f_x0 = tk.Frame(sec_params, bg=Theme.BG_CARD)
        f_x0.pack(fill=tk.X, pady=3)
        tk.Label(f_x0, text="Posición inicial (x₀):", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 8, "bold")).pack(side=tk.LEFT)
        self.cmb_x0_unit = ttk.Combobox(f_x0, textvariable=self.x0_unit_var, values=["m", "cm", "km"], width=4, state="readonly")
        self.cmb_x0_unit.pack(side=tk.RIGHT)
        self.ent_x0 = ttk.Entry(f_x0, textvariable=self.x0_var, width=8)
        self.ent_x0.pack(side=tk.RIGHT, padx=3)

        # Velocidad inicial v0
        f_v0 = tk.Frame(sec_params, bg=Theme.BG_CARD)
        f_v0.pack(fill=tk.X, pady=3)
        tk.Label(f_v0, text="Velocidad inicial (v₀):", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 8, "bold")).pack(side=tk.LEFT)
        self.cmb_v0_unit = ttk.Combobox(f_v0, textvariable=self.v0_unit_var, values=["m/s", "km/h", "cm/s"], width=4, state="readonly")
        self.cmb_v0_unit.pack(side=tk.RIGHT)
        self.ent_v0 = ttk.Entry(f_v0, textvariable=self.v0_var, width=8)
        self.ent_v0.pack(side=tk.RIGHT, padx=3)

        # Aceleración a
        f_a = tk.Frame(sec_params, bg=Theme.BG_CARD)
        f_a.pack(fill=tk.X, pady=3)
        tk.Label(f_a, text="Aceleración (a):", bg=Theme.BG_CARD, fg="#f59e0b", font=(Theme.FONT_FAMILY, 8, "bold")).pack(side=tk.LEFT)
        self.cmb_a_unit = ttk.Combobox(f_a, textvariable=self.a_unit_var, values=["m/s²", "cm/s²", "km/h²"], width=4, state="readonly")
        self.cmb_a_unit.pack(side=tk.RIGHT)
        self.ent_a = ttk.Entry(f_a, textvariable=self.a_var, width=8)
        self.ent_a.pack(side=tk.RIGHT, padx=3)

        # Duración opcional
        f_dur = tk.Frame(sec_params, bg=Theme.BG_CARD)
        f_dur.pack(fill=tk.X, pady=3)
        tk.Label(f_dur, text="Duración lím. (s):", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)
        self.ent_dur = ttk.Entry(f_dur, textvariable=self.duration_var, width=8)
        self.ent_dur.pack(side=tk.RIGHT, padx=(0, 48))

        # Botón aplicar parámetros
        ttk.Button(
            sec_params,
            text="✓ Aplicar Parámetros",
            style="Primary.TButton",
            command=self._apply_user_parameters
        ).pack(fill=tk.X, pady=(6, 2))

        # Enlazar eventos de modificación
        for ent in (self.ent_min, self.ent_max, self.ent_x0, self.ent_v0, self.ent_a):
            ent.bind("<Return>", lambda e: self._apply_user_parameters())

        # --- SECCIÓN 3: CONTROLES DE SIMULACIÓN ---
        sec_ctrl = tk.LabelFrame(
            self,
            text=" 3. Mando de la Simulación ",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold"),
            padx=8,
            pady=8
        )
        sec_ctrl.pack(fill=tk.X, pady=(0, 8))

        btn_grid = tk.Frame(sec_ctrl, bg=Theme.BG_CARD)
        btn_grid.pack(fill=tk.X)

        self.btn_start = ttk.Button(btn_grid, text="▶ Iniciar", style="Success.TButton", command=self.on_start)
        self.btn_start.grid(row=0, column=0, padx=2, pady=3, sticky="ew")

        self.btn_pause = ttk.Button(btn_grid, text="⏸ Pausar", style="Warning.TButton", command=self.on_pause, state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=2, pady=3, sticky="ew")

        self.btn_resume = ttk.Button(btn_grid, text="⏯ Continuar", style="Success.TButton", command=self.on_resume, state="disabled")
        self.btn_resume.grid(row=1, column=0, padx=2, pady=3, sticky="ew")

        self.btn_stop = ttk.Button(btn_grid, text="⏹ Detener", style="Danger.TButton", command=self.on_stop, state="disabled")
        self.btn_stop.grid(row=1, column=1, padx=2, pady=3, sticky="ew")

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        self.btn_reset = ttk.Button(sec_ctrl, text="↺ Reiniciar Simulación", style="Secondary.TButton", command=self.on_reset)
        self.btn_reset.pack(fill=tk.X, pady=(4, 0))

        # --- SECCIÓN 4: INFORMES Y TEORÍA ---
        sec_tools = tk.Frame(self, bg=Theme.BG_CARD)
        sec_tools.pack(fill=tk.X, pady=(4, 0))

        if self.on_show_summary:
            ttk.Button(
                sec_tools,
                text="📊 Ver Informe MRUA",
                style="Secondary.TButton",
                command=self.on_show_summary
            ).pack(fill=tk.X, pady=2)

        if self.on_show_theory:
            ttk.Button(
                sec_tools,
                text="📖 Ecuaciones y Teoría",
                style="Secondary.TButton",
                command=self.on_show_theory
            ).pack(fill=tk.X, pady=2)

    def _on_preset_selected(self, event=None) -> None:
        self._apply_preset(self.preset_var.get())

    def _apply_preset(self, preset_name: str) -> None:
        if "1. Aceleración positiva desde el reposo" in preset_name:
            self.track_min_var.set(-10.0)
            self.track_max_var.set(90.0)
            self.x0_var.set(0.0)
            self.v0_var.set(0.0)
            self.a_var.set(2.0)
        elif "2. Aceleración positiva con avance previo" in preset_name:
            self.track_min_var.set(-20.0)
            self.track_max_var.set(80.0)
            self.x0_var.set(-10.0)
            self.v0_var.set(5.0)
            self.a_var.set(3.0)
        elif "3. Desaceleración / Frenado" in preset_name:
            self.track_min_var.set(-10.0)
            self.track_max_var.set(90.0)
            self.x0_var.set(0.0)
            self.v0_var.set(20.0)
            self.a_var.set(-2.5)
        elif "4. Frenado y cambio de sentido" in preset_name:
            self.track_min_var.set(-50.0)
            self.track_max_var.set(50.0)
            self.x0_var.set(0.0)
            self.v0_var.set(16.0)
            self.a_var.set(-4.0)
        elif "5. Movimiento en sentido negativo" in preset_name:
            self.track_min_var.set(-80.0)
            self.track_max_var.set(20.0)
            self.x0_var.set(10.0)
            self.v0_var.set(-5.0)
            self.a_var.set(-2.0)
        elif "6. Aceleración nula" in preset_name:
            self.track_min_var.set(-50.0)
            self.track_max_var.set(50.0)
            self.x0_var.set(0.0)
            self.v0_var.set(10.0)
            self.a_var.set(0.0)

        self.x0_unit_var.set("m")
        self.v0_unit_var.set("m/s")
        self.a_unit_var.set("m/s²")
        self._apply_user_parameters()

    def _apply_user_parameters(self) -> None:
        try:
            xmin = self.track_min_var.get()
            xmax = self.track_max_var.get()
            if xmin >= xmax:
                messagebox.showerror("Error de Validación", f"x_min ({xmin}) debe ser menor que x_max ({xmax}).")
                return

            track = TrackConfig(x_min=xmin, x_max=xmax)

            x0_raw = self.x0_var.get()
            x0_si = UnitConverter.length_to_si(x0_raw, self.x0_unit_var.get())

            v0_raw = self.v0_var.get()
            v0_si = UnitConverter.velocity_to_si(v0_raw, self.v0_unit_var.get())

            a_raw = self.a_var.get()
            a_si = UnitConverter.acceleration_to_si(a_raw, self.a_unit_var.get())

            dur_str = self.duration_var.get().strip()
            dur_si = float(dur_str) if dur_str else None

            if not track.contains(x0_si):
                messagebox.showerror(
                    "Error de Validación",
                    f"La posición inicial x₀ = {x0_si:.2f} m está fuera de los límites [{xmin:.2f}, {xmax:.2f}]."
                )
                return

            params = MRUAParameters(x0=x0_si, v0=v0_si, acceleration=a_si, configured_duration=dur_si)
            self.on_config_changed(track, params)
        except ValueError as err:
            messagebox.showerror("Error de Formato", f"Valores numéricos no válidos: {err}")

    def get_current_config(self) -> Tuple[TrackConfig, MRUAParameters]:
        track = TrackConfig(x_min=self.track_min_var.get(), x_max=self.track_max_var.get())
        x0_si = UnitConverter.length_to_si(self.x0_var.get(), self.x0_unit_var.get())
        v0_si = UnitConverter.velocity_to_si(self.v0_var.get(), self.v0_unit_var.get())
        a_si = UnitConverter.acceleration_to_si(self.a_var.get(), self.a_unit_var.get())
        dur_str = self.duration_var.get().strip()
        dur_si = float(dur_str) if dur_str else None
        return track, MRUAParameters(x0=x0_si, v0=v0_si, acceleration=a_si, configured_duration=dur_si)

    def set_simulation_state(self, status: ExperimentStatus) -> None:
        """Sincroniza el estado de habilitación de botones de acuerdo a la máquina de estados."""
        if status == ExperimentStatus.READY:
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.btn_reset.config(state="normal")
        elif status == ExperimentStatus.RUNNING:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_reset.config(state="normal")
        elif status == ExperimentStatus.PAUSED:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="normal")
            self.btn_stop.config(state="normal")
            self.btn_reset.config(state="normal")
        elif status == ExperimentStatus.FINISHED:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.btn_reset.config(state="normal")
