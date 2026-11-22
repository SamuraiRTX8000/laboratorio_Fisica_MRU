"""
Módulo del Controlador de Simulación.

Actúa como intermediario (patrón MVC/Presenter) entre los modelos físicos/temporales
y la interfaz de usuario. Administra el bucle de animación basado en tiempo monotónico,
la actualización periódica de la telemetría, el redibujado de la pista y las gráficas.
"""

import time
import datetime
from typing import Optional, Callable
from ..models.physics import (
    TrackConfig,
    MRUParameters,
    MRUAParameters,
    FreeFallParameters,
    PhysicalState
)
from ..models.experiment_state import (
    ExperimentStatus,
    ExperimentControllerModel,
    ExperimentSummary,
    MeasurementSample
)
from ..data.schema import PhysicsModel, DataSource, ExperimentRecord
from ..data.repository import ExperimentRepository


class SimulationController:
    """Controlador principal de la simulación de MRU."""

    def __init__(
        self,
        root,
        get_ui_components: Callable[[], tuple],
        repository: Optional[ExperimentRepository] = None,
        on_experiment_saved: Optional[Callable[[ExperimentRecord], None]] = None,
        on_save_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """
        Args:
            root: Ventana principal de Tkinter (para programar after()).
            get_ui_components: Función que retorna (track_view, plots_view, telemetry_panel, control_panel).
            repository: Repositorio persistente de datos científicos (opcional).
            on_experiment_saved: Callback ejecutado cuando se auto-guarda un experimento.
            on_save_error: Callback ejecutado en caso de error de validación o guardado.
        """
        self.root = root
        self.get_ui_components = get_ui_components
        self.repository = repository
        self.on_experiment_saved = on_experiment_saved
        self.on_save_error = on_save_error

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

        # Control de persistencia y deduplicación automática
        self._is_recorded: bool = False
        self._experiment_started_at: Optional[str] = None

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

        self._is_recorded = False
        self._experiment_started_at = None
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

        self._is_recorded = False
        self._experiment_started_at = datetime.datetime.now().isoformat()
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

        # Guardado automático transparente en el repositorio
        self._save_experiment_if_completed()

        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def reset(self) -> None:
        """Reinicia el experimento al estado inicial con los parámetros vigentes."""
        self._cancel_scheduled_frame()
        self.model = ExperimentControllerModel(self.track, self.params)
        self._is_recorded = False
        self._experiment_started_at = None

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
            self._save_experiment_if_completed()
            _, _, telemetry_panel, control_panel = self.get_ui_components()
            control_panel.set_simulation_state(self.model.status)
            telemetry_panel.set_status(self.model.status)
            return

        # 4. Programar siguiente fotograma
        self._schedule_next_frame()

    def _save_experiment_if_completed(self) -> Optional[ExperimentRecord]:
        """
        Guarda automáticamente el experimento completado si no ha sido registrado aún.
        Previene duplicaciones y asegura integridad física antes de persistir.
        """
        if self._is_recorded:
            return None

        if self.repository is None:
            return None

        # Exigir al menos 2 muestras para considerar que hubo simulación real
        if len(self.model.samples) < 2:
            return None

        self._is_recorded = True
        now_iso = datetime.datetime.now().isoformat()
        started_at = self._experiment_started_at or now_iso
        completed_at = now_iso

        summary = self.model.generate_summary()
        try:
            record = self.repository.record_completed_experiment(
                summary=summary,
                samples=self.model.samples,
                track=self.track,
                params=self.params,
                started_at=started_at,
                completed_at=completed_at,
                physics_model=PhysicsModel.MRU,
                data_source=DataSource.IDEAL_SIMULATION
            )
            if record and self.on_experiment_saved:
                self.on_experiment_saved(record)
            return record
        except Exception as e:
            if self.on_save_error:
                self.on_save_error(e)
            else:
                print(f"[SimulationController] Error al guardar experimento automáticamente: {e}")
            return None

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


class MRUASimulationController:
    """Controlador principal de la simulación de MRUA (Movimiento Rectilíneo Uniformemente Acelerado)."""

    def __init__(
        self,
        root,
        get_ui_components: Callable[[], tuple],
        repository: Optional[ExperimentRepository] = None,
        on_experiment_saved: Optional[Callable[[ExperimentRecord], None]] = None,
        on_save_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        self.root = root
        self.get_ui_components = get_ui_components
        self.repository = repository
        self.on_experiment_saved = on_experiment_saved
        self.on_save_error = on_save_error

        # Configuración por defecto: a = +2 m/s², v0 = 0 m/s, x0 = 0 m
        self.track = TrackConfig(x_min=-10.0, x_max=90.0)
        self.params = MRUAParameters(x0=0.0, v0=0.0, acceleration=2.0)
        self.model = ExperimentControllerModel(self.track, self.params)

        self._loop_id: Optional[str] = None
        self._fps_delay_ms = 25
        self._last_plot_update_time = 0.0
        self._plot_update_interval = 0.08
        self._is_recorded: bool = False
        self._experiment_started_at: Optional[str] = None

    @property
    def status(self) -> ExperimentStatus:
        return self.model.status

    @property
    def summary(self) -> ExperimentSummary:
        return self.model.generate_summary()

    @property
    def samples(self) -> list[MeasurementSample]:
        return self.model.samples

    def on_config_changed(self, track: TrackConfig, params: MRUAParameters) -> None:
        """Llamado cuando el usuario modifica parámetros antes de iniciar."""
        if self.model.status != ExperimentStatus.READY:
            return

        self._is_recorded = False
        self._experiment_started_at = None
        self.track = track
        self.params = params
        self.model = ExperimentControllerModel(track, params)

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        track_view.set_track_config(track)
        turnaround_x = getattr(self.model.physics, "turnaround_position", None)
        track_view.update_state(
            self.model.current_physics_state,
            params.x0,
            is_moving=False,
            turnaround_x=turnaround_x
        )
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            x0=params.x0,
            v0=params.v0,
            acceleration=params.acceleration,
            status=self.model.status
        )
        plots_view.reset_plots(x0=params.x0, v0=params.v0, a=params.acceleration)

    def start(self) -> None:
        if self.model.status != ExperimentStatus.READY:
            return
        self._is_recorded = False
        self._experiment_started_at = datetime.datetime.now().isoformat()
        self.model.start()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        self._schedule_next_frame()

    def pause(self) -> None:
        if self.model.status != ExperimentStatus.RUNNING:
            return
        self.model.pause()
        self._update_views_sync(force_plot=True)
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def resume(self) -> None:
        if self.model.status != ExperimentStatus.PAUSED:
            return
        self.model.resume()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        self._schedule_next_frame()

    def stop(self, reason: str = "Detenido por el usuario") -> None:
        if self.model.status in (ExperimentStatus.FINISHED, ExperimentStatus.READY):
            return
        self._cancel_scheduled_frame()
        self.model.stop(reason)
        self._update_views_sync(force_plot=True)
        self._save_experiment_if_completed()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def reset(self) -> None:
        self._cancel_scheduled_frame()
        self.model = ExperimentControllerModel(self.track, self.params)
        self._is_recorded = False
        self._experiment_started_at = None

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        turnaround_x = getattr(self.model.physics, "turnaround_position", None)
        track_view.update_state(
            self.model.current_physics_state,
            self.params.x0,
            is_moving=False,
            turnaround_x=turnaround_x
        )
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            x0=self.params.x0,
            v0=self.params.v0,
            acceleration=self.params.acceleration,
            status=self.model.status
        )
        plots_view.reset_plots(x0=self.params.x0, v0=self.params.v0, a=self.params.acceleration)

    def _schedule_next_frame(self) -> None:
        self._cancel_scheduled_frame()
        if self.model.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            self._loop_id = self.root.after(self._fps_delay_ms, self._animation_step)

    def _cancel_scheduled_frame(self) -> None:
        if self._loop_id is not None:
            try:
                self.root.after_cancel(self._loop_id)
            except Exception:
                pass
            self._loop_id = None

    def _animation_step(self) -> None:
        if self.model.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            return
        state = self.model.update()
        self._update_views_sync(force_plot=False)
        if self.model.status == ExperimentStatus.FINISHED:
            self._cancel_scheduled_frame()
            self._update_views_sync(force_plot=True)
            self._save_experiment_if_completed()
            _, _, telemetry_panel, control_panel = self.get_ui_components()
            control_panel.set_simulation_state(self.model.status)
            telemetry_panel.set_status(self.model.status)
            return
        self._schedule_next_frame()

    def _save_experiment_if_completed(self) -> Optional[ExperimentRecord]:
        if self._is_recorded or self.repository is None or len(self.model.samples) < 2:
            return None
        self._is_recorded = True
        now_iso = datetime.datetime.now().isoformat()
        started_at = self._experiment_started_at or now_iso
        completed_at = now_iso
        summary = self.model.generate_summary()
        try:
            record = self.repository.record_completed_experiment(
                summary=summary,
                samples=self.model.samples,
                track=self.track,
                params=self.params,
                started_at=started_at,
                completed_at=completed_at,
                physics_model=PhysicsModel.MRUA,
                data_source=DataSource.IDEAL_SIMULATION
            )
            if record and self.on_experiment_saved:
                self.on_experiment_saved(record)
            return record
        except Exception as e:
            if self.on_save_error:
                self.on_save_error(e)
            else:
                print(f"[MRUASimulationController] Error al guardar experimento: {e}")
            return None

    def _update_views_sync(self, force_plot: bool = False) -> None:
        track_view, plots_view, telemetry_panel, _ = self.get_ui_components()
        state = self.model.current_physics_state
        t_eff, t_total = self.model.get_current_times()
        is_running = (self.model.status == ExperimentStatus.RUNNING)

        turnaround_x = getattr(self.model.physics, "turnaround_position", None)
        track_view.update_state(
            state,
            self.params.x0,
            is_moving=is_running,
            turnaround_x=turnaround_x
        )
        telemetry_panel.update_telemetry(
            state,
            t_eff=t_eff,
            t_total=t_total,
            x0=self.params.x0,
            v0=self.params.v0,
            acceleration=self.params.acceleration,
            status=self.model.status
        )
        now = time.perf_counter()
        if force_plot or (now - self._last_plot_update_time >= self._plot_update_interval):
            self._last_plot_update_time = now
            plots_view.update_plots(
                self.model.samples,
                x0=self.params.x0,
                v0=self.params.v0,
                a=self.params.acceleration,
                force=force_plot
            )


class FreeFallSimulationController:
    """Controlador principal de la simulación de Caída Libre y Lanzamiento Vertical."""

    def __init__(
        self,
        root,
        get_ui_components: Callable[[], tuple],
        repository: Optional[ExperimentRepository] = None,
        on_experiment_saved: Optional[Callable[[ExperimentRecord], None]] = None,
        on_save_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        self.root = root
        self.get_ui_components = get_ui_components
        self.repository = repository
        self.on_experiment_saved = on_experiment_saved
        self.on_save_error = on_save_error

        # Escenario por defecto: y0 = 45 m, v0 = 0 m/s, g = 9.81 m/s²
        self.track = TrackConfig(x_min=0.0, x_max=1000.0)
        self.params = FreeFallParameters(y0=45.0, v0=0.0, g=9.81)
        self.model = ExperimentControllerModel(self.track, self.params)

        self._loop_id: Optional[str] = None
        self._fps_delay_ms = 25
        self._last_plot_update_time = 0.0
        self._plot_update_interval = 0.08
        self._is_recorded: bool = False
        self._experiment_started_at: Optional[str] = None

    @property
    def status(self) -> ExperimentStatus:
        return self.model.status

    @property
    def summary(self) -> ExperimentSummary:
        return self.model.generate_summary()

    @property
    def samples(self) -> list[MeasurementSample]:
        return self.model.samples

    def on_config_changed(self, params: FreeFallParameters) -> None:
        """Llamado cuando el usuario modifica parámetros verticales."""
        if self.model.status != ExperimentStatus.READY:
            return

        self._is_recorded = False
        self._experiment_started_at = None
        self.params = params
        self.model = ExperimentControllerModel(self.track, params)

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        h_max_val = getattr(self.model.physics, "h_max", params.y0)
        t_impact_val = getattr(self.model.physics, "t_impact", 0.0)
        track_view.set_environment(
            max_height=max(60.0, params.y0 * 1.5, h_max_val * 1.2),
            initial_y=params.y0,
            gravity=params.g
        )
        track_view.update_state(
            self.model.current_physics_state,
            params.y0,
            is_moving=False,
            h_max=h_max_val
        )
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            y0=params.y0,
            v0=params.v0,
            g=params.g,
            h_max=h_max_val,
            t_impact=t_impact_val,
            status=self.model.status
        )
        plots_view.reset_plots(x0=params.y0, v0=params.v0, a=-params.g)

    def start(self) -> None:
        if self.model.status != ExperimentStatus.READY:
            return
        self._is_recorded = False
        self._experiment_started_at = datetime.datetime.now().isoformat()
        self.model.start()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        self._schedule_next_frame()

    def pause(self) -> None:
        if self.model.status != ExperimentStatus.RUNNING:
            return
        self.model.pause()
        self._update_views_sync(force_plot=True)
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def resume(self) -> None:
        if self.model.status != ExperimentStatus.PAUSED:
            return
        self.model.resume()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        self._schedule_next_frame()

    def stop(self, reason: str = "Detenido por el usuario") -> None:
        if self.model.status in (ExperimentStatus.FINISHED, ExperimentStatus.READY):
            return
        self._cancel_scheduled_frame()
        self.model.stop(reason)
        self._update_views_sync(force_plot=True)
        self._save_experiment_if_completed()
        _, _, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)

    def reset(self) -> None:
        self._cancel_scheduled_frame()
        self.model = ExperimentControllerModel(self.track, self.params)
        self._is_recorded = False
        self._experiment_started_at = None

        track_view, plots_view, telemetry_panel, control_panel = self.get_ui_components()
        control_panel.set_simulation_state(self.model.status)
        telemetry_panel.set_status(self.model.status)
        h_max_val = getattr(self.model.physics, "h_max", self.params.y0)
        t_impact_val = getattr(self.model.physics, "t_impact", 0.0)
        track_view.update_state(
            self.model.current_physics_state,
            self.params.y0,
            is_moving=False,
            h_max=h_max_val
        )
        telemetry_panel.update_telemetry(
            self.model.current_physics_state,
            t_eff=0.0,
            t_total=0.0,
            y0=self.params.y0,
            v0=self.params.v0,
            g=self.params.g,
            h_max=h_max_val,
            t_impact=t_impact_val,
            status=self.model.status
        )
        plots_view.reset_plots(x0=self.params.y0, v0=self.params.v0, a=-self.params.g)

    def _schedule_next_frame(self) -> None:
        self._cancel_scheduled_frame()
        if self.model.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            self._loop_id = self.root.after(self._fps_delay_ms, self._animation_step)

    def _cancel_scheduled_frame(self) -> None:
        if self._loop_id is not None:
            try:
                self.root.after_cancel(self._loop_id)
            except Exception:
                pass
            self._loop_id = None

    def _animation_step(self) -> None:
        if self.model.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            return
        state = self.model.update()
        self._update_views_sync(force_plot=False)
        if self.model.status == ExperimentStatus.FINISHED:
            self._cancel_scheduled_frame()
            self._update_views_sync(force_plot=True)
            self._save_experiment_if_completed()
            _, _, telemetry_panel, control_panel = self.get_ui_components()
            control_panel.set_simulation_state(self.model.status)
            telemetry_panel.set_status(self.model.status)
            return
        self._schedule_next_frame()

    def _save_experiment_if_completed(self) -> Optional[ExperimentRecord]:
        if self._is_recorded or self.repository is None or len(self.model.samples) < 2:
            return None
        self._is_recorded = True
        now_iso = datetime.datetime.now().isoformat()
        started_at = self._experiment_started_at or now_iso
        completed_at = now_iso
        summary = self.model.generate_summary()
        try:
            record = self.repository.record_completed_experiment(
                summary=summary,
                samples=self.model.samples,
                track=self.track,
                params=self.params,
                started_at=started_at,
                completed_at=completed_at,
                physics_model=PhysicsModel.CAIDA_LIBRE,
                data_source=DataSource.IDEAL_SIMULATION
            )
            if record and self.on_experiment_saved:
                self.on_experiment_saved(record)
            return record
        except Exception as e:
            if self.on_save_error:
                self.on_save_error(e)
            else:
                print(f"[FreeFallSimulationController] Error al guardar experimento: {e}")
            return None

    def _update_views_sync(self, force_plot: bool = False) -> None:
        track_view, plots_view, telemetry_panel, _ = self.get_ui_components()
        state = self.model.current_physics_state
        t_eff, t_total = self.model.get_current_times()
        is_running = (self.model.status == ExperimentStatus.RUNNING)

        h_max_val = getattr(self.model.physics, "h_max", self.params.y0)
        t_impact_val = getattr(self.model.physics, "t_impact", 0.0)
        track_view.update_state(
            state,
            self.params.y0,
            is_moving=is_running,
            h_max=h_max_val
        )
        telemetry_panel.update_telemetry(
            state,
            t_eff=t_eff,
            t_total=t_total,
            y0=self.params.y0,
            v0=self.params.v0,
            g=self.params.g,
            h_max=h_max_val,
            t_impact=t_impact_val,
            status=self.model.status
        )
        now = time.perf_counter()
        if force_plot or (now - self._last_plot_update_time >= self._plot_update_interval):
            self._last_plot_update_time = now
            plots_view.update_plots(
                self.model.samples,
                x0=self.params.y0,
                v0=self.params.v0,
                a=-self.params.g,
                force=force_plot
            )
