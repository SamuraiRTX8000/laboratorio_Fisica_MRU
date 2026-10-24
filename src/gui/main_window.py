"""
Módulo de la Ventana Principal del Laboratorio Virtual de Cinemática.

Organiza la interfaz de usuario con diseño moderno y ergonómico:
- Barra superior con título institucional, subtítulo y estado.
- Menú de opciones (Archivo, Experimento, Herramientas, Ayuda).
- Panel lateral izquierdo para configuración de pista, magnitudes y botones de control.
- Panel derecho principal con:
    1. Pista virtual interactiva (Canvas con recta graduada, origen, vector y vehículo).
    2. Panel de telemetría de alta resolución (tarjetas métricas digitales).
    3. Gráficas científicas de Matplotlib en tiempo real (x-t y v-t).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .theme import Theme
from .track_view import TrackView
from .plots_view import PlotsView
from .telemetry_panel import TelemetryPanel
from .control_panel import ControlPanel
from .dialogs import SummaryDialog, TheoryGuideDialog
from .detailed_plot_viewer import DetailedPlotViewer
from ..controllers.simulation_controller import SimulationController
from ..data.exporter import ExperimentDataExporter


class MainWindow:
    """Ventana principal de la aplicación."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Laboratorio Virtual de Cinemática: Movimiento Rectilíneo Uniforme (MRU)")
        self.root.geometry("1280x820")
        self.root.minsize(1024, 700)
        self.root.configure(bg=Theme.BG_DARK)

        # Aplicar estilos TTK modernos
        Theme.apply_ttk_styles(self.root)

        # Controlador de simulación (se inicializa tras crear los componentes)
        self.controller: SimulationController = None

        self._build_menu()
        self._build_header()
        self._build_main_layout()

        # Inicializar el controlador
        self.controller = SimulationController(
            root=self.root,
            get_ui_components=lambda: (
                self.track_view,
                self.plots_view,
                self.telemetry_panel,
                self.control_panel
            )
        )

        # Enviar configuración inicial a la vista
        track, params = self.control_panel.get_current_config()
        self.controller.on_config_changed(track, params)

        # Atajos de teclado útiles
        self.root.bind("<space>", self._on_spacebar_pressed)
        self.root.bind("<Escape>", lambda e: self.controller.stop("Detenido mediante Escape"))
        self.root.bind("<Control-r>", lambda e: self.controller.reset())
        self.root.bind("<Control-g>", lambda e: self.show_detailed_plot_viewer())
        self.root.bind("<F11>", lambda e: self.show_detailed_plot_viewer())

    def _build_menu(self) -> None:
        """Construye la barra de menú superior estándar."""
        menubar = tk.Menu(self.root, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, activebackground=Theme.PRIMARY)
        self.root.config(menu=menubar)

        # Menú Archivo
        menu_file = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Archivo", menu=menu_file)
        menu_file.add_command(label="Exportar Datos a CSV...", command=self.show_export_csv_dialog)
        menu_file.add_separator()
        menu_file.add_command(label="Salir", command=self.root.quit)

        # Menú Experimento
        menu_exp = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Experimento", menu=menu_exp)
        menu_exp.add_command(label="Iniciar (Espacio)", command=lambda: self.controller.start())
        menu_exp.add_command(label="Pausar / Continuar (Espacio)", command=self._toggle_pause_resume)
        menu_exp.add_command(label="Finalizar (Esc)", command=lambda: self.controller.stop())
        menu_exp.add_command(label="Reiniciar (Ctrl+R)", command=lambda: self.controller.reset())
        menu_exp.add_separator()
        menu_exp.add_command(label="🔍 Ampliar Gráfica y Ver en Detalle... (Ctrl+G)", command=self.show_detailed_plot_viewer)
        menu_exp.add_command(label="📊 Ver Informe Científico", command=self.show_summary_dialog)

        # Menú Ayuda
        menu_help = tk.Menu(menubar, tearoff=0, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT)
        menubar.add_cascade(label="Ayuda", menu=menu_help)
        menu_help.add_command(label="Guía Teórica de Cinemática...", command=self.show_theory_dialog)
        menu_help.add_command(label="Acerca del Laboratorio...", command=self._show_about_dialog)

    def _build_header(self) -> None:
        """Construye el encabezado superior con títulos descriptivos."""
        header_frame = tk.Frame(self.root, bg=Theme.BG_CARD, padx=16, pady=8)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_box = tk.Frame(header_frame, bg=Theme.BG_CARD)
        title_box.pack(side=tk.LEFT)

        lbl_title = tk.Label(
            title_box,
            text="LABORATORIO VIRTUAL DE CINEMÁTICA",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=Theme.FONT_TITLE
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="Simulador Interactivo de Movimiento Rectilíneo Uniforme (MRU) | x(t) = x₀ + v · t",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        )
        lbl_sub.pack(anchor="w")

        info_box = tk.Frame(header_frame, bg=Theme.BG_CARD)
        info_box.pack(side=tk.RIGHT)

        tk.Label(
            info_box,
            text="Física General I — Ingeniería de Sistemas",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_LIGHT,
            font=(Theme.FONT_FAMILY, 9, "bold")
        ).pack(anchor="e")

        tk.Label(
            info_box,
            text="Atajos: [Espacio] Iniciar/Pausar | [Esc] Finalizar | [Ctrl+R] Reiniciar",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 8, "italic")
        ).pack(anchor="e")

    def _build_main_layout(self) -> None:
        """Construye la distribución de paneles con diseño responsivo."""
        main_container = tk.Frame(self.root, bg=Theme.BG_DARK, padx=10, pady=8)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo (Configuración y Controles)
        self.control_panel = ControlPanel(
            main_container,
            on_start=lambda: self.controller.start() if self.controller else None,
            on_pause=lambda: self.controller.pause() if self.controller else None,
            on_resume=lambda: self.controller.resume() if self.controller else None,
            on_stop=lambda: self.controller.stop() if self.controller else None,
            on_reset=lambda: self.controller.reset() if self.controller else None,
            on_config_changed=lambda t, p: self.controller.on_config_changed(t, p) if self.controller else None,
            on_show_summary=self.show_summary_dialog,
            on_export_csv=self.show_export_csv_dialog,
            on_show_theory=self.show_theory_dialog,
            on_expand_plot=self.show_detailed_plot_viewer,
            width=320
        )
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.control_panel.pack_propagate(False)

        # Panel derecho (Pista, Telemetría y Gráficas)
        right_container = tk.Frame(main_container, bg=Theme.BG_DARK)
        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 1. Pista virtual superior
        self.track_view = TrackView(
            right_container,
            track=self.control_panel.get_current_config()[0]
        )
        self.track_view.pack(fill=tk.X, pady=(0, 6))

        # 2. Panel de telemetría intermedio
        self.telemetry_panel = TelemetryPanel(right_container)
        self.telemetry_panel.pack(fill=tk.X, pady=(0, 6))

        # 3. Gráficas científicas inferiores
        self.plots_view = PlotsView(
            right_container,
            on_expand_plot=self.show_detailed_plot_viewer
        )
        self.plots_view.pack(fill=tk.BOTH, expand=True)

    def _on_spacebar_pressed(self, event) -> None:
        """Maneja la barra espaciadora para Iniciar, Pausar o Reanudar de forma intuitiva."""
        if self.controller is None:
            return
        status = self.controller.status
        from ..models.experiment_state import ExperimentStatus
        if status == ExperimentStatus.READY:
            self.controller.start()
        elif status == ExperimentStatus.RUNNING:
            self.controller.pause()
        elif status == ExperimentStatus.PAUSED:
            self.controller.resume()

    def _toggle_pause_resume(self) -> None:
        """Alterna entre pausar y continuar."""
        if self.controller is None:
            return
        from ..models.experiment_state import ExperimentStatus
        if self.controller.status == ExperimentStatus.RUNNING:
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
            "• Exportación de datos telemétricos a CSV\n\n"
            "Licencia: Académica y Educativa.",
            parent=self.root
        )
