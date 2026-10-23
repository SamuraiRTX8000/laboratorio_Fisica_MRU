"""
Módulo del Controlador de Simulación.

Actúa como intermediario (patrón MVC/Presenter) entre los modelos físicos/temporales
y la interfaz de usuario. Administra el bucle de animación basado en tiempo monotónico,
la actualización periódica de la telemetría, el redibujado de la pista y las gráficas.
"""

import time
from typing import Optional, Callable
from ..models.physics import TrackConfig, MRUParameters, PhysicalState
from ..models.experiment_state import (
    ExperimentStatus,
    ExperimentControllerModel,
    ExperimentSummary,
    MeasurementSample
)


class SimulationController:
    """Controlador principal de la simulación de MRU."""

    def __init__(self, root, get_ui_components: Callable[[], tuple]) -> None:
        """
        Args:
            root: Ventana principal de Tkinter (para programar after()).
            get_ui_components: Función que retorna (track_view, plots_view, telemetry_panel, control_panel).
        """
        self.root = root
        self.get_ui_components = get_ui_components

        # Configuración física activa por defecto
        self.track = TrackConfig(x_min=-50.0, x_max=50.0)
        self.params = MRUParameters(x0=0.0, velocity=10.0)

        # Modelo del experimento
        self.model = ExperimentControllerModel(self.track, self.params)

        # Control del bucle de animación
        self._loop_id: Optional[str] = None
        self._fps_delay_ms = 25  # ~40 FPS para fluidez visual
        self._last_plot_update_time = 0.0
        self._plot_update_interval = 0.08  # Actualizar gráficas cada 80 ms para eficiencia

    @property
    def status(self) -> ExperimentStatus:
        return self.model.status

    @property
    def summary(self) -> ExperimentSummary:
        return self.model.generate_summary()

    @property
    def samples(self) -> list[MeasurementSample]:
        return self.model.samples

    def on_config_changed(self, track: TrackConfig, params: MRUParameters) -> None:
        """Llamado cuando el usuario modifica parámetros antes de iniciar."""
        if self.model.status != ExperimentStatus.READY:
            return

        self.track = track
        self.params = params
        self.model = ExperimentControllerModel(track, params)

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        track_view.set_track_config(track)
        track_view.update_state(self.model.current_physics_state, params.x0, is_moving=False)
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            x0=params.x0,
            configured_v=params.velocity,
            status=self.model.status
        )
        plots_view.reset_plots(x0=params.x0, v=params.velocity)

    def start(self) -> None:
        """Inicia el experimento."""
        if self.model.status != ExperimentStatus.READY:
            return

        self.model.start()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

        # Iniciar bucle de animación
        self._schedule_next_frame()

    def pause(self) -> None:
        """Pausa el experimento."""
        if self.model.status != ExperimentStatus.RUNNING:
            return

        self.model.pause()
        self._update_views_sync(force_plot=True)
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def resume(self) -> None:
        """Reanuda el experimento desde la pausa."""
        if self.model.status != ExperimentStatus.PAUSED:
            return

        self.model.resume()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

        self._schedule_next_frame()

    def stop(self, reason: str = "Detenido por el usuario") -> None:
        """Finaliza definitivamente la simulación."""
        if self.model.status in (ExperimentStatus.FINISHED, ExperimentStatus.READY):
            return

        self._cancel_scheduled_frame()
        self.model.stop(reason)
        self._update_views_sync(force_plot=True)

        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def reset(self) -> None:
        """Reinicia el experimento al estado inicial con los parámetros vigentes."""
        self._cancel_scheduled_frame()
        self.model = ExperimentControllerModel(self.track, self.params)

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

        track_view.update_state(self.model.current_physics_state, self.params.x0, is_moving=False)
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            x0=self.params.x0,
            configured_v=self.params.velocity,
            status=self.model.status
        )
        plots_view.reset_plots(x0=self.params.x0, v=self.params.velocity)

    def _schedule_next_frame(self) -> None:
        """Programa el próximo ciclo de actualización en el event loop de Tkinter."""
        self._cancel_scheduled_frame()
        if self.model.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            self._loop_id = self.root.after(self._fps_delay_ms, self._animation_step)

    def _cancel_scheduled_frame(self) -> None:
        """Cancela llamadas pendientes para evitar bucles zombis."""
        if self._loop_id is not None:
            try:
                self.root.after_cancel(self._loop_id)
            except Exception:
                pass
            self._loop_id = None

    def _animation_step(self) -> None:
        """Paso elemental del bucle de animación."""
        if self.model.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            return

        # 1. Actualizar el modelo lógico
        state = self.model.update()

        # 2. Actualizar las vistas
        self._update_views_sync(force_plot=False)

        # 3. Si el modelo cambió a FINISHED (por ejemplo alcanzó el límite)
        if self.model.status == ExperimentStatus.FINISHED:
            self._cancel_scheduled_frame()
            self._update_views_sync(force_plot=True)
            _, _, telemetry_panel, control_panel = self.get_ui_components()
            control_panel.set_simulation_state(self.model.status)
            telemetry_panel.set_status(self.model.status)
            return

        # 4. Programar siguiente fotograma
        self._schedule_next_frame()

    def _update_views_sync(self, force_plot: bool = False) -> None:
        """Sincroniza los componentes visuales con el estado actual."""
        track_view, plots_view, telemetry_panel, _ = self.get_ui_components()
        state = self.model.current_physics_state
        t_eff, t_total = self.model.get_current_times()
        is_running = (self.model.status == ExperimentStatus.RUNNING)

        # Actualizar pista
        track_view.update_state(state, self.params.x0, is_moving=is_running)

        # Actualizar telemetría
        telemetry_panel.update_telemetry(
            state,
            t_eff=t_eff,
            t_total=t_total,
            x0=self.params.x0,
            configured_v=self.params.velocity,
            status=self.model.status
        )

        # Actualizar gráficas (con limitador de tasa para máxima fluidez)
        now = time.perf_counter()
        if force_plot or (now - self._last_plot_update_time >= self._plot_update_interval):
            self._last_plot_update_time = now
            plots_view.update_plots(
                self.model.samples,
                x0=self.params.x0,
                v=self.params.velocity,
                force=force_plot
            )
