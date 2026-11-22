"""
Módulo de Sistema de Unidades Físicas y Conversiones Cinemáticas.

Soporta conversiones multidimensionales para cinemática clásica:
- Longitud: metros (m), kilómetros (km), centímetros (cm), milímetros (mm).
- Tiempo: segundos (s), minutos (min), horas (h).
- Velocidad: metros por segundo (m/s), kilómetros por hora (km/h),
             centímetros por segundo (cm/s), kilómetros por segundo (km/s).
- Aceleración / Gravedad: metros por segundo al cuadrado (m/s²),
                          centímetros por segundo al cuadrado (cm/s²),
                          kilómetros por hora al cuadrado (km/h²).

Todos los cálculos internos se realizan en unidades del Sistema Internacional (SI).
"""

from enum import Enum
from typing import Dict, Tuple, Optional


class LengthUnit(str, Enum):
    """Unidades de longitud compatibles."""
    METER = "m"
    KILOMETER = "km"
    CENTIMETER = "cm"
    MILLIMETER = "mm"

    @property
    def label(self) -> str:
        names = {
            LengthUnit.METER: "Metro [m]",
            LengthUnit.KILOMETER: "Kilómetro [km]",
            LengthUnit.CENTIMETER: "Centímetro [cm]",
            LengthUnit.MILLIMETER: "Milímetro [mm]",
        }
        return names.get(self, self.value)


class TimeUnit(str, Enum):
    """Unidades de tiempo compatibles."""
    SECOND = "s"
    MINUTE = "min"
    HOUR = "h"

    @property
    def label(self) -> str:
        names = {
            TimeUnit.SECOND: "Segundo [s]",
            TimeUnit.MINUTE: "Minuto [min]",
            TimeUnit.HOUR: "Hora [h]",
        }
        return names.get(self, self.value)


class VelocityUnit(str, Enum):
    """Unidades de velocidad y rapidez compatibles."""
    M_S = "m/s"
    KM_H = "km/h"
    CM_S = "cm/s"
    KM_S = "km/s"

    @property
    def label(self) -> str:
        names = {
            VelocityUnit.M_S: "Metro por segundo [m/s]",
            VelocityUnit.KM_H: "Kilómetro por hora [km/h]",
            VelocityUnit.CM_S: "Centímetro por segundo [cm/s]",
            VelocityUnit.KM_S: "Kilómetro por segundo [km/s]",
        }
        return names.get(self, self.value)


class AccelerationUnit(str, Enum):
    """Unidades de aceleración y gravedad compatibles."""
    M_S2 = "m/s²"
    CM_S2 = "cm/s²"
    KM_H2 = "km/h²"

    @property
    def label(self) -> str:
        names = {
            AccelerationUnit.M_S2: "Metro por segundo al cuadrado [m/s²]",
            AccelerationUnit.CM_S2: "Centímetro por segundo al cuadrado [cm/s²]",
            AccelerationUnit.KM_H2: "Kilómetro por hora al cuadrado [km/h²]",
        }
        return names.get(self, self.value)


# Factores multiplicativos para convertir hacia el Sistema Internacional (SI)
# valor_SI = valor_original * factor
_LENGTH_TO_SI: Dict[str, float] = {
    LengthUnit.METER.value: 1.0,
    LengthUnit.KILOMETER.value: 1000.0,
    LengthUnit.CENTIMETER.value: 0.01,
    LengthUnit.MILLIMETER.value: 0.001,
    "m": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
}

_TIME_TO_SI: Dict[str, float] = {
    TimeUnit.SECOND.value: 1.0,
    TimeUnit.MINUTE.value: 60.0,
    TimeUnit.HOUR.value: 3600.0,
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
}

_VELOCITY_TO_SI: Dict[str, float] = {
    VelocityUnit.M_S.value: 1.0,
    VelocityUnit.KM_H.value: 1.0 / 3.6,          # 1 km/h = 1000 m / 3600 s = 1/3.6 m/s
    VelocityUnit.CM_S.value: 0.01,               # 1 cm/s = 0.01 m/s
    VelocityUnit.KM_S.value: 1000.0,             # 1 km/s = 1000 m/s
    "m/s": 1.0,
    "km/h": 1.0 / 3.6,
    "cm/s": 0.01,
    "km/s": 1000.0,
}

_ACCEL_TO_SI: Dict[str, float] = {
    AccelerationUnit.M_S2.value: 1.0,
    AccelerationUnit.CM_S2.value: 0.01,          # 1 cm/s² = 0.01 m/s²
    AccelerationUnit.KM_H2.value: 1000.0 / (3600.0 ** 2),  # 1 km/h² = 1/(12960) m/s²
    "m/s²": 1.0,
    "m/s^2": 1.0,
    "cm/s²": 0.01,
    "cm/s^2": 0.01,
    "km/h²": 1000.0 / (3600.0 ** 2),
    "km/h^2": 1000.0 / (3600.0 ** 2),
}


class UnitConverter:
    """Conversor bidireccional y explicativo de unidades cinemáticas."""

    @staticmethod
    def length_to_si(value: float, unit: str) -> float:
        """Convierte cualquier unidad de longitud soportada a metros [m]."""
        unit_clean = unit.strip()
        factor = _LENGTH_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de longitud no reconocida: '{unit}'. Soportadas: {list(_LENGTH_TO_SI.keys())}")
        return value * factor

    @staticmethod
    def length_from_si(value_m: float, target_unit: str) -> float:
        """Convierte metros [m] a la unidad de longitud destino."""
        unit_clean = target_unit.strip()
        factor = _LENGTH_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de longitud no reconocida: '{target_unit}'")
        return value_m / factor

    @staticmethod
    def time_to_si(value: float, unit: str) -> float:
        """Convierte cualquier unidad de tiempo soportada a segundos [s]."""
        unit_clean = unit.strip()
        factor = _TIME_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de tiempo no reconocida: '{unit}'. Soportadas: {list(_TIME_TO_SI.keys())}")
        return value * factor

    @staticmethod
    def time_from_si(value_s: float, target_unit: str) -> float:
        """Convierte segundos [s] a la unidad de tiempo destino."""
        unit_clean = target_unit.strip()
        factor = _TIME_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de tiempo no reconocida: '{target_unit}'")
        return value_s / factor

    @staticmethod
    def velocity_to_si(value: float, unit: str) -> float:
        """Convierte cualquier unidad de velocidad soportada a m/s."""
        unit_clean = unit.strip()
        factor = _VELOCITY_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de velocidad no reconocida: '{unit}'. Soportadas: {list(_VELOCITY_TO_SI.keys())}")
        return value * factor

    @staticmethod
    def velocity_from_si(value_m_s: float, target_unit: str) -> float:
        """Convierte m/s a la unidad de velocidad destino."""
        unit_clean = target_unit.strip()
        factor = _VELOCITY_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de velocidad no reconocida: '{target_unit}'")
        return value_m_s / factor

    @staticmethod
    def acceleration_to_si(value: float, unit: str) -> float:
        """Convierte cualquier unidad de aceleración soportada a m/s²."""
        unit_clean = unit.strip()
        factor = _ACCEL_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de aceleración no reconocida: '{unit}'. Soportadas: {list(_ACCEL_TO_SI.keys())}")
        return value * factor

    @staticmethod
    def acceleration_from_si(value_m_s2: float, target_unit: str) -> float:
        """Convierte m/s² a la unidad de aceleración destino."""
        unit_clean = target_unit.strip()
        factor = _ACCEL_TO_SI.get(unit_clean)
        if factor is None:
            raise ValueError(f"Unidad de aceleración no reconocida: '{target_unit}'")
        return value_m_s2 / factor

    @classmethod
    def to_si(cls, value: float, dimension: str, unit: str) -> float:
        """
        Conversión genérica a SI según la dimensión física:
        dimension: 'length', 'time', 'velocity', 'acceleration'.
        """
        dim = dimension.lower().strip()
        if dim in ("length", "longitud", "posicion", "distancia", "desplazamiento", "altura"):
            return cls.length_to_si(value, unit)
        elif dim in ("time", "tiempo", "duracion"):
            return cls.time_to_si(value, unit)
        elif dim in ("velocity", "velocidad", "rapidez"):
            return cls.velocity_to_si(value, unit)
        elif dim in ("acceleration", "aceleracion", "gravedad"):
            return cls.acceleration_to_si(value, unit)
        else:
            raise ValueError(f"Dimensión física no reconocida: '{dimension}'")

    @classmethod
    def from_si(cls, value_si: float, dimension: str, target_unit: str) -> float:
        """Conversión genérica desde SI hacia la unidad destino."""
        dim = dimension.lower().strip()
        if dim in ("length", "longitud", "posicion", "distancia", "desplazamiento", "altura"):
            return cls.length_from_si(value_si, target_unit)
        elif dim in ("time", "tiempo", "duracion"):
            return cls.time_from_si(value_si, target_unit)
        elif dim in ("velocity", "velocidad", "rapidez"):
            return cls.velocity_from_si(value_si, target_unit)
        elif dim in ("acceleration", "aceleracion", "gravedad"):
            return cls.acceleration_from_si(value_si, target_unit)
        else:
            raise ValueError(f"Dimensión física no reconocida: '{dimension}'")

    @classmethod
    def explain_conversion(cls, value: float, dimension: str, from_unit: str, to_unit: str) -> str:
        """
        Genera una explicación pedagógica paso a paso de la conversión de unidades
        con factores de conversión explícitos para el estudiante.
        """
        if from_unit == to_unit:
            return f"{value} {from_unit} (no requiere conversión)"

        dim = dimension.lower().strip()
        val_si = cls.to_si(value, dim, from_unit)
        val_target = cls.from_si(val_si, dim, to_unit)

        if dim in ("length", "longitud", "posicion", "distancia", "desplazamiento", "altura"):
            return f"{value} {from_unit} · ({_LENGTH_TO_SI[from_unit]} m / 1 {from_unit}) = {val_si:.6g} m" + (
                f" = {val_target:.6g} {to_unit}" if to_unit != "m" else ""
            )
        elif dim in ("velocity", "velocidad", "rapidez"):
            if from_unit == "km/h" and to_unit == "m/s":
                return f"{value} km/h · (1000 m / 1 km) · (1 h / 3600 s) = {value} / 3.6 = {val_si:.6g} m/s"
            elif from_unit == "m/s" and to_unit == "km/h":
                return f"{value} m/s · (1 km / 1000 m) · (3600 s / 1 h) = {value} · 3.6 = {val_target:.6g} km/h"
            else:
                return f"{value} {from_unit} = {val_si:.6g} m/s = {val_target:.6g} {to_unit}"
        elif dim in ("time", "tiempo", "duracion"):
            if from_unit == "min" and to_unit == "s":
                return f"{value} min · (60 s / 1 min) = {val_si:.6g} s"
            elif from_unit == "h" and to_unit == "s":
                return f"{value} h · (3600 s / 1 h) = {val_si:.6g} s"
            else:
                return f"{value} {from_unit} = {val_si:.6g} s"
        elif dim in ("acceleration", "aceleracion", "gravedad"):
            return f"{value} {from_unit} = {val_si:.6g} m/s²"

        return f"{value} {from_unit} = {val_target:.6g} {to_unit}"
