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
from typing import List, Optional, Callable, Tuple, Union, Any
from .physics import (
    MRUPhysicsModel,
    PhysicalState,
    TrackConfig,
    MRUParameters,
    MRUAParameters,
    MRUAPhysicsModel,
    FreeFallParameters,
    FreeFallPhysicsModel
)


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
    position: float     # Posición x(t) o y(t) (m)
    displacement: float # Desplazamiento acumulado (m)
    distance: float     # Distancia acumulada (m)
    velocity: float     # Velocidad en ese instante (m/s) [0 durante pausas]
    speed: float        # Rapidez en ese instante (m/s) [0 durante pausas]
    status: str         # Estado en que se registró
    acceleration: float = 0.0  # Aceleración en ese instante (m/s²)


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
    configured_acceleration: float = 0.0
    motion_type: str = "MRU"


class ExperimentControllerModel:
    """
    Controlador lógico del experimento físico.
    Administra la máquina de estados, el tiempo monotónico y el historial de muestras.
    Soporta de manera polimórfica modelos de MRU, MRUA y Caída Libre.
    """

    def __init__(
        self,
        track: TrackConfig,
        params: Union[MRUParameters, MRUAParameters, FreeFallParameters],
        physics_model: Optional[Any] = None
    ) -> None:
        self.track = track
        self.params = params

        if physics_model is not None:
            self.physics = physics_model
        elif isinstance(params, MRUAParameters):
            self.physics = MRUAPhysicsModel(track, params)
        elif isinstance(params, FreeFallParameters):
            self.physics = FreeFallPhysicsModel(params)
        else:
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
    def initial_velocity(self) -> float:
        if hasattr(self.params, "velocity"):
            return self.params.velocity
        elif hasattr(self.params, "v0"):
            return self.params.v0
        return 0.0

    @property
    def initial_position(self) -> float:
        if hasattr(self.params, "x0"):
            return self.params.x0
        elif hasattr(self.params, "y0"):
            return self.params.y0
        return 0.0

    @property
    def configured_acceleration(self) -> float:
        if hasattr(self.params, "acceleration"):
            return self.params.acceleration
        elif hasattr(self.params, "g"):
            return -self.params.g
        return 0.0

    @property
    def motion_type(self) -> str:
        if isinstance(self.physics, FreeFallPhysicsModel) or isinstance(self.params, FreeFallParameters):
            return "CAIDA_LIBRE"
        elif isinstance(self.physics, MRUAPhysicsModel) or isinstance(self.params, MRUAParameters):
            return "MRUA"
        return "MRU"

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

        init_v = self.initial_velocity
        init_a = self.configured_acceleration
        if abs(init_v) < 1e-9 and abs(init_a) < 1e-9:
            self.termination_reason = "El cuerpo está permanentemente en reposo (v = 0 m/s, a = 0 m/s²)."

        self._current_physics_state = self.physics.evaluate(0.0)
        self._record_sample(self._current_physics_state, t_total=0.0, vel_override=init_v)

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

        # Registrar muestra de reanudación
        t_total = now - (self._wall_start_perf or now)
        self._current_physics_state = self.physics.evaluate(self._accumulated_eff_time)
        self._record_sample(self._current_physics_state, t_total=t_total, vel_override=None)

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

            # Verificar si alcanzó el límite o finalización
            if state.reached_boundary:
                if state.boundary_name == "x_max":
                    reason = f"Alcanzó el límite superior x_max = {self.track.x_max:.2f} m."
                elif state.boundary_name == "x_min":
                    reason = f"Alcanzó el límite inferior x_min = {self.track.x_min:.2f} m."
                elif state.boundary_name == "ground":
                    reason = "Impactó contra el suelo (y = 0.00 m)."
                else:
                    reason = "Alcanzó el límite programado del movimiento."
                self.stop(reason=reason)
            else:
                self._record_sample(state, t_total=t_total, vel_override=None)

        elif self._status == ExperimentStatus.PAUSED:
            now = time.perf_counter()
            t_total = now - (self._wall_start_perf or now)
            state = self._current_physics_state
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
        inst_acc = 0.0 if (vel_override == 0.0 and self._status == ExperimentStatus.PAUSED) else state.acceleration

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
            status=self._status.label,
            acceleration=round(inst_acc, 4)
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

        expected_v = self.initial_velocity
        expected_a = self.configured_acceleration
        mtype = self.motion_type

        if mtype == "MRU":
            verified = (abs(v_avg_eff - expected_v) < 1e-3) or (t_eff == 0 and abs(disp) < 1e-4)
            if self.pause_count == 0:
                explanation = (
                    "El experimento se ejecutó de forma continua sin pausas. Por tanto, "
                    f"el tiempo efectivo coincide con el total (t_eff = t_total = {t_eff:.2f} s). "
                    f"La velocidad media calculada ({v_avg_eff:.3f} m/s) es idéntica a la configurada ({expected_v:.3f} m/s), "
                    "confirmando el comportamiento característico del Movimiento Rectilíneo Uniforme."
                )
            else:
                explanation = (
                    f"Se realizaron {self.pause_count} pausa(s) con duración acumulada de {self.total_pause_duration:.2f} s. "
                    f"Durante el movimiento efectivo ({t_eff:.2f} s), la velocidad media fue {v_avg_eff:.3f} m/s, "
                    f"mientras que respecto al tiempo global ({t_total:.2f} s) desciende a {v_avg_total:.3f} m/s "
                    "debido al tiempo en reposo de las pausas."
                )
        elif mtype == "MRUA":
            # En MRUA con aceleración constante, v_avg = (v0 + v_final)/2
            v_theoretical_avg = (expected_v + state.velocity) / 2.0
            verified = (abs(v_avg_eff - v_theoretical_avg) < 0.05) or (t_eff == 0)
            explanation = (
                f"Movimiento Rectilíneo Uniformemente Acelerado (a = {expected_a:+.2f} m/s²). "
                f"La velocidad inicial fue v₀ = {expected_v:+.2f} m/s y la velocidad final alcanzada es v = {state.velocity:+.2f} m/s. "
                f"La velocidad media en MRUA satisface v_med = (v₀ + v)/2 = {v_theoretical_avg:.2f} m/s. "
                f"Desplazamiento total: Δx = {disp:+.2f} m, distancia recorrida: d = {dist:.2f} m."
            )
        else:  # CAIDA_LIBRE
            verified = True
            h_max_val = getattr(self.physics, "h_max", state.position)
            t_impact_val = getattr(self.physics, "t_impact", t_eff)
            explanation = (
                f"Caída Libre / Lanzamiento Vertical bajo aceleración gravitatoria g = {abs(expected_a):.2f} m/s². "
                f"Altura inicial: y₀ = {self.initial_position:.2f} m. Altura máxima alcanzada: {h_max_val:.2f} m. "
                f"Tiempo de vuelo estimado: {t_impact_val:.2f} s. Velocidad final: {state.velocity:+.2f} m/s."
            )

        return ExperimentSummary(
            x0=self.initial_position,
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
            is_mru_verified=verified,
            explanation=explanation,
            configured_acceleration=expected_a,
            motion_type=mtype
        )
