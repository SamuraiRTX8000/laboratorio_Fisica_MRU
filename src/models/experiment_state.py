"""
Módulo de Gestión de Estado y Cronometría del Experimento.

Implementa una máquina de estados determinista y un control de tiempo monotónico
de alta precisión (usando time.perf_counter).

Garantiza la estricta separación entre:
    1. Tiempo total o de pared (t_total): Duración total del experimento desde el
       primer inicio, incluyendo todos los periodos de pausa.
    2. Tiempo efectivo de movimiento (t_eff): Tiempo durante el cual el cuerpo
       estuvo efectivamente desplazándose con velocidad constante v.
"""

from enum import Enum, auto
import time
from dataclasses import dataclass
from typing import List, Optional, Callable
from .physics import MRUPhysicsModel, PhysicalState, TrackConfig, MRUParameters


class ExperimentStatus(Enum):
    """Estados del ciclo de vida del experimento cinemático."""
    READY = auto()       # Escenario preparado, t=0, esperando iniciar
    RUNNING = auto()     # En movimiento activo, acumulando tiempo efectivo
    PAUSED = auto()      # Pausado temporalmente por el usuario, t_eff congelado
    FINISHED = auto()    # Finalizado por alcanzar límite o por orden del usuario

    @property
    def label(self) -> str:
        names = {
            ExperimentStatus.READY: "PREPARADO",
            ExperimentStatus.RUNNING: "EN MOVIMIENTO",
            ExperimentStatus.PAUSED: "PAUSADO",
            ExperimentStatus.FINISHED: "FINALIZADO",
        }
        return names[self]


@dataclass(frozen=True)
class MeasurementSample:
    """Muestra de telemetría registrada en un instante dado."""
    sample_id: int
    t_total: float      # Tiempo total de experimento (s)
    t_eff: float        # Tiempo efectivo de movimiento (s)
    position: float     # Posición x(t) (m)
    displacement: float # Desplazamiento acumulado (m)
    distance: float     # Distancia acumulada (m)
    velocity: float     # Velocidad en ese instante (m/s) [0 durante pausas]
    speed: float        # Rapidez en ese instante (m/s) [0 durante pausas]
    status: str         # Estado en que se registró


@dataclass
class ExperimentSummary:
    """Resumen integral y analítico al concluir la simulación."""
    x0: float
    x_final: float
    configured_velocity: float
    configured_speed: float
    t_eff: float
    t_total: float
    total_pause_duration: float
    pause_count: int
    displacement: float
    distance: float
    v_avg_eff: float      # Delta x / t_eff
    s_avg_eff: float      # d / t_eff
    v_avg_total: float    # Delta x / t_total
    s_avg_total: float    # d / t_total
    termination_reason: str
    is_mru_verified: bool
    explanation: str


class ExperimentControllerModel:
    """
    Controlador lógico del experimento físico.
    Administra la máquina de estados, el tiempo monotónico y el historial de muestras.
    """

    def __init__(self, track: TrackConfig, params: MRUParameters) -> None:
        self.track = track
        self.params = params
        self.physics = MRUPhysicsModel(track, params)

        self._status = ExperimentStatus.READY
        self._sample_counter = 0
        self._samples: List[MeasurementSample] = []

        # Tiempos de referencia monotónicos (usando time.perf_counter)
        self._wall_start_perf: Optional[float] = None
        self._segment_start_perf: Optional[float] = None
        self._accumulated_eff_time: float = 0.0
        self._frozen_total_time: float = 0.0

        # Registro de pausas
        self.pause_count: int = 0
        self.total_pause_duration: float = 0.0
        self._current_pause_start_perf: Optional[float] = None

        # Razón de finalización
        self.termination_reason: str = "Aún no finalizado"

        # Estado físico inicial (t=0)
        self._current_physics_state = self.physics.evaluate(0.0)
        self._record_sample(self._current_physics_state, t_total=0.0, vel_override=None)

    @property
    def status(self) -> ExperimentStatus:
        return self._status

    @property
    def samples(self) -> List[MeasurementSample]:
        return list(self._samples)

    @property
    def current_physics_state(self) -> PhysicalState:
        return self._current_physics_state

    def start(self) -> None:
        """Inicia el experimento desde el estado READY."""
        if self._status != ExperimentStatus.READY:
            raise RuntimeError(f"No se puede iniciar desde el estado {self._status.label}.")

        now = time.perf_counter()
        self._wall_start_perf = now
        self._segment_start_perf = now
        self._accumulated_eff_time = 0.0
        self._status = ExperimentStatus.RUNNING

        # Si la velocidad configurada es 0, no habrá desplazamiento
        if abs(self.params.velocity) < 1e-9:
            self.termination_reason = "El vehículo está en reposo (v = 0 m/s)."

        self._current_physics_state = self.physics.evaluate(0.0)
        self._record_sample(self._current_physics_state, t_total=0.0, vel_override=self.params.velocity)

    def pause(self) -> None:
        """Pausa el experimento, congelando el tiempo efectivo."""
        if self._status != ExperimentStatus.RUNNING:
            return  # Acción ignorada si no está en ejecución

        now = time.perf_counter()
        if self._segment_start_perf is not None:
            self._accumulated_eff_time += (now - self._segment_start_perf)
        self._segment_start_perf = None

        self._current_pause_start_perf = now
        self.pause_count += 1
        self._status = ExperimentStatus.PAUSED

        # Actualizar estado y registrar muestra de inicio de pausa (velocidad = 0)
        t_total = now - (self._wall_start_perf or now)
        self._current_physics_state = self.physics.evaluate(self._accumulated_eff_time)
        self._record_sample(self._current_physics_state, t_total=t_total, vel_override=0.0)

    def resume(self) -> None:
        """Reanuda el experimento desde la pausa sin reiniciar cronómetros."""
        if self._status != ExperimentStatus.PAUSED:
            return

        now = time.perf_counter()
        if self._current_pause_start_perf is not None:
            pause_dur = now - self._current_pause_start_perf
            self.total_pause_duration += pause_dur
            self._current_pause_start_perf = None

        self._segment_start_perf = now
        self._status = ExperimentStatus.RUNNING

        # Registrar muestra de reanudación (vuelve a la velocidad configurada)
        t_total = now - (self._wall_start_perf or now)
        self._current_physics_state = self.physics.evaluate(self._accumulated_eff_time)
        self._record_sample(self._current_physics_state, t_total=t_total, vel_override=self.params.velocity)

    def stop(self, reason: str = "Detenido por el usuario") -> None:
        """Finaliza definitivamente el experimento actual."""
        if self._status in (ExperimentStatus.FINISHED, ExperimentStatus.READY):
            if self._status == ExperimentStatus.READY:
                self._status = ExperimentStatus.FINISHED
                self.termination_reason = reason
            return

        now = time.perf_counter()
        t_total = now - (self._wall_start_perf or now)

        if self._status == ExperimentStatus.RUNNING and self._segment_start_perf is not None:
            self._accumulated_eff_time += (now - self._segment_start_perf)
            self._segment_start_perf = None
        elif self._status == ExperimentStatus.PAUSED and self._current_pause_start_perf is not None:
            self.total_pause_duration += (now - self._current_pause_start_perf)
            self._current_pause_start_perf = None

        self._frozen_total_time = t_total
        self._status = ExperimentStatus.FINISHED
        self.termination_reason = reason

        self._current_physics_state = self.physics.evaluate(self._accumulated_eff_time)
        self._record_sample(self._current_physics_state, t_total=t_total, vel_override=0.0)

    def update(self) -> PhysicalState:
        """
        Ciclo de actualización llamado periódicamente por el bucle de animación.
        Calcula tiempos actuales con precisión monotónica y actualiza la física.
        """
        if self._status == ExperimentStatus.RUNNING:
            now = time.perf_counter()
            current_t_eff = self._accumulated_eff_time + (now - (self._segment_start_perf or now))
            t_total = now - (self._wall_start_perf or now)

            # Evaluar física analítica en current_t_eff
            state = self.physics.evaluate(current_t_eff)
            self._current_physics_state = state

            # Verificar si alcanzó el límite de la pista
            if state.reached_boundary:
                reason = (
                    f"Alcanzó el límite superior x_max = {self.track.x_max:.2f} m."
                    if state.boundary_name == "x_max"
                    else f"Alcanzó el límite inferior x_min = {self.track.x_min:.2f} m."
                )
                self.stop(reason=reason)
            else:
                self._record_sample(state, t_total=t_total, vel_override=self.params.velocity)

        elif self._status == ExperimentStatus.PAUSED:
            now = time.perf_counter()
            t_total = now - (self._wall_start_perf or now)
            # En pausa, la física no avanza en t_eff, pero se mantiene la posición
            state = self._current_physics_state
            # Opcionalmente registrar muestra para mantener gráficas en tiempo global
            self._record_sample(state, t_total=t_total, vel_override=0.0)

        return self._current_physics_state

    def get_current_times(self) -> Tuple[float, float]:
        """Retorna (t_efectivo, t_total) en segundos."""
        if self._status == ExperimentStatus.READY:
            return 0.0, 0.0
        elif self._status == ExperimentStatus.RUNNING:
            now = time.perf_counter()
            t_eff = self._accumulated_eff_time + (now - (self._segment_start_perf or now))
            t_total = now - (self._wall_start_perf or now)
            return t_eff, t_total
        elif self._status == ExperimentStatus.PAUSED:
            now = time.perf_counter()
            t_total = now - (self._wall_start_perf or now)
            return self._accumulated_eff_time, t_total
        else:  # FINISHED
            return self._current_physics_state.t_eff, self._frozen_total_time

    def _record_sample(self, state: PhysicalState, t_total: float, vel_override: Optional[float] = None) -> None:
        """Registra una muestra asegurando espaciado temporal adecuado."""
        inst_vel = vel_override if vel_override is not None else state.velocity
        inst_spd = abs(inst_vel)

        # Evitar sobrecargar el registro si el intervalo entre muestras es extremadamente corto (< 10 ms),
        # salvo transiciones de estado importantes.
        if self._samples:
            last = self._samples[-1]
            if (t_total - last.t_total < 0.015) and (last.status == self._status.label):
                return

        sample = MeasurementSample(
            sample_id=self._sample_counter,
            t_total=round(t_total, 4),
            t_eff=round(state.t_eff, 4),
            position=round(state.position, 4),
            displacement=round(state.displacement, 4),
            distance=round(state.distance, 4),
            velocity=round(inst_vel, 4),
            speed=round(inst_spd, 4),
            status=self._status.label
        )
        self._samples.append(sample)
        self._sample_counter += 1

    def generate_summary(self) -> ExperimentSummary:
        """Genera el informe de resultados analíticos del experimento completado."""
        t_eff, t_total = self.get_current_times()
        state = self._current_physics_state

        disp = state.displacement
        dist = state.distance

        v_avg_eff = MRUPhysicsModel.calculate_average_velocity(disp, t_eff)
        s_avg_eff = MRUPhysicsModel.calculate_average_speed(dist, t_eff)

        v_avg_total = MRUPhysicsModel.calculate_average_velocity(disp, t_total)
        s_avg_total = MRUPhysicsModel.calculate_average_speed(dist, t_total)

        # Verificación del modelo de MRU durante los intervalos de movimiento
        # En MRU estricto: v_avg_eff debe coincidir con la velocidad configurada
        expected_v = self.params.velocity
        mru_verified = (abs(v_avg_eff - expected_v) < 1e-3) or (t_eff == 0 and abs(disp) < 1e-4)

        if self.pause_count == 0:
            explanation = (
                "El experimento se ejecutó de forma continua sin pausas. Por tanto, "
                "el tiempo efectivo coincide exactamente con el tiempo total del experimento "
                f"(t_eff = t_total = {t_eff:.2f} s). La velocidad media calculada "
                f"({v_avg_eff:.3f} m/s) es idéntica a la velocidad configurada ({expected_v:.3f} m/s), "
                "lo cual confirma el comportamiento característico del Movimiento Rectilíneo Uniforme."
            )
        else:
            explanation = (
                f"Se realizaron {self.pause_count} pausa(s) con una duración acumulada de "
                f"{self.total_pause_duration:.2f} s. "
                f"Durante los lapsos de movimiento efectivo ({t_eff:.2f} s), el vehículo mantuvo "
                f"la velocidad constante configurada de {expected_v:.3f} m/s (v_med_efectiva = {v_avg_eff:.3f} m/s). "
                f"Sin embargo, al considerar el tiempo global de pared ({t_total:.2f} s), la velocidad media global "
                f"desciende a {v_avg_total:.3f} m/s debido al tiempo en reposo de las pausas. "
                "Esto demuestra pedagógicamente la distinción crucial entre tiempo de movimiento y tiempo total de observación."
            )

        return ExperimentSummary(
            x0=self.params.x0,
            x_final=state.position,
            configured_velocity=expected_v,
            configured_speed=abs(expected_v),
            t_eff=t_eff,
            t_total=t_total,
            total_pause_duration=self.total_pause_duration,
            pause_count=self.pause_count,
            displacement=disp,
            distance=dist,
            v_avg_eff=v_avg_eff,
            s_avg_eff=s_avg_eff,
            v_avg_total=v_avg_total,
            s_avg_total=s_avg_total,
            termination_reason=self.termination_reason,
            is_mru_verified=mru_verified,
            explanation=explanation
        )
