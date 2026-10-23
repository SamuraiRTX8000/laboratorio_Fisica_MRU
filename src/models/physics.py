"""
Módulo de Modelo Físico para Movimiento Rectilíneo Uniforme (MRU).

Este módulo implementa las leyes de la cinemática clásica para un cuerpo puntual
en movimiento unidimensional con aceleración nula (a = 0).

Ecuación fundamental del MRU:
    x(t) = x_0 + v * t_eff

Donde:
    - x(t): Posición instantánea en metros (m).
    - x_0: Posición inicial en el sistema de referencia (m).
    - v: Velocidad constante (magnitud vectorial unidimensional con signo) en m/s.
    - t_eff: Tiempo efectivo de movimiento (sin pausas) en segundos (s).

Magnitudes derivadas:
    - Desplazamiento: Delta x = x(t) - x_0 (vector unidimensional, m)
    - Distancia recorrida: d = |v| * t_eff = |Delta x| (escalar, m)
    - Rapidez instantánea: s = |v| (escalar, m/s)
    - Aceleración: a = 0 m/s^2 (constante)
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class TrackConfig:
    """Configuración geométrica y límites de la pista sobre la recta numérica."""
    x_min: float = -50.0  # Límite inferior en metros
    x_max: float = 50.0   # Límite superior en metros

    def __post_init__(self) -> None:
        if self.x_min >= self.x_max:
            raise ValueError(
                f"El límite inferior (x_min={self.x_min} m) debe ser estrictamente menor "
                f"que el límite superior (x_max={self.x_max} m)."
            )

    @property
    def total_length(self) -> float:
        """Longitud total de la pista en metros."""
        return self.x_max - self.x_min

    def contains(self, x: float, tolerance: float = 1e-7) -> bool:
        """Verifica si una coordenada está dentro de los límites de la pista."""
        return (self.x_min - tolerance) <= x <= (self.x_max + tolerance)


@dataclass(frozen=True)
class MRUParameters:
    """Parámetros cinemáticos iniciales para la simulación de MRU."""
    x0: float          # Posición inicial en metros
    velocity: float    # Velocidad constante en m/s (con signo según el sentido)

    @property
    def speed(self) -> float:
        """Rapidez (magnitud escalar de la velocidad, siempre >= 0)."""
        return abs(self.velocity)

    @property
    def direction_sign(self) -> int:
        """Signo del sentido de movimiento (+1 derecha, -1 izquierda, 0 reposo)."""
        if self.velocity > 0:
            return 1
        elif self.velocity < 0:
            return -1
        return 0


@dataclass(frozen=True)
class PhysicalState:
    """Estado instantáneo calculado del cuerpo según las ecuaciones cinemáticas."""
    t_eff: float            # Tiempo efectivo de movimiento (s)
    position: float         # Posición actual x(t) (m)
    displacement: float     # Desplazamiento Delta x = x(t) - x0 (m)
    distance: float         # Distancia total recorrida d (m)
    velocity: float         # Velocidad vectorial instantánea (m/s)
    speed: float            # Rapidez instantánea (m/s)
    reached_boundary: bool  # Indica si alcanzó el final de la pista
    boundary_name: Optional[str] = None  # "x_max", "x_min" o None


class MRUPhysicsModel:
    """
    Modelo matemático y analítico de MRU.
    
    Aplica rigurosamente la solución analítica x(t) = x0 + v * t en lugar de
    métodos numéricos de acumulación paso a paso (Euler), eliminando el error
    por discretización temporal.
    """

    def __init__(self, track: TrackConfig, params: MRUParameters) -> None:
        self.track = track
        self.params = params
        self.validate_configuration()
        self.max_effective_time = self._calculate_time_to_boundary()

    def validate_configuration(self) -> None:
        """
        Valida que los parámetros iniciales sean físicamente consistentes
        dentro del escenario configurado.
        """
        x0 = self.params.x0
        v = self.params.velocity

        if not self.track.contains(x0):
            raise ValueError(
                f"La posición inicial x0={x0:.2f} m se encuentra fuera de los límites "
                f"de la pista [{self.track.x_min:.2f} m, {self.track.x_max:.2f} m]."
            )

        # Si ya está en un extremo y la velocidad apunta hacia afuera de la pista
        if v > 0 and abs(x0 - self.track.x_max) < 1e-6:
            raise ValueError(
                f"El vehículo ya está en el límite superior x_max={self.track.x_max:.2f} m "
                f"y no puede desplazarse en sentido positivo (v={v:.2f} m/s)."
            )
        if v < 0 and abs(x0 - self.track.x_min) < 1e-6:
            raise ValueError(
                f"El vehículo ya está en el límite inferior x_min={self.track.x_min:.2f} m "
                f"y no puede desplazarse en sentido negativo (v={v:.2f} m/s)."
            )

    def _calculate_time_to_boundary(self) -> float:
        """
        Calcula de forma exacta el tiempo en segundos que tardará el vehículo
        en alcanzar el límite de la pista en el sentido de su movimiento.
        Si la velocidad es 0, retorna infinito.
        """
        v = self.params.velocity
        x0 = self.params.x0

        if v > 0:
            return (self.track.x_max - x0) / v
        elif v < 0:
            return (self.track.x_min - x0) / v
        else:
            return float('inf')

    def evaluate(self, t_eff: float) -> PhysicalState:
        """
        Evalúa el estado físico en el tiempo efectivo t_eff (segundos).
        
        Garantiza que el vehículo no traspase los límites de la pista:
        si t_eff supera el tiempo de colisión/límite, se satura exactamente
        en el límite físico de la pista.
        """
        if t_eff < 0:
            t_eff = 0.0

        v = self.params.velocity
        x0 = self.params.x0

        reached_boundary = False
        boundary_name = None

        if t_eff >= self.max_effective_time and self.max_effective_time != float('inf'):
            # El tiempo solicitado iguala o supera el límite de la pista
            t_eff_actual = self.max_effective_time
            reached_boundary = True
            if v > 0:
                pos = self.track.x_max
                boundary_name = "x_max"
            else:
                pos = self.track.x_min
                boundary_name = "x_min"
            vel_instant = 0.0
            spd_instant = 0.0
        else:
            t_eff_actual = t_eff
            pos = x0 + v * t_eff_actual
            vel_instant = v
            spd_instant = abs(v)

        disp = pos - x0
        dist = abs(v) * t_eff_actual

        return PhysicalState(
            t_eff=t_eff_actual,
            position=pos,
            displacement=disp,
            distance=dist,
            velocity=vel_instant,
            speed=spd_instant,
            reached_boundary=reached_boundary,
            boundary_name=boundary_name
        )

    @staticmethod
    def calculate_average_velocity(displacement: float, elapsed_time: float) -> float:
        """
        Calcula la velocidad media:
            v_med = Delta x / Delta t
        Donde Delta x es el desplazamiento vectorial y Delta t es el intervalo de tiempo.
        """
        if elapsed_time <= 0:
            return 0.0
        return displacement / elapsed_time

    @staticmethod
    def calculate_average_speed(distance: float, elapsed_time: float) -> float:
        """
        Calcula la rapidez media:
            s_med = d / Delta t
        Donde d es la distancia recorrida (escalar) y Delta t es el intervalo de tiempo.
        """
        if elapsed_time <= 0:
            return 0.0
        return distance / elapsed_time
