"""
Módulo de la Ventana Principal del Laboratorio Virtual de Cinemática.

Organiza la interfaz de usuario con diseño moderno y ergonómico:
- Barra superior con título institucional, subtítulo del módulo activo y atajos.
- Menú de opciones (Archivo, Experimento, Módulos, Ayuda).
- Navegación central por pestañas (Notebook):
    1. MRU: Movimiento Rectilíneo Uniforme (Pista, Telemetría, Gráficas x-t y v-t).
    2. MRUA: Movimiento Uniformemente Acelerado (Pista interactiva, Telemetría, 3 Gráficas x-t, v-t, a-t).
    3. Caída Libre y Tiro Vertical (Pista vertical con suelo/torre/cúspide, Telemetría, 3 Gráficas y-t, v-t, a-t).
    4. Resolución de Problemas Paso a Paso (Solucionador analítico independiente, unidades multidimensionales, 10 pasos pedagógicos).
- Barra inferior con estado de sesión activa y exportaciones consolidada y multi-sesión.
"""

import os
import subprocess
import platform
import tkinter as tk
from pathlib import Path
from typing import Optional
from tkinter import ttk, messagebox, filedialog, simpledialog
from .theme import Theme
from .track_view import TrackView
from .plots_view import PlotsView
from .telemetry_panel import TelemetryPanel
from .control_panel import ControlPanel
from .mrua_track_view import MRUATrackView
from .mrua_plots_view import MRUAPlotsView
from .specialized_telemetry import MRUATelemetryPanel, VerticalTelemetryPanel
from .mrua_control_panel import MRUAControlPanel
from .vertical_track_view import VerticalTrackView
from .free_fall_control_panel import FreeFallControlPanel
from .solver_view import SolverView
from .dialogs import SummaryDialog, TheoryGuideDialog, SessionManagerDialog
from .detailed_plot_viewer import DetailedPlotViewer
from ..controllers.simulation_controller import (
    SimulationController,
    MRUASimulationController,
    FreeFallSimulationController
)
from ..data.exporter import ExperimentDataExporter
from ..data.schema import SessionMetadata, ExperimentRecord
from ..data.repository import ExperimentRepository
from ..data.consolidator import DatasetConsolidator
from ..data.migrator import LegacyReportMigrator


class MainWindow:
    """Ventana principal de la aplicación."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Laboratorio Virtual de Física Clásica y Cinemática (MRU - MRUA - Caída Libre)")
        self.root.geometry("1300x870")
        self.root.minsize(1024, 720)
        self.root.configure(bg=Theme.BG_DARK)

        # Aplicar estilos TTK modernos
        Theme.apply_ttk_styles(self.root)

        # 1. Inicializar infraestructura persistente de registro científico y datasets
        self.repository = ExperimentRepository()
        self.consolidator = DatasetConsolidator(self.repository)
        self.migrator = LegacyReportMigrator(self.repository)

        # Controladores de simulación para cada módulo
        self.controller: Optional[SimulationController] = None
        self.mrua_controller: Optional[MRUASimulationController] = None
        self.free_fall_controller: Optional[FreeFallSimulationController] = None

        self._build_menu()
        self._build_header()
        self._build_status_bar()
        self._build_main_layout()

        # 2. Inicializar el controlador MRU (preservando retrocompatibilidad)
        self.controller = SimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.track_view,
                self.plots_view,
                self.telemetry_panel,
                self.control_panel
            ),
            repository=self.repository,
            on_experiment_saved=self._on_experiment_saved,
            on_save_error=self._on_save_error
        )
        track, params = self.control_panel.get_current_config()
        self.controller.on_config_changed(track, params)

        # 3. Inicializar el controlador MRUA
        self.mrua_controller = MRUASimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.mrua_track_view,
                self.mrua_plots_view,
                self.mrua_telemetry_panel,
                self.mrua_control_panel
            ),
            repository=self.repository,
            on_experiment_saved=self._on_experiment_saved,
            on_save_error=self._on_save_error
        )
        mrua_track, mrua_params = self.mrua_control_panel.get_current_config()
        self.mrua_controller.on_config_changed(mrua_track, mrua_params)

        # 4. Inicializar el controlador de Caída Libre
        self.free_fall_controller = FreeFallSimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.vertical_track_view,
                self.vertical_plots_view,
                self.vertical_telemetry_panel,
                self.free_fall_control_panel
            ),
            repository=self.repository,
            on_experiment_saved=self._on_experiment_saved,
            on_save_error=self._on_save_error
        )
        ff_params = self.free_fall_control_panel.get_current_config()
        self.free_fall_controller.on_config_changed(ff_params)

        # Refrescar estado visual de la sesión activa
        self._refresh_session_ui()

        # Atajos de teclado útiles dinámicos según el módulo activo
        self.root.bind("<space>", self._on_spacebar_pressed)
        self.root.bind("<Escape>", self._on_escape_pressed)
        self.root.bind("<Control-r>", self._on_reset_pressed)
        self.root.bind("<Control-g>", lambda e: self.show_detailed_plot_viewer())
        self.root.bind("<F11>", lambda e: self.show_detailed_plot_viewer())
        self.root.bind("<Control-e>", lambda e: self.show_export_session_dataset_dialog())

    def _build_menu(self) -> None:
        """Construye la barra de menú superior estándar."""
        menubar = tk.Menu(self.root, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, activebackground=Theme.PRIMARY)
        self.root.config(menu=menubar)

        # Menú Archivo
        menu_file = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Archivo", menu=menu_file)
        menu_file.add_command(label="📦 Exportar Dataset de la Sesión (Ctrl+E)...", command=self.show_export_session_dataset_dialog)
        menu_file.add_command(label="🌐 Exportar Historial Completo (Multi-sesión)...", command=self.show_export_historical_dataset_dialog)
        menu_file.add_separator()
        menu_file.add_command(label="➕ Iniciar Nueva Sesión Experimental...", command=self.create_new_session_dialog)
        menu_file.add_command(label="📑 Gestionar y Reanudar Sesiones...", command=self.show_session_manager_dialog)
        menu_file.add_command(label="🔄 Migrar Informe CSV Antiguo...", command=self.show_migrate_legacy_dialog)
        menu_file.add_command(label="📁 Abrir Directorio de Datos Locales...", command=self.open_data_directory)
        menu_file.add_separator()
        menu_file.add_command(label="💾 Exportar Datos de este Simulacro a CSV (Individual)...", command=lambda: self.show_export_csv_dialog())
        menu_file.add_separator()
        menu_file.add_command(label="Salir", command=self.root.quit)

        # Menú Módulos de Física
        menu_mods = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Módulos", menu=menu_mods)
        menu_mods.add_command(label="1. 🚗 Movimiento Rectilíneo Uniforme (MRU)", command=lambda: self.switch_to_tab(0))
        menu_mods.add_command(label="2. 🏎️ Movimiento Uniformemente Acelerado (MRUA)", command=lambda: self.switch_to_tab(1))
        menu_mods.add_command(label="3. 🍏 Caída Libre y Tiro Vertical", command=lambda: self.switch_to_tab(2))
        menu_mods.add_command(label="4. 🧮 Resolución de Problemas Paso a Paso", command=lambda: self.switch_to_tab(3))

        # Menú Experimento
        menu_exp = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Experimento", menu=menu_exp)
        menu_exp.add_command(label="Iniciar Simulación Activa (Espacio)", command=lambda: self.get_active_controller().start() if self.get_active_controller() else None)
        menu_exp.add_command(label="Pausar / Continuar (Espacio)", command=self._toggle_pause_resume)
        menu_exp.add_command(label="Finalizar Simulación (Esc)", command=lambda: self.get_active_controller().stop() if self.get_active_controller() else None)
        menu_exp.add_command(label="Reiniciar (Ctrl+R)", command=lambda: self.get_active_controller().reset() if self.get_active_controller() else None)
        menu_exp.add_separator()
        menu_exp.add_command(label="🔍 Ampliar Gráfica y Ver en Detalle... (Ctrl+G)", command=lambda: self.show_detailed_plot_viewer())
        menu_exp.add_command(label="📊 Ver Informe Científico", command=lambda: self.show_summary_dialog())

        # Menú Ayuda
        menu_help = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Ayuda", menu=menu_help)
        menu_help.add_command(label="Guía Teórica de Cinemática (MRU, MRUA, Gravedad)...", command=self.show_theory_dialog)
        menu_help.add_command(label="Acerca del Laboratorio...", command=self._show_about_dialog)

    def _build_header(self) -> None:
        """Construye el encabezado superior con títulos descriptivos."""
        header_frame = tk.Frame(self.root, bg=Theme.BG_CARD, padx=16, pady=8)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_box = tk.Frame(header_frame, bg=Theme.BG_CARD)
        title_box.pack(side=tk.LEFT)

        lbl_title = tk.Label(
            title_box,
            text="LABORATORIO VIRTUAL DE FÍSICA Y CINEMÁTICA",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=Theme.FONT_TITLE
        )
        lbl_title.pack(anchor="w")

        self.lbl_sub = tk.Label(
            title_box,
            text="Módulo Activo: Movimiento Rectilíneo Uniforme (MRU) | x(t) = x₀ + v · t",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        )
        self.lbl_sub.pack(anchor="w")

        info_box = tk.Frame(header_frame, bg=Theme.BG_CARD)
        info_box.pack(side=tk.RIGHT)

        tk.Label(
            info_box,
            text="Física General I — Ingeniería de Sistemas | IA & Datasets",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 9, "bold")
        ).pack(anchor="e")

        tk.Label(
            info_box,
            text="Atajos: [Espacio] Iniciar/Pausar | [Esc] Finalizar | [Ctrl+R] Reiniciar | [Ctrl+E] Exportar Dataset",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "italic")
        ).pack(anchor="e")

    def _build_status_bar(self) -> None:
        """Construye la barra inferior con estado de sesión y registro de datasets."""
        self.status_bar = tk.Frame(self.root, bg=Theme.BG_CARD, padx=12, pady=5)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        info_frame = tk.Frame(self.status_bar, bg=Theme.BG_CARD)
        info_frame.pack(side=tk.LEFT)

        self.lbl_status_session = tk.Label(
            info_frame,
            text="📁 Sesión: ...",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 9, "bold")
        )
        self.lbl_status_session.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_status_count = tk.Label(
            info_frame,
            text="Experimentos: 0",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 9)
        )
        self.lbl_status_count.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_status_save = tk.Label(
            info_frame,
            text="✓ Guardado automático activo",
            bg=Theme.BG_CARD,
            fg=Theme.SUCCESS,
            font=(Theme.FONT_FAMILY, 9)
        )
        self.lbl_status_save.pack(side=tk.LEFT)

        btn_frame = tk.Frame(self.status_bar, bg=Theme.BG_CARD)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(
            btn_frame,
            text="📦 Exportar Sesión",
            style="Primary.TButton",
            command=self.show_export_session_dataset_dialog
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_frame,
            text="🌐 Exportar Historial",
            style="Secondary.TButton",
            command=self.show_export_historical_dataset_dialog
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_frame,
            text="📑 Sesiones",
            style="Secondary.TButton",
            command=self.show_session_manager_dialog
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_frame,
            text="📁 Directorio",
            style="Secondary.TButton",
            command=self.open_data_directory
        ).pack(side=tk.LEFT, padx=3)

    def _build_main_layout(self) -> None:
        """Construye las 4 secciones principales diferenciadas del laboratorio mediante pestañas ergonómicas."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 6))

        # =====================================================================
        # PESTAÑA 1: MOVIMIENTO RECTILÍNEO UNIFORME (MRU)
        # =====================================================================
        tab_mru = tk.Frame(self.notebook, bg=Theme.BG_DARK, padx=4, pady=4)
        self.notebook.add(tab_mru, text="  🚗 Movimiento Rectilíneo Uniforme (MRU)  ")

        mru_split = tk.Frame(tab_mru, bg=Theme.BG_DARK)
        mru_split.pack(fill=tk.BOTH, expand=True)

        self.control_panel = ControlPanel(
            mru_split,
            on_start=lambda: self.controller.start() if self.controller else None,
            on_pause=lambda: self.controller.pause() if self.controller else None,
            on_resume=lambda: self.controller.resume() if self.controller else None,
            on_stop=lambda: self.controller.stop() if self.controller else None,
            on_reset=lambda: self.controller.reset() if self.controller else None,
            on_config_changed=lambda t, p: self.controller.on_config_changed(t, p) if self.controller else None,
            on_show_summary=lambda: self.show_summary_dialog(self.controller),
            on_export_csv=lambda: self.show_export_csv_dialog(self.controller),
            on_show_theory=self.show_theory_dialog,
            on_expand_plot=lambda: self.show_detailed_plot_viewer(self.controller),
            on_export_session_dataset=self.show_export_session_dataset_dialog,
            on_export_historical_dataset=self.show_export_historical_dataset_dialog,
            on_manage_sessions=self.show_session_manager_dialog,
            on_new_session=self.create_new_session_dialog,
            width=320
        )
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.control_panel.pack_propagate(False)

        mru_right = tk.Frame(mru_split, bg=Theme.BG_DARK)
        mru_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.track_view = TrackView(
            mru_right,
            track=self.control_panel.get_current_config()[0]
        )
        self.track_view.pack(fill=tk.X, pady=(0, 4))

        self.telemetry_panel = TelemetryPanel(mru_right)
        self.telemetry_panel.pack(fill=tk.X, pady=(0, 4))

        self.plots_view = PlotsView(
            mru_right,
            on_expand_plot=lambda: self.show_detailed_plot_viewer(self.controller)
        )
        self.plots_view.pack(fill=tk.BOTH, expand=True)

        # =====================================================================
        # PESTAÑA 2: MOVIMIENTO UNIFORMEMENTE ACELERADO (MRUA)
        # =====================================================================
        tab_mrua = tk.Frame(self.notebook, bg=Theme.BG_DARK, padx=4, pady=4)
        self.notebook.add(tab_mrua, text="  🏎️ Movimiento Uniformemente Acelerado (MRUA)  ")

        mrua_split = tk.Frame(tab_mrua, bg=Theme.BG_DARK)
        mrua_split.pack(fill=tk.BOTH, expand=True)

        self.mrua_control_panel = MRUAControlPanel(
            mrua_split,
            on_start=lambda: self.mrua_controller.start() if self.mrua_controller else None,
            on_pause=lambda: self.mrua_controller.pause() if self.mrua_controller else None,
            on_resume=lambda: self.mrua_controller.resume() if self.mrua_controller else None,
            on_stop=lambda: self.mrua_controller.stop() if self.mrua_controller else None,
            on_reset=lambda: self.mrua_controller.reset() if self.mrua_controller else None,
            on_config_changed=lambda t, p: self.mrua_controller.on_config_changed(t, p) if self.mrua_controller else None,
            on_show_summary=lambda: self.show_summary_dialog(self.mrua_controller),
            on_show_theory=self.show_theory_dialog,
            width=320
        )
        self.mrua_control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.mrua_control_panel.pack_propagate(False)

        mrua_right = tk.Frame(mrua_split, bg=Theme.BG_DARK)
        mrua_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.mrua_track_view = MRUATrackView(
            mrua_right,
            track=self.mrua_control_panel.get_current_config()[0]
        )
        self.mrua_track_view.pack(fill=tk.X, pady=(0, 4))

        self.mrua_telemetry_panel = MRUATelemetryPanel(mrua_right)
        self.mrua_telemetry_panel.pack(fill=tk.X, pady=(0, 4))

        self.mrua_plots_view = MRUAPlotsView(
            mrua_right,
            is_vertical=False,
            on_expand_plot=lambda: self.show_detailed_plot_viewer(self.mrua_controller)
        )
        self.mrua_plots_view.pack(fill=tk.BOTH, expand=True)

        # =====================================================================
        # PESTAÑA 3: CAÍDA LIBRE Y LANZAMIENTO VERTICAL
        # =====================================================================
        tab_ff = tk.Frame(self.notebook, bg=Theme.BG_DARK, padx=4, pady=4)
        self.notebook.add(tab_ff, text="  🍏 Caída Libre y Tiro Vertical  ")

        ff_split = tk.Frame(tab_ff, bg=Theme.BG_DARK)
        ff_split.pack(fill=tk.BOTH, expand=True)

        self.free_fall_control_panel = FreeFallControlPanel(
            ff_split,
            on_start=lambda: self.free_fall_controller.start() if self.free_fall_controller else None,
            on_pause=lambda: self.free_fall_controller.pause() if self.free_fall_controller else None,
            on_resume=lambda: self.free_fall_controller.resume() if self.free_fall_controller else None,
            on_stop=lambda: self.free_fall_controller.stop() if self.free_fall_controller else None,
            on_reset=lambda: self.free_fall_controller.reset() if self.free_fall_controller else None,
            on_config_changed=lambda p: self.free_fall_controller.on_config_changed(p) if self.free_fall_controller else None,
            on_show_summary=lambda: self.show_summary_dialog(self.free_fall_controller),
            on_show_theory=self.show_theory_dialog,
            width=320
        )
        self.free_fall_control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.free_fall_control_panel.pack_propagate(False)

        ff_right = tk.Frame(ff_split, bg=Theme.BG_DARK)
        ff_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.vertical_track_view = VerticalTrackView(ff_right, max_height=60.0)
        self.vertical_track_view.pack(fill=tk.X, pady=(0, 4))

        self.vertical_telemetry_panel = VerticalTelemetryPanel(ff_right)
        self.vertical_telemetry_panel.pack(fill=tk.X, pady=(0, 4))

        self.vertical_plots_view = MRUAPlotsView(
            ff_right,
            is_vertical=True,
            on_expand_plot=lambda: self.show_detailed_plot_viewer(self.free_fall_controller)
        )
        self.vertical_plots_view.pack(fill=tk.BOTH, expand=True)

        # =====================================================================
        # PESTAÑA 4: RESOLUCIÓN DE PROBLEMAS PASO A PASO
        # =====================================================================
        tab_solver = tk.Frame(self.notebook, bg=Theme.BG_DARK, padx=4, pady=4)
        self.notebook.add(tab_solver, text="  🧮 Resolución de Problemas  ")

        self.solver_view = SolverView(tab_solver)
        self.solver_view.pack(fill=tk.BOTH, expand=True)

        # Enlace del evento de cambio de pestaña para ajustar subtítulos e interactividad
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def switch_to_tab(self, index: int) -> None:
        """Cambia programáticamente a la pestaña especificada (0: MRU, 1: MRUA, 2: Caída Libre, 3: Solver)."""
        try:
            self.notebook.select(index)
        except Exception:
            pass

    def _on_tab_changed(self, event=None) -> None:
        """Actualiza el subtítulo descriptivo al alternar de módulo."""
        try:
            idx = self.notebook.index(self.notebook.select())
            descriptions = [
                ("MRU", "x(t) = x₀ + v · t | Movimiento a velocidad constante (a = 0)"),
                ("MRUA", "x(t) = x₀ + v₀·t + ½·a·t² | v(t) = v₀ + a·t | Aceleración constante"),
                ("Caída Libre", "y(t) = y₀ + v₀·t - ½·g·t² | Gravedad g hacia abajo (a = -g)"),
                ("Solucionador Paso a Paso", "Motor algebraico riguroso | Despejes, sustitución e interpretación")
            ]
            if idx < len(descriptions):
                mod_name, mod_desc = descriptions[idx]
                self.lbl_sub.config(text=f"Módulo Activo: {mod_name} | {mod_desc}")
        except Exception:
            pass

    def get_active_controller(self):
        """Retorna el controlador de simulación correspondiente a la pestaña actualmente en foco."""
        try:
            idx = self.notebook.index(self.notebook.select())
            if idx == 0:
                return self.controller
            elif idx == 1:
                return self.mrua_controller
            elif idx == 2:
                return self.free_fall_controller
            return self.controller
        except Exception:
            return self.controller

    def _on_spacebar_pressed(self, event) -> None:
        """Maneja la barra espaciadora para Iniciar, Pausar o Reanudar el simulador activo."""
        ctrl = self.get_active_controller()
        if ctrl is None:
            return
        status = ctrl.status
        from ..models.experiment_state import ExperimentStatus
        if status == ExperimentStatus.READY:
            ctrl.start()
        elif status == ExperimentStatus.RUNNING:
            ctrl.pause()
        elif status == ExperimentStatus.PAUSED:
            ctrl.resume()

    def _on_escape_pressed(self, event=None) -> None:
        """Detiene la simulación del módulo activo."""
        ctrl = self.get_active_controller()
        if ctrl:
            ctrl.stop("Detenido mediante Escape")

    def _on_reset_pressed(self, event=None) -> None:
        """Reinicia la simulación del módulo activo."""
        ctrl = self.get_active_controller()
        if ctrl:
            ctrl.reset()

    def _toggle_pause_resume(self) -> None:
        """Alterna entre pausar y continuar el simulador activo."""
        ctrl = self.get_active_controller()
        if ctrl is None:
            return
        from ..models.experiment_state import ExperimentStatus
        if ctrl.status == ExperimentStatus.RUNNING:
            ctrl.pause()
        elif ctrl.status == ExperimentStatus.PAUSED:
            ctrl.resume()
            self.controller.pause()
        elif self.controller.status == ExperimentStatus.PAUSED:
            self.controller.resume()

    def show_summary_dialog(self) -> None:
        """Abre la ventana modal del informe de resultados analíticos."""
        if self.controller is None:
            return
        summary = self.controller.summary
        samples = self.controller.samples
        track = self.controller.track
        params = self.controller.params

        SummaryDialog(
            parent=self.root,
            summary=summary,
            samples=samples,
            track=track,
            params=params,
            on_export_callback=self.show_export_csv_dialog
        )

    def show_export_csv_dialog(self) -> None:
        """Abre el diálogo para exportar datos reales a CSV."""
        if self.controller is None or not self.controller.samples:
            messagebox.showinfo("Aviso", "No hay datos de simulación disponibles para exportar.")
            return

        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar Datos Telemétricos a CSV",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="mru_mediciones.csv"
        )
        if filepath:
            try:
                ExperimentDataExporter.export_to_file(
                    filepath,
                    self.controller.samples,
                    self.controller.summary,
                    self.controller.track,
                    self.controller.params
                )
                messagebox.showinfo(
                    "Exportación Exitosa",
                    f"Se exportaron con éxito {len(self.controller.samples)} muestras a:\n{filepath}",
                    parent=self.root
                )
            except Exception as e:
                messagebox.showerror("Error al Exportar", f"Error al guardar el archivo:\n{str(e)}", parent=self.root)

    def show_detailed_plot_viewer(self) -> None:
        """Abre el Visor Científico Avanzado para ampliar e inspeccionar el plano cartesiano."""
        if self.controller is None:
            return
        summary = self.controller.summary
        samples = self.controller.samples
        track = self.controller.track
        params = self.controller.params

        DetailedPlotViewer(
            parent=self.root,
            samples=samples,
            summary=summary,
            track=track,
            params=params
        )

    def show_theory_dialog(self) -> None:
        """Abre la ventana modal con la guía teórica interactiva."""
        TheoryGuideDialog(parent=self.root)

    def _show_about_dialog(self) -> None:
        """Muestra cuadro de diálogo acerca de la aplicación."""
        messagebox.showinfo(
            "Acerca del Simulador",
            "Laboratorio Virtual de Cinemática (MRU)\n"
            "Desarrollado para estudiantes de Ingeniería de Sistemas.\n\n"
            "• Modelo: Ecuación horaria analítica x(t) = x₀ + v·t\n"
            "• Tiempo monotónico de alta resolución\n"
            "• Gráficas científicas en tiempo real (x-t y v-t)\n"
            "• Sistema de Registro Científico y Datasets para IA / Machine Learning\n"
            "• Exportación normalizada compatible con pandas y scikit-learn\n\n"
            "Licencia: Académica y Educativa.",
            parent=self.root
        )

    # -------------------------------------------------------------------------
    # MÉTODOS DE GESTIÓN DE SESIONES, DATASETS Y EXPORTACIÓN CIENTÍFICA
    # -------------------------------------------------------------------------

    def _refresh_session_ui(self, status_msg: Optional[str] = None) -> None:
        """Actualiza los indicadores de sesión en la barra de estado y panel de control."""
        sess = self.repository.active_session
        sess_id = sess.session_id
        count = sess.experiment_count

        disp_id = sess_id if len(sess_id) <= 24 else sess_id[:21] + "..."
        self.lbl_status_session.config(text=f"📁 Sesión: {disp_id}")
        self.lbl_status_count.config(text=f"Experimentos: {count}")

        if status_msg:
            self.lbl_status_save.config(text=status_msg, fg=Theme.SUCCESS)
        else:
            self.lbl_status_save.config(text="✓ Guardado automático activo", fg=Theme.SUCCESS)

        if hasattr(self, "control_panel") and self.control_panel:
            self.control_panel.update_session_display(sess_id, count, status_msg)

    def _on_experiment_saved(self, record: ExperimentRecord) -> None:
        """Notificación disparada tras el auto-guardado exitoso de un experimento."""
        msg = f"✓ Exp. #{record.experiment_number} guardado automáticamente ({record.experiment_id})"
        self._refresh_session_ui(status_msg=msg)

    def _on_save_error(self, err: Exception) -> None:
        """Notificación disparada ante fallos en la persistencia del experimento."""
        err_msg = f"⚠️ Error al guardar: {str(err)[:35]}"
        self._refresh_session_ui(status_msg=err_msg)
        messagebox.showwarning(
            "Aviso de Validación / Persistencia",
            f"El experimento no pudo ser registrado automáticamente:\n{str(err)}",
            parent=self.root
        )

    def show_export_session_dataset_dialog(self, session_id: Optional[str] = None) -> None:
        """Exporta el dataset consolidado de una sesión específica (por defecto la activa)."""
        target_sess_id = session_id or self.repository.active_session.session_id
        exps = self.repository.load_session_experiments(target_sess_id)

        if not exps:
            confirm = messagebox.askyesno(
                "Sesión sin experimentos",
                f"La sesión '{target_sess_id}' aún no contiene experimentos finalizados.\n"
                "¿Desea exportar el dataset con el esquema vacío y documentación?",
                parent=self.root
            )
            if not confirm:
                return

        target_dir = filedialog.askdirectory(
            parent=self.root,
            title=f"Seleccionar Directorio de Destino para Exportar Dataset de la Sesión [{target_sess_id}]"
        )
        if not target_dir:
            return

        out_path = Path(target_dir).resolve()

        # Comprobar confirmación de sobrescritura si ya existen archivos
        if (out_path / "experiments.csv").exists():
            overwrite = messagebox.askyesno(
                "Confirmar Sobrescritura",
                f"El directorio destino ya contiene archivos de dataset (experiments.csv).\n"
                f"¿Desea sobrescribir los archivos con la exportación de la sesión '{target_sess_id}'?",
                parent=self.root
            )
            if not overwrite:
                return

        try:
            exported_dir = self.consolidator.export_session_dataset(target_sess_id, str(out_path))
            obs = self.repository.load_session_observations(target_sess_id)
            messagebox.showinfo(
                "Exportación Exitosa",
                f"Dataset de la sesión exportado correctamente a:\n{exported_dir}\n\n"
                f"• Experimentos: {len(exps)}\n"
                f"• Observaciones: {len(obs)}\n\n"
                "Archivos generados:\n"
                "✓ experiments.csv\n"
                "✓ observations.csv\n"
                "✓ manifest.json\n"
                "✓ README_dataset.md",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Error en la Exportación",
                f"Ocurrió un error al exportar el dataset de la sesión:\n{str(e)}",
                parent=self.root
            )

    def show_export_historical_dataset_dialog(self) -> None:
        """Exporta el historial completo acumulado de todas las sesiones registradas."""
        all_exps = self.repository.load_all_experiments()
        all_obs = self.repository.load_all_observations()

        if not all_exps:
            messagebox.showinfo(
                "Historial Vacío",
                "No existen experimentos almacenados en el repositorio actualmente.",
                parent=self.root
            )
            return

        target_dir = filedialog.askdirectory(
            parent=self.root,
            title="Seleccionar Directorio para Exportar Historial Completo Consolidado"
        )
        if not target_dir:
            return

        out_path = Path(target_dir).resolve()

        if (out_path / "experiments.csv").exists():
            overwrite = messagebox.askyesno(
                "Confirmar Sobrescritura",
                f"El directorio seleccionado ya contiene archivos de exportación previos.\n"
                "¿Desea generar una nueva instantánea y sobrescribirlos?",
                parent=self.root
            )
            if not overwrite:
                return

        try:
            exported_dir = self.consolidator.export_historical_dataset(str(out_path))
            total_sessions = len(self.repository.list_all_sessions())
            messagebox.showinfo(
                "Historial Exportado",
                f"Dataset consolidado histórico exportado exitosamente a:\n{exported_dir}\n\n"
                f"• Sesiones combinadas: {total_sessions}\n"
                f"• Experimentos totales: {len(all_exps)}\n"
                f"• Muestras telemétricas: {len(all_obs)}\n\n"
                "Archivos generados:\n"
                "✓ experiments.csv\n"
                "✓ observations.csv\n"
                "✓ manifest.json\n"
                "✓ README_dataset.md",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Error al Exportar Historial",
                f"Error al exportar el historial completo:\n{str(e)}",
                parent=self.root
            )

    def create_new_session_dialog(self) -> None:
        """Abre un cuadro de diálogo para iniciar una nueva sesión experimental."""
        notes = simpledialog.askstring(
            "Nueva Sesión Experimental",
            "Ingrese notas o descripción para la nueva sesión (opcional):",
            parent=self.root
        )
        if notes is not None:
            new_sess = self.repository.create_new_session(notes=notes or "")
            self._refresh_session_ui(status_msg="✓ Nueva sesión iniciada")
            messagebox.showinfo(
                "Sesión Iniciada",
                f"Se ha iniciado la nueva sesión:\n{new_sess.session_id}",
                parent=self.root
            )

    def show_session_manager_dialog(self) -> None:
        """Abre el gestor modal de sesiones experimentales."""
        SessionManagerDialog(
            parent=self.root,
            repository=self.repository,
            on_session_switched=lambda s: self._refresh_session_ui(status_msg=f"✓ Sesión activa: {s.session_id}"),
            on_export_session_callback=self.show_export_session_dataset_dialog
        )

    def show_migrate_legacy_dialog(self) -> None:
        """Permite al usuario seleccionar un archivo CSV antiguo para importarlo al repositorio."""
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title="Seleccionar Informe CSV de Versión Anterior para Migrar",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return

        try:
            rec, count = self.migrator.migrate_file(filepath)
            if rec is not None:
                self._refresh_session_ui(status_msg=f"✓ Migrado: {rec.experiment_id}")
                messagebox.showinfo(
                    "Migración Exitosa",
                    f"Se migró correctamente el informe al repositorio activo.\n\n"
                    f"• ID de Experimento: {rec.experiment_id}\n"
                    f"• Modelo Físico: {rec.physics_model}\n"
                    f"• Procedencia: {rec.data_source}\n"
                    f"• Muestras telemétricas: {count}\n"
                    f"• Archivo original conservado intacto.",
                    parent=self.root
                )
            else:
                messagebox.showinfo(
                    "Informe ya Existente",
                    "Este archivo ya fue migrado previamente al repositorio (identificado por hash SHA-256).\n"
                    "No se produjeron duplicaciones.",
                    parent=self.root
                )
        except Exception as e:
            messagebox.showerror(
                "Error de Migración",
                f"No se pudo procesar el archivo como informe legado:\n{str(e)}",
                parent=self.root
            )

    def open_data_directory(self) -> None:
        """Abre la carpeta de datos en el explorador de archivos del sistema operativo."""
        data_path = str(self.repository.base_dir)
        try:
            current_os = platform.system()
            if current_os == "Linux":
                subprocess.Popen(["xdg-open", data_path])
            elif current_os == "Darwin":
                subprocess.Popen(["open", data_path])
            elif current_os == "Windows":
                os.startfile(data_path)
            else:
                messagebox.showinfo("Directorio de Datos", f"Ruta de almacenamiento local:\n{data_path}", parent=self.root)
        except Exception:
            messagebox.showinfo("Directorio de Datos", f"Ruta de almacenamiento local:\n{data_path}", parent=self.root)
