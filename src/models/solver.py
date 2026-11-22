"""
Módulo del Motor Algebraico y Solucionador Paso a Paso de Cinemática (MRUA y Caída Libre).

Diseñado específicamente para la enseñanza universitaria de Física:
- Analiza las variables provistas por el estudiante.
- Detecta si los datos son suficientes o insuficientes (sin inventar ni asumir valores).
- Evalúa el catálogo de ecuaciones cinemáticas fundamentales y sus variantes algebraicas:
    1. v = v₀ + a·t
    2. Δx = v₀·t + ½·a·t²  /  x = x₀ + v₀·t + ½·a·t²
    3. v² = v₀² + 2·a·Δx (Torricelli)
    4. Δx = ((v₀ + v) / 2) · t (Velocidad media)
    5. Ecuaciones verticales de caída libre y lanzamiento vertical bajo gravedad g.
- Genera soluciones didácticas detalladas con los 10 pasos requeridos:
    1. Datos conocidos con unidades originales y conversión a SI.
    2. Variable desconocida (incógnita).
    3. Ecuación seleccionada.
    4. Justificación física y matemática.
    5. Despeje algebraico paso a paso.
    6. Sustitución numérica.
    7. Operaciones intermedias paso a paso.
    8. Resultado final con unidad en SI y unidad solicitada.
    9. Interpretación física del resultado.
    10. Análisis de multiplicidad de soluciones (raíces cuadráticas y signos de ±√).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math
from .units import UnitConverter


@dataclass
class VariableSpec:
    """Especificación de una variable cinemática en un problema."""
    code: str              # Código interno: "v0", "v", "a", "t", "x0", "x", "dx", "d", "y0", "y", "dy", "g", "h_max", etc.
    symbol: str            # Símbolo estándar: "v₀", "v", "a", "t", "Δx", etc.
    name: str              # Nombre descriptivo: "Velocidad inicial", etc.
    dimension: str         # "velocity", "acceleration", "time", "length"
    default_unit: str      # "m/s", "m/s²", "s", "m"


# Catálogo completo de variables cinemáticas
VARIABLES_CATALOG: Dict[str, VariableSpec] = {
    # MRUA Horizontal
    "x0": VariableSpec("x0", "x₀", "Posición inicial", "length", "m"),
    "x": VariableSpec("x", "x", "Posición final", "length", "m"),
    "dx": VariableSpec("dx", "Δx", "Desplazamiento horizontal", "length", "m"),
    "d": VariableSpec("d", "d", "Distancia recorrida", "length", "m"),
    "v0": VariableSpec("v0", "v₀", "Velocidad inicial", "velocity", "m/s"),
    "v": VariableSpec("v", "v", "Velocidad final", "velocity", "m/s"),
    "a": VariableSpec("a", "a", "Aceleración constante", "acceleration", "m/s²"),
    "t": VariableSpec("t", "t", "Tiempo transcurrido", "time", "s"),

    # Caída Libre / Lanzamiento Vertical
    "y0": VariableSpec("y0", "y₀", "Altura / Posición inicial", "length", "m"),
    "y": VariableSpec("y", "y", "Altura / Posición final", "length", "m"),
    "dy": VariableSpec("dy", "Δy", "Desplazamiento vertical", "length", "m"),
    "g": VariableSpec("g", "g", "Aceleración gravitatoria", "acceleration", "m/s²"),
    "h_max": VariableSpec("h_max", "h_máx", "Altura máxima alcanzada", "length", "m"),
    "t_subida": VariableSpec("t_subida", "t_subida", "Tiempo de subida", "time", "s"),
    "t_vuelo": VariableSpec("t_vuelo", "t_vuelo", "Tiempo de vuelo hasta y₀", "time", "s"),
    "t_impacto": VariableSpec("t_impacto", "t_impacto", "Tiempo de impacto contra el suelo", "time", "s"),
    "v_impacto": VariableSpec("v_impacto", "v_impacto", "Velocidad de impacto", "velocity", "m/s"),
}


@dataclass
class InputVariable:
    """Variable introducida por el usuario con su unidad."""
    code: str
    value: float
    unit: str
    si_value: float = field(init=False)
    conversion_note: str = field(init=False)

    def __post_init__(self) -> None:
        spec = VARIABLES_CATALOG.get(self.code)
        dim = spec.dimension if spec else "length"
        self.si_value = UnitConverter.to_si(self.value, dim, self.unit)
        self.conversion_note = UnitConverter.explain_conversion(
            self.value, dim, self.unit, spec.default_unit if spec else "m"
        )


@dataclass
class StepByStepSolution:
    """Resultado estructurado de la resolución pedagógica de un problema físico."""
    is_solvable: bool
    scenario: str                          # "MRUA_HORIZONTAL" o "CAIDA_LIBRE"
    target_code: str                       # Variable a despejar
    target_spec: VariableSpec
    target_unit: str
    known_inputs: List[InputVariable]

    # Pasos de la resolución
    equation_name: str = ""
    equation_formula: str = ""
    justification: str = ""
    derivation_steps: List[str] = field(default_factory=list)
    substitution_text: str = ""
    calculation_steps: List[str] = field(default_factory=list)

    # Resultados numéricos
    final_value_si: Optional[float] = None
    final_unit_si: str = ""
    final_value_target: Optional[float] = None
    physical_interpretation: str = ""
    multiple_solutions_note: Optional[str] = None
    diagnostic_error: Optional[str] = None


class KinematicsSolver:
    """
    Motor de resolución de cinemática clásica.
    Identifica ecuaciones compatibles, despeja algebraicamente y formula la solución paso a paso.
    """

    @classmethod
    def solve(
        cls,
        scenario: str,  # "MRUA" o "CAIDA_LIBRE"
        known_inputs: Dict[str, Tuple[float, str]],  # {"v0": (10.0, "m/s"), ...}
        target_code: str,
        target_unit: Optional[str] = None
    ) -> StepByStepSolution:
        """
        Resuelve un problema cinemático a partir de datos conocidos.
        scenario: 'MRUA' o 'CAIDA_LIBRE'.
        known_inputs: dict de {codigo: (valor, unidad)}.
        target_code: codigo de la incógnita a calcular.
        target_unit: unidad opcional para el resultado (si no se indica, usa la estándar del SI).
        """
        target_spec = VARIABLES_CATALOG.get(target_code)
        if not target_spec:
            raise ValueError(f"Variable incógnita desconocida: '{target_code}'")

        if not target_unit:
            target_unit = target_spec.default_unit

        # Parsear variables de entrada
        parsed_inputs: List[InputVariable] = []
        si_dict: Dict[str, float] = {}

        for code, (val, unit) in known_inputs.items():
            if code == target_code:
                continue  # No se puede tener la incógnita en las entradas
            inp = InputVariable(code=code, value=val, unit=unit)
            parsed_inputs.append(inp)
            si_dict[code] = inp.si_value

        # Inferir relaciones geométricas previas (ej: dx = x - x0 o dy = y - y0)
        cls._infer_derived_knowns(scenario, si_dict)

        # Buscar estrategia de resolución
        if scenario == "CAIDA_LIBRE":
            # Si no se especificó g, por defecto se considera 9.81 m/s²
            if "g" not in si_dict:
                si_dict["g"] = 9.81
                parsed_inputs.append(InputVariable("g", 9.81, "m/s²"))

            solution = cls._solve_free_fall(si_dict, parsed_inputs, target_code, target_spec, target_unit)
        else:
            solution = cls._solve_mrua(si_dict, parsed_inputs, target_code, target_spec, target_unit)

        return solution

    @staticmethod
    def _infer_derived_knowns(scenario: str, si_dict: Dict[str, float]) -> None:
        """Infiere magnitudes suplementarias directas (como desplazamiento a partir de posiciones)."""
        if scenario == "MRUA":
            if "x" in si_dict and "x0" in si_dict and "dx" not in si_dict:
                si_dict["dx"] = si_dict["x"] - si_dict["x0"]
            elif "dx" in si_dict and "x0" in si_dict and "x" not in si_dict:
                si_dict["x"] = si_dict["x0"] + si_dict["dx"]
            elif "x" in si_dict and "dx" in si_dict and "x0" not in si_dict:
                si_dict["x0"] = si_dict["x"] - si_dict["dx"]
        elif scenario == "CAIDA_LIBRE":
            if "y" in si_dict and "y0" in si_dict and "dy" not in si_dict:
                si_dict["dy"] = si_dict["y"] - si_dict["y0"]
            elif "dy" in si_dict and "y0" in si_dict and "y" not in si_dict:
                si_dict["y"] = si_dict["y0"] + si_dict["dy"]
            elif "y" in si_dict and "dy" in si_dict and "y0" not in si_dict:
                si_dict["y0"] = si_dict["y"] - si_dict["dy"]

    # =========================================================================
    # RESOLUTOR MRUA HORIZONTAL
    # =========================================================================

    @staticmethod
    def _fmt(val: float, with_sign: bool = False) -> str:
        """Formatea un número de forma limpia para presentaciones matemáticas."""
        if abs(val) < 1e-12:
            return "0"
        if with_sign and val > 0:
            return f"+{val:.4g}"
        return f"{val:.4g}"

    @classmethod
    def _solve_mrua(
        cls,
        si: Dict[str, float],
        inputs: List[InputVariable],
        target: str,
        spec: VariableSpec,
        target_unit: str
    ) -> StepByStepSolution:
        """Busca una ecuación de MRUA capaz de calcular la incógnita 'target'."""

        # ---------------------------------------------------------------------
        # CASO 1: Calcular Velocidad Final (v)
        # ---------------------------------------------------------------------
        if target == "v":
            # A) Con v0, a, t -> v = v0 + a*t
            if "v0" in si and "a" in si and "t" in si:
                v0, a, t = si["v0"], si["a"], si["t"]
                val = v0 + (a * t)
                interp = cls._interpret_velocity(val, v0, a)
                f_v0 = cls._fmt(v0)
                f_a = cls._fmt(a)
                f_t = cls._fmt(t)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Ecuación de velocidad en función del tiempo",
                    formula="v = v₀ + a · t",
                    justification="Se conocen la velocidad inicial (v₀), la aceleración (a) y el tiempo transcurrido (t).",
                    derivation=["La incógnita 'v' ya se encuentra despejada en la forma estándar."],
                    substitution=f"v = ({f_v0} m/s) + [({f_a} m/s²) · ({f_t} s)]",
                    calc_steps=[
                        f"Multiplicación de la aceleración por el tiempo: a · t = ({f_a}) · ({f_t}) = {a*t:.4g} m/s",
                        f"Suma con la velocidad inicial: v = {f_v0} + ({a*t:.4g}) = {val:.4g} m/s"
                    ],
                    final_val_si=val, interp=interp
                )

            # B) Con v0, a, dx (Torricelli) -> v = ±√(v0² + 2*a*dx)
            if "v0" in si and "a" in si and "dx" in si:
                v0, a, dx = si["v0"], si["a"], si["dx"]
                radicand = (v0 ** 2) + (2.0 * a * dx)
                if radicand < 0:
                    return cls._unsolvable(
                        "MRUA", target, spec, target_unit, inputs,
                        f"Inconsistencia física: El radicando en la ecuación de Torricelli es negativo "
                        f"(v₀² + 2aΔx = {v0:.4g}² + 2({a:.4g})({dx:.4g}) = {radicand:.4g} < 0). "
                        "Esto indica que con la desaceleración dada, el móvil no puede alcanzar ese desplazamiento."
                    )
                mag = radicand ** 0.5
                # Sentido de v: si a*dx > 0 y v0 >= 0, es +; si invirtió o va a la izquierda, explicar ambos signos
                val = mag if (v0 >= 0 and not (a < 0 and dx < (-(v0**2)/(2*a)))) else -mag
                notes = (
                    f"La raíz cuadrada produce dos soluciones matemáticas: v = ±{mag:.4g} m/s. "
                    "El signo positivo (+) corresponde al movimiento hacia la derecha; "
                    "el signo negativo (-) corresponde al retorno hacia la izquierda tras detenerse e invertir sentido."
                )
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Ecuación de Torricelli (independiente del tiempo)",
                    formula="v² = v₀² + 2 · a · Δx   ⇒   v = ±√(v₀² + 2 · a · Δx)",
                    justification="Se conocen v₀, a y Δx, y no se requiere conocer el tiempo para hallar la velocidad.",
                    derivation=[
                        "1. Partimos de: v² = v₀² + 2 · a · Δx",
                        "2. Aplicamos raíz cuadrada a ambos miembros: v = ±√(v₀² + 2 · a · Δx)"
                    ],
                    substitution=f"v = ±√[({v0:+.4g})² + 2 · ({a:+.4g}) · ({dx:+.4g})]",
                    calc_steps=[
                        f"Término cuadrático: v₀² = ({v0:+.4g})² = {v0**2:.4g} (m/s)²",
                        f"Término de aceleración: 2 · a · Δx = 2 · ({a:+.4g}) · ({dx:+.4g}) = {2*a*dx:+.4g} (m/s)²",
                        f"Suma bajo el radical: {v0**2:.4g} + ({2*a*dx:+.4g}) = {radicand:.4g} (m/s)²",
                        f"Extracción de la raíz: √({radicand:.4g}) = {mag:.4g} m/s"
                    ],
                    final_val_si=val, interp=cls._interpret_velocity(val, v0, a), mult_note=notes
                )

            # C) Con dx, t, v0 (Velocidad media) -> Δx = ((v0 + v)/2)*t -> v = (2*dx/t) - v0
            if "dx" in si and "t" in si and "v0" in si:
                dx, t, v0 = si["dx"], si["t"], si["v0"]
                if t <= 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "El tiempo t debe ser positivo.")
                val = ((2.0 * dx) / t) - v0
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Ecuación del desplazamiento mediante velocidad media",
                    formula="Δx = ½ · (v₀ + v) · t   ⇒   v = (2 · Δx / t) - v₀",
                    justification="Se conocen el desplazamiento (Δx), la velocidad inicial (v₀) y el tiempo (t) con aceleración constante.",
                    derivation=[
                        "1. Δx = ½ · (v₀ + v) · t",
                        "2. Multiplicando ambos lados por 2: 2 · Δx = (v₀ + v) · t",
                        "3. Dividiendo entre t: (2 · Δx) / t = v₀ + v",
                        "4. Restando v₀: v = (2 · Δx / t) - v₀"
                    ],
                    substitution=f"v = [2 · ({dx:+.4g} m) / ({t:.4g} s)] - ({v0:+.4g} m/s)",
                    calc_steps=[
                        f"Doble del desplazamiento sobre tiempo: (2 · {dx:+.4g}) / {t:.4g} = {2*dx/t:+.4g} m/s",
                        f"Resta de la velocidad inicial: {2*dx/t:+.4g} - ({v0:+.4g}) = {val:+.4g} m/s"
                    ],
                    final_val_si=val, interp=cls._interpret_velocity(val, v0, None)
                )

        # ---------------------------------------------------------------------
        # CASO 2: Calcular Velocidad Inicial (v0)
        # ---------------------------------------------------------------------
        if target == "v0":
            # A) Con v, a, t -> v0 = v - a*t
            if "v" in si and "a" in si and "t" in si:
                v, a, t = si["v"], si["a"], si["t"]
                val = v - (a * t)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de v₀ en función del tiempo y aceleración",
                    formula="v = v₀ + a · t   ⇒   v₀ = v - a · t",
                    justification="Se conocen la velocidad final (v), la aceleración (a) y el tiempo (t).",
                    derivation=[
                        "1. v = v₀ + a · t",
                        "2. Restamos el término (a · t) en ambos lados: v₀ = v - a · t"
                    ],
                    substitution=f"v₀ = ({v:+.4g} m/s) - [({a:+.4g} m/s²) · ({t:.4g} s)]",
                    calc_steps=[
                        f"a · t = ({a:+.4g}) · ({t:.4g}) = {a*t:+.4g} m/s",
                        f"v₀ = {v:+.4g} - ({a*t:+.4g}) = {val:+.4g} m/s"
                    ],
                    final_val_si=val, interp=f"El cuerpo inició su movimiento con una velocidad de {val:+.4g} m/s."
                )

            # B) Con dx, a, t -> dx = v0*t + 0.5*a*t² -> v0 = (dx - 0.5*a*t²)/t
            if "dx" in si and "a" in si and "t" in si:
                dx, a, t = si["dx"], si["a"], si["t"]
                if t <= 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "El tiempo t debe ser estrictamente positivo.")
                val = (dx - (0.5 * a * (t ** 2))) / t
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de v₀ a partir del desplazamiento y tiempo",
                    formula="Δx = v₀ · t + ½ · a · t²   ⇒   v₀ = (Δx - ½ · a · t²) / t",
                    justification="Se conocen el desplazamiento Δx, la aceleración a y el tiempo transcurrido t.",
                    derivation=[
                        "1. Δx = v₀ · t + ½ · a · t²",
                        "2. Restamos ½ · a · t²: Δx - ½ · a · t² = v₀ · t",
                        "3. Dividimos entre t: v₀ = (Δx - ½ · a · t²) / t"
                    ],
                    substitution=f"v₀ = [({dx:+.4g}) - ½ · ({a:+.4g}) · ({t:.4g})²] / ({t:.4g})",
                    calc_steps=[
                        f"Término cuadrático de aceleración: ½ · a · t² = 0.5 · ({a:+.4g}) · ({t**2:.4g}) = {0.5*a*(t**2):+.4g} m",
                        f"Diferencia de desplazamiento: {dx:+.4g} - ({0.5*a*(t**2):+.4g}) = {dx - (0.5*a*(t**2)):+.4g} m",
                        f"División entre tiempo: {dx - (0.5*a*(t**2)):+.4g} / {t:.4g} = {val:+.4g} m/s"
                    ],
                    final_val_si=val, interp=f"La velocidad inicial requerida para ese trayecto es {val:+.4g} m/s."
                )

            # C) Con v, a, dx (Torricelli) -> v0 = ±√(v² - 2*a*dx)
            if "v" in si and "a" in si and "dx" in si:
                v, a, dx = si["v"], si["a"], si["dx"]
                radicand = (v ** 2) - (2.0 * a * dx)
                if radicand < 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, f"Radicando negativo ({radicand:.4g} < 0) en Torricelli.")
                mag = radicand ** 0.5
                val = mag  # default positivo
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de v₀ mediante Torricelli",
                    formula="v² = v₀² + 2 · a · Δx   ⇒   v₀ = ±√(v² - 2 · a · Δx)",
                    justification="Se conocen v, a y Δx sin depender del tiempo.",
                    derivation=[
                        "1. v² = v₀² + 2 · a · Δx",
                        "2. v₀² = v² - 2 · a · Δx",
                        "3. v₀ = ±√(v² - 2 · a · Δx)"
                    ],
                    substitution=f"v₀ = ±√[({v:+.4g})² - 2 · ({a:+.4g}) · ({dx:+.4g})]",
                    calc_steps=[
                        f"v² = {v**2:.4g}",
                        f"2 · a · Δx = {2*a*dx:+.4g}",
                        f"v² - 2aΔx = {radicand:.4g}",
                        f"√({radicand:.4g}) = {mag:.4g} m/s"
                    ],
                    final_val_si=val, interp=f"La rapidez inicial con que comenzó el movimiento fue de {mag:.4g} m/s."
                )

        # ---------------------------------------------------------------------
        # CASO 3: Calcular Aceleración (a)
        # ---------------------------------------------------------------------
        if target == "a":
            # A) Con v, v0, t -> a = (v - v0)/t
            if "v" in si and "v0" in si and "t" in si:
                v, v0, t = si["v"], si["v0"], si["t"]
                if t <= 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "El tiempo t debe ser positivo.")
                val = (v - v0) / t
                interp = cls._interpret_acceleration(val, v0, v)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Definición de aceleración en función del cambio de velocidad",
                    formula="a = (v - v₀) / t",
                    justification="Se conocen la velocidad inicial v₀, la velocidad final v y el tiempo transcurrido t.",
                    derivation=[
                        "1. Partimos de la ecuación horaria: v = v₀ + a · t",
                        "2. Restamos v₀ a ambos miembros: v - v₀ = a · t",
                        "3. Dividimos entre t: a = (v - v₀) / t"
                    ],
                    substitution=f"a = [({v:+.4g} m/s) - ({v0:+.4g} m/s)] / ({t:.4g} s)",
                    calc_steps=[
                        f"Variación de velocidad: Δv = v - v₀ = ({v:+.4g}) - ({v0:+.4g}) = {v - v0:+.4g} m/s",
                        f"Cociente con el tiempo: ({v - v0:+.4g}) / {t:.4g} = {val:+.4g} m/s²"
                    ],
                    final_val_si=val, interp=interp
                )

            # B) Con v, v0, dx (Torricelli) -> a = (v² - v0²)/(2*dx)
            if "v" in si and "v0" in si and "dx" in si:
                v, v0, dx = si["v"], si["v0"], si["dx"]
                if abs(dx) < 1e-9:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "El desplazamiento Δx no puede ser cero para calcular aceleración por Torricelli.")
                val = ((v ** 2) - (v0 ** 2)) / (2.0 * dx)
                interp = cls._interpret_acceleration(val, v0, v)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de aceleración mediante la ecuación de Torricelli",
                    formula="v² = v₀² + 2 · a · Δx   ⇒   a = (v² - v₀²) / (2 · Δx)",
                    justification="Se conocen las velocidades v₀, v y el desplazamiento Δx sin requerir el tiempo.",
                    derivation=[
                        "1. v² = v₀² + 2 · a · Δx",
                        "2. v² - v₀² = 2 · a · Δx",
                        "3. Dividiendo entre (2 · Δx): a = (v² - v₀²) / (2 · Δx)"
                    ],
                    substitution=f"a = [({v:+.4g})² - ({v0:+.4g})²] / [2 · ({dx:+.4g})]",
                    calc_steps=[
                        f"Diferencia de cuadrados: v² - v₀² = {v**2:.4g} - {v0**2:.4g} = {(v**2)-(v0**2):+.4g} (m/s)²",
                        f"Denominador: 2 · Δx = 2 · ({dx:+.4g}) = {2*dx:+.4g} m",
                        f"Aceleración: {(v**2)-(v0**2):+.4g} / {2*dx:+.4g} = {val:+.4g} m/s²"
                    ],
                    final_val_si=val, interp=interp
                )

            # C) Con dx, v0, t -> dx = v0*t + 0.5*a*t² -> a = 2*(dx - v0*t)/t²
            if "dx" in si and "v0" in si and "t" in si:
                dx, v0, t = si["dx"], si["v0"], si["t"]
                if t <= 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "El tiempo t debe ser positivo.")
                val = (2.0 * (dx - (v0 * t))) / (t ** 2)
                interp = cls._interpret_acceleration(val, v0, None)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de aceleración a partir del desplazamiento y tiempo",
                    formula="Δx = v₀ · t + ½ · a · t²   ⇒   a = 2 · (Δx - v₀ · t) / t²",
                    justification="Se conocen el desplazamiento total Δx, la velocidad inicial v₀ y la duración t.",
                    derivation=[
                        "1. Δx = v₀ · t + ½ · a · t²",
                        "2. Δx - v₀ · t = ½ · a · t²",
                        "3. Multiplicando por 2: 2 · (Δx - v₀ · t) = a · t²",
                        "4. Dividiendo entre t²: a = 2 · (Δx - v₀ · t) / t²"
                    ],
                    substitution=f"a = 2 · [({dx:+.4g}) - ({v0:+.4g}) · ({t:.4g})] / ({t:.4g})²",
                    calc_steps=[
                        f"Desplazamiento por velocidad inicial: v₀ · t = ({v0:+.4g}) · ({t:.4g}) = {v0*t:+.4g} m",
                        f"Diferencia: Δx - v₀ · t = {dx:+.4g} - ({v0*t:+.4g}) = {dx - (v0*t):+.4g} m",
                        f"Multiplicado por 2: 2 · ({dx - (v0*t):+.4g}) = {2*(dx - (v0*t)):+.4g} m",
                        f"Dividido entre t² ({t**2:.4g} s²): a = {val:+.4g} m/s²"
                    ],
                    final_val_si=val, interp=interp
                )

        # ---------------------------------------------------------------------
        # CASO 4: Calcular Tiempo (t)
        # ---------------------------------------------------------------------
        if target == "t":
            # A) Con v, v0, a -> t = (v - v0)/a
            if "v" in si and "v0" in si and "a" in si:
                v, v0, a = si["v"], si["v0"], si["a"]
                if abs(a) < 1e-12:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "La aceleración a no puede ser 0 para despejar t con v=v₀+at (sería MRU).")
                val = (v - v0) / a
                if val < 0:
                    return cls._unsolvable(
                        "MRUA", target, spec, target_unit, inputs,
                        f"El tiempo obtenido es negativo (t = {val:.4g} s), lo cual indica que bajo la aceleración a = {a:+.4g} m/s², "
                        f"la velocidad {v:+.4g} m/s precedió al estado inicial o no es alcanzable en el futuro."
                    )
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje del tiempo en la ecuación de velocidad",
                    formula="v = v₀ + a · t   ⇒   t = (v - v₀) / a",
                    justification="Se conocen la velocidad inicial, la velocidad final y la tasa de aceleración constante.",
                    derivation=[
                        "1. v = v₀ + a · t",
                        "2. v - v₀ = a · t",
                        "3. t = (v - v₀) / a"
                    ],
                    substitution=f"t = [({v:+.4g} m/s) - ({v0:+.4g} m/s)] / ({a:+.4g} m/s²)",
                    calc_steps=[
                        f"Cambio de velocidad: Δv = {v - v0:+.4g} m/s",
                        f"División entre la aceleración: ({v - v0:+.4g}) / ({a:+.4g}) = {val:.4g} s"
                    ],
                    final_val_si=val,
                    interp=f"El cuerpo tardará exactamente {val:.4g} segundos en alcanzar la velocidad de {v:+.4g} m/s."
                )

            # B) Con dx, v0, v (Velocidad media) -> t = 2*dx/(v0 + v)
            if "dx" in si and "v0" in si and "v" in si:
                dx, v0, v = si["dx"], si["v0"], si["v"]
                denom = v0 + v
                if abs(denom) < 1e-12:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "La suma v₀ + v es 0 (velocidad media nula), no es posible despejar t.")
                val = (2.0 * dx) / denom
                if val < 0:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, f"El tiempo calculado resultó negativo (t = {val:.4g} s).")
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Tiempo a partir de la velocidad media",
                    formula="Δx = ½ · (v₀ + v) · t   ⇒   t = 2 · Δx / (v₀ + v)",
                    justification="Se conocen el desplazamiento Δx y ambas velocidades (inicial y final).",
                    derivation=[
                        "1. Δx = ½ · (v₀ + v) · t",
                        "2. 2 · Δx = (v₀ + v) · t",
                        "3. t = (2 · Δx) / (v₀ + v)"
                    ],
                    substitution=f"t = [2 · ({dx:+.4g})] / [({v0:+.4g}) + ({v:+.4g})]",
                    calc_steps=[
                        f"Numerador: 2 · Δx = {2*dx:+.4g} m",
                        f"Denominador: v₀ + v = {denom:+.4g} m/s",
                        f"t = {2*dx:+.4g} / {denom:+.4g} = {val:.4g} s"
                    ],
                    final_val_si=val, interp=f"El recorrido de {dx:+.4g} m se completó en {val:.4g} segundos."
                )

            # C) Con dx, v0, a -> ½*a*t² + v0*t - dx = 0 (Resolución Cuadrática)
            if "dx" in si and "v0" in si and "a" in si:
                dx, v0, a = si["dx"], si["v0"], si["a"]
                if abs(a) < 1e-12:
                    # MRU degenerado
                    if abs(v0) < 1e-12:
                        return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "Con v₀=0 y a=0 el móvil está en reposo indefinido.")
                    val = dx / v0
                    return cls._build_solution(
                        scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                        eq_name="Tiempo en MRU (a = 0)",
                        formula="Δx = v₀ · t   ⇒   t = Δx / v₀",
                        justification="La aceleración configurada es cero, comportándose como MRU.",
                        derivation=["t = Δx / v₀"],
                        substitution=f"t = {dx:+.4g} / {v0:+.4g}",
                        calc_steps=[f"t = {val:.4g} s"],
                        final_val_si=val, interp=f"Tiempo de recorrido en velocidad constante: {val:.4g} s."
                    )

                # Coeficientes: A*t² + B*t + C = 0
                A = 0.5 * a
                B = v0
                C = -dx
                disc = (B ** 2) - (4.0 * A * C)

                if disc < 0:
                    return cls._unsolvable(
                        "MRUA", target, spec, target_unit, inputs,
                        f"No existe solución real: El discriminante de la ecuación cuadrática es negativo "
                        f"(Δ = B² - 4AC = ({B:.4g})² - 4({A:.4g})({C:.4g}) = {disc:.4g} < 0). "
                        "Esto demuestra matemáticamente que el móvil nunca llega a alcanzar ese desplazamiento "
                        "con los valores de velocidad inicial y aceleración provistos."
                    )

                sqrt_d = disc ** 0.5
                t1 = (-B + sqrt_d) / (2.0 * A)
                t2 = (-B - sqrt_d) / (2.0 * A)

                # Filtrar raíces físicas t >= 0
                physical_roots = [r for r in (t1, t2) if r >= -1e-9]

                if not physical_roots:
                    return cls._unsolvable(
                        "MRUA", target, spec, target_unit, inputs,
                        f"Ambas raíces matemáticas son negativas (t₁ = {t1:.4g} s, t₂ = {t2:.4g} s). "
                        "El desplazamiento solicitado sólo fue posible en instantes anteriores a t = 0."
                    )

                # Si hay dos raíces positivas (ej: pasa por un punto de ida y luego de vuelta al invertir)
                if len(physical_roots) == 2 and abs(t1 - t2) > 1e-4:
                    val = min(physical_roots)  # Primer cruce
                    notes = (
                        f"La ecuación de segundo grado arroja dos tiempos físicamente válidos:\n"
                        f"• t₁ = {min(t1, t2):.4g} s: Primer cruce (el móvil avanza en el sentido inicial).\n"
                        f"• t₂ = {max(t1, t2):.4g} s: Segundo cruce (el móvil regresa por la misma posición tras frenar e invertir su sentido de marcha)."
                    )
                else:
                    val = max(physical_roots)
                    notes = (
                        f"Raíces matemáticas: t₁ = {t1:.4g} s, t₂ = {t2:.4g} s. "
                        f"Se descarta la raíz negativa por carecer de sentido temporal para t > 0."
                    )

                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Resolución de la ecuación cuadrática del tiempo",
                    formula="Δx = v₀ · t + ½ · a · t²   ⇒   ½ · a · t² + v₀ · t - Δx = 0",
                    justification="El tiempo aparece elevado al cuadrado; se requiere resolver la fórmula general de segundo grado: t = (-B ± √(B² - 4AC)) / 2A.",
                    derivation=[
                        "1. Ecuación horaria: Δx = v₀ · t + ½ · a · t²",
                        "2. Igualando a cero en forma estándar: (½ · a) · t² + (v₀) · t + (-Δx) = 0",
                        f"3. Identificando coeficientes: A = ½ · a = {A:+.4g},  B = v₀ = {B:+.4g},  C = -Δx = {C:+.4g}",
                        "4. Aplicando la fórmula resolvente: t = (-B ± √(B² - 4AC)) / (2A)"
                    ],
                    substitution=f"t = [-({B:+.4g}) ± √(({B:+.4g})² - 4 · ({A:+.4g}) · ({C:+.4g}))] / [2 · ({A:+.4g})]",
                    calc_steps=[
                        f"Discriminante: Δ = ({B:+.4g})² - 4 · ({A:+.4g}) · ({C:+.4g}) = {B**2:.4g} - ({4*A*C:+.4g}) = {disc:.4g}",
                        f"Raíz del discriminante: √Δ = {sqrt_d:.4g}",
                        f"Raíz matemática 1: t₁ = [-({B:+.4g}) + {sqrt_d:.4g}] / ({2*A:+.4g}) = {t1:.4g} s",
                        f"Raíz matemática 2: t₂ = [-({B:+.4g}) - {sqrt_d:.4g}] / ({2*A:+.4g}) = {t2:.4g} s",
                        f"Solución física seleccionada: t = {val:.4g} s"
                    ],
                    final_val_si=val,
                    interp=f"El cuerpo alcanza la posición solicitada a los {val:.4g} segundos de iniciada la simulación.",
                    mult_note=notes
                )

        # ---------------------------------------------------------------------
        # CASO 5: Calcular Desplazamiento (dx) o Posición Final (x)
        # ---------------------------------------------------------------------
        if target in ("dx", "x"):
            # A) Con v0, a, t -> dx = v0*t + 0.5*a*t²
            if "v0" in si and "a" in si and "t" in si:
                v0, a, t = si["v0"], si["a"], si["t"]
                dx_val = (v0 * t) + (0.5 * a * (t ** 2))
                x0_val = si.get("x0", 0.0)
                final_val = (x0_val + dx_val) if target == "x" else dx_val

                formula_text = "x = x₀ + v₀ · t + ½ · a · t²" if target == "x" else "Δx = v₀ · t + ½ · a · t²"
                eq_title = "Ecuación horaria de la posición en MRUA" if target == "x" else "Ecuación del desplazamiento en MRUA"
                interp = (
                    f"El cuerpo experimenta un desplazamiento de {dx_val:+.4g} m, "
                    f"alcanzando la coordenada x = {final_val:+.4g} m."
                    if target == "x"
                    else f"El desplazamiento neto experimentado es de {dx_val:+.4g} m."
                )

                steps = [
                    f"Término de avance por velocidad inicial: v₀ · t = ({v0:+.4g}) · ({t:.4g}) = {v0*t:+.4g} m",
                    f"Término de aceleración: ½ · a · t² = 0.5 · ({a:+.4g}) · ({t**2:.4g}) = {0.5*a*(t**2):+.4g} m",
                    f"Suma de componentes: Δx = {v0*t:+.4g} + ({0.5*a*(t**2):+.4g}) = {dx_val:+.4g} m"
                ]
                if target == "x":
                    steps.append(f"Posición final: x = x₀ + Δx = {x0_val:+.4g} + ({dx_val:+.4g}) = {final_val:+.4g} m")

                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name=eq_title,
                    formula=formula_text,
                    justification="Se conocen la velocidad inicial v₀, la aceleración constante a y el tiempo t.",
                    derivation=["La variable se encuentra despejada analíticamente."],
                    substitution=f"Δx = ({v0:+.4g} m/s) · ({t:.4g} s) + ½ · ({a:+.4g} m/s²) · ({t:.4g} s)²",
                    calc_steps=steps,
                    final_val_si=final_val, interp=interp
                )

            # B) Con v, v0, a (Torricelli) -> dx = (v² - v0²)/(2*a)
            if "v" in si and "v0" in si and "a" in si:
                v, v0, a = si["v"], si["v0"], si["a"]
                if abs(a) < 1e-12:
                    return cls._unsolvable("MRUA", target, spec, target_unit, inputs, "Aceleración nula: use las fórmulas de MRU.")
                dx_val = ((v ** 2) - (v0 ** 2)) / (2.0 * a)
                x0_val = si.get("x0", 0.0)
                final_val = (x0_val + dx_val) if target == "x" else dx_val

                steps = [
                    f"Cuadrados de las velocidades: v² = {v**2:.4g},  v₀² = {v0**2:.4g}",
                    f"Diferencia: v² - v₀² = {(v**2)-(v0**2):+.4g} (m/s)²",
                    f"Denominador: 2 · a = {2*a:+.4g} m/s²",
                    f"Δx = {(v**2)-(v0**2):+.4g} / ({2*a:+.4g}) = {dx_val:+.4g} m"
                ]
                if target == "x":
                    steps.append(f"x = x₀ + Δx = {x0_val:+.4g} + ({dx_val:+.4g}) = {final_val:+.4g} m")

                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Despeje de desplazamiento mediante Torricelli",
                    formula="v² = v₀² + 2 · a · Δx   ⇒   Δx = (v² - v₀²) / (2 · a)",
                    justification="Se conocen ambas velocidades y la aceleración, prescindiendo del tiempo.",
                    derivation=[
                        "1. v² = v₀² + 2 · a · Δx",
                        "2. v² - v₀² = 2 · a · Δx",
                        "3. Δx = (v² - v₀²) / (2 · a)"
                    ],
                    substitution=f"Δx = [({v:+.4g})² - ({v0:+.4g})²] / [2 · ({a:+.4g})]",
                    calc_steps=steps,
                    final_val_si=final_val, interp=f"El cuerpo recorre un desplazamiento neto de {dx_val:+.4g} m."
                )

            # C) Con v0, v, t (Velocidad media) -> dx = ((v0 + v)/2)*t
            if "v0" in si and "v" in si and "t" in si:
                v0, v, t = si["v0"], si["v"], si["t"]
                dx_val = ((v0 + v) / 2.0) * t
                x0_val = si.get("x0", 0.0)
                final_val = (x0_val + dx_val) if target == "x" else dx_val

                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Desplazamiento por velocidad media",
                    formula="Δx = ½ · (v₀ + v) · t",
                    justification="En aceleración constante, la velocidad media es el promedio aritmético de v₀ y v.",
                    derivation=["Δx = ((v₀ + v) / 2) · t"],
                    substitution=f"Δx = [({v0:+.4g}) + ({v:+.4g})] / 2 · ({t:.4g})",
                    calc_steps=[
                        f"Velocidad media: (v₀ + v) / 2 = ({v0+v:+.4g}) / 2 = {(v0+v)/2:+.4g} m/s",
                        f"Multiplicación por el tiempo: {(v0+v)/2:+.4g} · {t:.4g} = {dx_val:+.4g} m"
                    ],
                    final_val_si=final_val, interp=f"El desplazamiento obtenido es {dx_val:+.4g} m."
                )

        # ---------------------------------------------------------------------
        # CASO 6: Distancia recorrida (d)
        # ---------------------------------------------------------------------
        if target == "d":
            if "v0" in si and "a" in si and "t" in si:
                v0, a, t = si["v0"], si["a"], si["t"]
                # Comprobar si invierte sentido
                if a != 0 and (a * v0 < 0):
                    t_turn = -v0 / a
                    if 0 < t_turn < t:
                        # Hubo inversión de sentido
                        d1 = (v0 ** 2) / (2.0 * abs(a))
                        pos_turn = (v0 * t_turn) + (0.5 * a * (t_turn ** 2))
                        pos_final = (v0 * t) + (0.5 * a * (t ** 2))
                        d2 = abs(pos_final - pos_turn)
                        val = d1 + d2
                        notes = (
                            f"¡Atención física importante!: El cuerpo desaceleró hasta detenerse a los t = {t_turn:.4g} s "
                            f"(alcanzando una distancia de frenado d₁ = {d1:.4g} m) y luego comenzó a retroceder "
                            f"durante los restantes {t - t_turn:.4g} s (recorriendo d₂ = {d2:.4g} m). "
                            "Por tanto, la distancia escalar total recorrida es la suma de ambos tramos: d = d₁ + d₂."
                        )
                        return cls._build_solution(
                            scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                            eq_name="Cálculo de distancia total con cambio de sentido",
                            formula="d = d_frenado + d_retorno = (|v₀|² / 2|a|) + |x(t) - x_inversión|",
                            justification="La velocidad inicial y la aceleración tienen signos opuestos; el móvil se detiene e invierte su marcha antes de concluir el tiempo total.",
                            derivation=[
                                f"1. Tiempo de inversión: t_inv = -v₀ / a = -({v0:+.4g}) / ({a:+.4g}) = {t_turn:.4g} s",
                                f"2. Distancia hasta detenerse: d₁ = v₀² / (2 · |a|) = {d1:.4g} m",
                                f"3. Distancia en sentido inverso: d₂ = ½ · |a| · (t - t_inv)² = {d2:.4g} m",
                                "4. Distancia total recorrida: d = d₁ + d₂"
                            ],
                            substitution=f"d = {d1:.4g} m + {d2:.4g} m",
                            calc_steps=[
                                f"Distancia tramo 1 (hasta v=0): {d1:.4g} m",
                                f"Distancia tramo 2 (en retroceso): {d2:.4g} m",
                                f"Distancia total: {val:.4g} m"
                            ],
                            final_val_si=val, interp=f"La distancia total recorrida sobre la pista es {val:.4g} m.", mult_note=notes
                        )

                # Si no invierte sentido, d = |Δx|
                dx_val = (v0 * t) + (0.5 * a * (t ** 2))
                val = abs(dx_val)
                return cls._build_solution(
                    scenario="MRUA", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Distancia recorrida en trayectoria unidireccional",
                    formula="d = |Δx| = |v₀ · t + ½ · a · t²|",
                    justification="El movimiento no presentó inversión de marcha en este intervalo de tiempo.",
                    derivation=["d = |Δx|"],
                    substitution=f"d = |({v0:+.4g}) · ({t:.4g}) + ½ · ({a:+.4g}) · ({t:.4g})²|",
                    calc_steps=[
                        f"Desplazamiento: Δx = {dx_val:+.4g} m",
                        f"Magnitud escalar: d = |{dx_val:+.4g}| = {val:.4g} m"
                    ],
                    final_val_si=val, interp=f"El cuerpo recorrió una distancia de {val:.4g} m."
                )

        # Si llegamos aquí, los datos provistos no fueron suficientes para resolver
        return cls._unsolvable(
            "MRUA", target, spec, target_unit, inputs,
            cls._diagnose_missing_data("MRUA", target, si)
        )

    # =========================================================================
    # RESOLUTOR CAÍDA LIBRE / LANZAMIENTO VERTICAL
    # =========================================================================

    @classmethod
    def _solve_free_fall(
        cls,
        si: Dict[str, float],
        inputs: List[InputVariable],
        target: str,
        spec: VariableSpec,
        target_unit: str
    ) -> StepByStepSolution:
        """Resuelve problemas de caída libre y lanzamiento vertical bajo gravedad g."""
        g = si.get("g", 9.81)

        # ---------------------------------------------------------------------
        # Altura máxima: h_max = y0 + v0² / (2g)
        # ---------------------------------------------------------------------
        if target == "h_max":
            if "v0" in si:
                v0 = si["v0"]
                y0 = si.get("y0", 0.0)
                if v0 <= 0:
                    val = y0
                    notes = "Como la velocidad inicial es nula o descendente (v₀ ≤ 0), el objeto no asciende; por tanto la altura máxima es su posición inicial."
                else:
                    val = y0 + ((v0 ** 2) / (2.0 * g))
                    notes = f"En la cúspide de la trayectoria, la velocidad instantánea se anula momentáneamente (v = 0 m/s)."

                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Altura máxima en lanzamiento vertical",
                    formula="h_máx = y₀ + (v₀² / (2 · g))",
                    justification="Se conocen la velocidad inicial vertical v₀ y la aceleración gravitatoria g.",
                    derivation=[
                        "1. En el punto más alto, la velocidad vertical se anula: v = 0",
                        "2. Torricelli: v² = v₀² - 2 · g · (h_máx - y₀) = 0",
                        "3. 2 · g · (h_máx - y₀) = v₀²",
                        "4. h_máx = y₀ + (v₀² / (2 · g))"
                    ],
                    substitution=f"h_máx = ({y0:.4g} m) + [({v0:+.4g} m/s)² / (2 · {g:.4g} m/s²)]",
                    calc_steps=[
                        f"Cuadrado de v₀: ({v0:+.4g})² = {v0**2:.4g} (m/s)²",
                        f"Denominador: 2 · g = 2 · {g:.4g} = {2*g:.4g} m/s²",
                        f"Ascenso adicional: {v0**2:.4g} / {2*g:.4g} = {(v0**2)/(2*g) if v0 > 0 else 0.0:.4g} m",
                        f"Altura máxima absoluta: {val:.4g} m"
                    ],
                    final_val_si=val, interp=f"El objeto alcanza una cota máxima de {val:.4g} metros sobre el suelo.", mult_note=notes
                )

        # ---------------------------------------------------------------------
        # Tiempo de subida: t_subida = v0 / g
        # ---------------------------------------------------------------------
        if target == "t_subida":
            if "v0" in si:
                v0 = si["v0"]
                val = max(0.0, v0 / g)
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Tiempo de subida hasta la cúspide",
                    formula="t_subida = v₀ / g",
                    justification="Es el tiempo necesario para que la gravedad reduzca la velocidad vertical ascendente hasta cero.",
                    derivation=[
                        "1. v = v₀ - g · t",
                        "2. En la altura máxima: v = 0",
                        "3. 0 = v₀ - g · t_subida  ⇒  t_subida = v₀ / g"
                    ],
                    substitution=f"t_subida = ({v0:+.4g} m/s) / ({g:.4g} m/s²)",
                    calc_steps=[f"t_subida = {val:.4g} s"],
                    final_val_si=val, interp=f"El ascenso dura {val:.4g} segundos hasta detenerse momentáneamente en el ápice."
                )

        # ---------------------------------------------------------------------
        # Tiempo de vuelo hasta y0: t_vuelo = 2*v0 / g
        # ---------------------------------------------------------------------
        if target == "t_vuelo":
            if "v0" in si:
                v0 = si["v0"]
                if v0 <= 0:
                    val = 0.0
                else:
                    val = (2.0 * v0) / g
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Tiempo de vuelo simétrico (retorno a la altura de disparo y₀)",
                    formula="t_vuelo = 2 · v₀ / g = 2 · t_subida",
                    justification="En ausencia de resistencia del aire, la trayectoria vertical es perfectamente simétrica: el tiempo de subida es igual al tiempo de bajada.",
                    derivation=[
                        "1. Desplazamiento neto al regresar al punto de lanzamiento: Δy = 0",
                        "2. Δy = v₀ · t - ½ · g · t² = 0",
                        "3. Factorizando t: t · (v₀ - ½ · g · t) = 0",
                        "4. Raíz t = 0 (inicio), o bien v₀ = ½ · g · t  ⇒  t_vuelo = 2 · v₀ / g"
                    ],
                    substitution=f"t_vuelo = 2 · ({v0:+.4g}) / ({g:.4g})",
                    calc_steps=[f"t_vuelo = {val:.4g} s"],
                    final_val_si=val, interp=f"El objeto permanece en el aire durante {val:.4g} s antes de volver al nivel de partida."
                )

        # ---------------------------------------------------------------------
        # Tiempo de impacto con el suelo (y = 0): t_impacto
        # ---------------------------------------------------------------------
        if target == "t_impacto":
            if "y0" in si and "v0" in si:
                y0, v0 = si["y0"], si["v0"]
                disc = (v0 ** 2) + (2.0 * g * y0)
                sqrt_d = disc ** 0.5
                val = (v0 + sqrt_d) / g
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Tiempo total hasta el impacto contra el suelo (y = 0)",
                    formula="y(t) = y₀ + v₀ · t - ½ · g · t² = 0   ⇒   t_impacto = (v₀ + √(v₀² + 2·g·y₀)) / g",
                    justification="Se resuelve la condición de frontera en la que la coordenada de altura es y = 0 m.",
                    derivation=[
                        "1. y = y₀ + v₀ · t - ½ · g · t² = 0",
                        "2. Multiplicando por -1: ½ · g · t² - v₀ · t - y₀ = 0",
                        "3. Coeficientes cuadráticos: A = ½·g,  B = -v₀,  C = -y₀",
                        "4. Raíz positiva: t = (v₀ + √(v₀² + 2·g·y₀)) / g"
                    ],
                    substitution=f"t_impacto = [({v0:+.4g}) + √(({v0:+.4g})² + 2 · ({g:.4g}) · ({y0:.4g}))] / ({g:.4g})",
                    calc_steps=[
                        f"Discriminante: v₀² + 2·g·y₀ = {v0**2:.4g} + {2*g*y0:.4g} = {disc:.4g}",
                        f"Raíz: √Δ = {sqrt_d:.4g}",
                        f"t_impacto = ({v0:+.4g} + {sqrt_d:.4g}) / {g:.4g} = {val:.4g} s"
                    ],
                    final_val_si=val, interp=f"El objeto colisiona contra el suelo {val:.4g} segundos después de ser liberado."
                )

        # ---------------------------------------------------------------------
        # Velocidad de impacto con el suelo (y = 0): v_impacto
        # ---------------------------------------------------------------------
        if target == "v_impacto":
            if "y0" in si and "v0" in si:
                y0, v0 = si["y0"], si["v0"]
                disc = (v0 ** 2) + (2.0 * g * y0)
                val = -(disc ** 0.5)
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Velocidad en el instante de impacto contra el suelo",
                    formula="v_impacto = -√(v₀² + 2 · g · y₀)",
                    justification="Conservación de la energía mecánica o aplicación directa de Torricelli para y = 0.",
                    derivation=[
                        "1. v² = v₀² - 2 · g · (y - y₀)",
                        "2. Evaluando en el suelo y = 0: v² = v₀² - 2 · g · (-y₀) = v₀² + 2 · g · y₀",
                        "3. Dado que el cuerpo se dirige hacia abajo en el impacto, se escoge el signo negativo: v = -√(v₀² + 2 · g · y₀)"
                    ],
                    substitution=f"v_impacto = -√[({v0:+.4g})² + 2 · ({g:.4g}) · ({y0:.4g})]",
                    calc_steps=[
                        f"Término cuadrático: v₀² + 2·g·y₀ = {disc:.4g}",
                        f"Velocidad vectorial: -√({disc:.4g}) = {val:.4g} m/s"
                    ],
                    final_val_si=val, interp=f"Impacta contra el suelo con una rapidez de {abs(val):.4g} m/s apuntando hacia abajo."
                )

        # ---------------------------------------------------------------------
        # Velocidad instantánea en un tiempo t dado: v(t) = v0 - g*t
        # ---------------------------------------------------------------------
        if target == "v":
            if "v0" in si and "t" in si:
                v0, t = si["v0"], si["t"]
                val = v0 - (g * t)
                interp = "El objeto asciende" if val > 0 else ("El objeto desciende" if val < 0 else "El objeto está en su punto de máxima altura (v = 0)")
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Velocidad en función del tiempo bajo gravedad",
                    formula="v(t) = v₀ - g · t",
                    justification="La aceleración vertical hacia abajo es -g constante.",
                    derivation=["v = v₀ - g · t"],
                    substitution=f"v = ({v0:+.4g} m/s) - [({g:.4g} m/s²) · ({t:.4g} s)]",
                    calc_steps=[
                        f"g · t = {g*t:.4g} m/s",
                        f"v = {v0:+.4g} - {g*t:.4g} = {val:+.4g} m/s"
                    ],
                    final_val_si=val, interp=f"{interp} con una velocidad instantánea de {val:+.4g} m/s."
                )

        # ---------------------------------------------------------------------
        # Altura instantánea en un tiempo t dado: y(t) = y0 + v0*t - 0.5*g*t²
        # ---------------------------------------------------------------------
        if target in ("y", "dy"):
            if "v0" in si and "t" in si:
                v0, t = si["v0"], si["t"]
                y0 = si.get("y0", 0.0)
                dy_val = (v0 * t) - (0.5 * g * (t ** 2))
                val = (y0 + dy_val) if target == "y" else dy_val
                return cls._build_solution(
                    scenario="CAIDA_LIBRE", target=target, spec=spec, target_unit=target_unit, inputs=inputs,
                    eq_name="Ecuación horaria de la altura",
                    formula="y(t) = y₀ + v₀ · t - ½ · g · t²" if target == "y" else "Δy = v₀ · t - ½ · g · t²",
                    justification="Ecuación de posición vertical para aceleración constante -g.",
                    derivation=["y = y₀ + v₀ · t - ½ · g · t²"],
                    substitution=f"y = ({y0:.4g}) + ({v0:+.4g}) · ({t:.4g}) - ½ · ({g:.4g}) · ({t:.4g})²",
                    calc_steps=[
                        f"v₀ · t = {v0*t:+.4g} m",
                        f"½ · g · t² = {0.5*g*(t**2):.4g} m",
                        f"y = {y0:.4g} + {v0*t:+.4g} - {0.5*g*(t**2):.4g} = {val:.4g} m"
                    ],
                    final_val_si=val, interp=f"En t = {t:.4g} s, la altura del objeto es {val:.4g} metros."
                )

        return cls._unsolvable(
            "CAIDA_LIBRE", target, spec, target_unit, inputs,
            cls._diagnose_missing_data("CAIDA_LIBRE", target, si)
        )

    # =========================================================================
    # AUXILIARES DE DIAGNÓSTICO E INTERPRETACIÓN
    # =========================================================================

    @staticmethod
    def _diagnose_missing_data(scenario: str, target: str, si: Dict[str, float]) -> str:
        """Explica con precisión pedagógica qué variables faltan para resolver."""
        known_symbols = [VARIABLES_CATALOG[k].symbol for k in si.keys() if k in VARIABLES_CATALOG]
        known_str = ", ".join(known_symbols) if known_symbols else "ninguno"
        target_sym = VARIABLES_CATALOG[target].symbol

        combinations = {
            "v": ["(v₀, a, t)", "(v₀, a, Δx)", "(v₀, Δx, t)"],
            "v0": ["(v, a, t)", "(v, a, Δx)", "(Δx, a, t)"],
            "a": ["(v, v₀, t)", "(v, v₀, Δx)", "(Δx, v₀, t)"],
            "t": ["(v, v₀, a)", "(v, v₀, Δx)", "(Δx, v₀, a)"],
            "dx": ["(v₀, a, t)", "(v, v₀, a)", "(v₀, v, t)"],
            "x": ["(x₀, v₀, a, t)", "(x₀, v, v₀, a)", "(x₀, v₀, v, t)"],
            "d": ["(v₀, a, t)"],
            "h_max": ["(v₀, g) y opcionalmente y₀"],
            "t_subida": ["(v₀, g)"],
            "t_vuelo": ["(v₀, g)"],
            "t_impacto": ["(y₀, v₀, g)"],
            "v_impacto": ["(y₀, v₀, g)"]
        }
        needed = combinations.get(target, ["datos cinemáticos adicionales"])
        needed_str = " o bien ".join(needed)

        return (
            f"Datos insuficientes para determinar '{target_sym}'. "
            f"Se han proporcionado: {known_str}. "
            f"Para calcular {target_sym} en {scenario}, se requiere disponer de al menos una combinación como: {needed_str}. "
            "Por favor, introduzca los parámetros faltantes en el formulario."
        )

    @staticmethod
    def _interpret_velocity(val: float, v0: Optional[float], a: Optional[float]) -> str:
        """Genera interpretación física de la velocidad."""
        sign_desc = "hacia el sentido positivo (derecha)" if val > 0 else ("hacia el sentido negativo (izquierda)" if val < 0 else "en reposo momentáneo")
        if v0 is not None and a is not None:
            if abs(val) > abs(v0):
                return f"El vehículo se desplaza a {val:+.4g} m/s {sign_desc}. Su rapidez aumentó respecto al inicio (acelera)."
            elif abs(val) < abs(v0):
                return f"El vehículo se desplaza a {val:+.4g} m/s {sign_desc}. Su rapidez disminuyó respecto al inicio (frena/desacelera)."
            else:
                return f"El vehículo mantiene una rapidez constante de {abs(val):.4g} m/s."
        return f"La velocidad instantánea del objeto es {val:+.4g} m/s {sign_desc}."

    @staticmethod
    def _interpret_acceleration(a: float, v0: Optional[float], v: Optional[float]) -> str:
        """Genera interpretación física de la aceleración."""
        if abs(a) < 1e-9:
            return "La aceleración es nula (a = 0 m/s²), lo que corresponde a un Movimiento Rectilíneo Uniforme (MRU)."
        if v0 is not None:
            if (a * v0) > 0:
                return f"Aceleración positiva en el sentido del movimiento ({a:+.4g} m/s²). El móvil aumenta progresivamente su rapidez."
            elif (a * v0) < 0:
                return f"Aceleración de signo opuesto a la velocidad ({a:+.4g} m/s²). El móvil experimenta una desaceleración (frenado)."
        return f"Aceleración constante de {a:+.4g} m/s²."

    @classmethod
    def _build_solution(
        cls,
        scenario: str,
        target: str,
        spec: VariableSpec,
        target_unit: str,
        inputs: List[InputVariable],
        eq_name: str,
        formula: str,
        justification: str,
        derivation: List[str],
        substitution: str,
        calc_steps: List[str],
        final_val_si: float,
        interp: str,
        mult_note: Optional[str] = None
    ) -> StepByStepSolution:
        """Construye el objeto de solución completa asegurando conversión a la unidad destino."""
        final_val_target = UnitConverter.from_si(final_val_si, spec.dimension, target_unit)
        return StepByStepSolution(
            is_solvable=True,
            scenario=scenario,
            target_code=target,
            target_spec=spec,
            target_unit=target_unit,
            known_inputs=inputs,
            equation_name=eq_name,
            equation_formula=formula,
            justification=justification,
            derivation_steps=derivation,
            substitution_text=substitution,
            calculation_steps=calc_steps,
            final_value_si=final_val_si,
            final_unit_si=spec.default_unit,
            final_value_target=final_val_target,
            physical_interpretation=interp,
            multiple_solutions_note=mult_note,
            diagnostic_error=None
        )

    @classmethod
    def _unsolvable(
        cls,
        scenario: str,
        target: str,
        spec: VariableSpec,
        target_unit: str,
        inputs: List[InputVariable],
        error_msg: str
    ) -> StepByStepSolution:
        """Construye un objeto de solución cuando el problema no puede resolverse."""
        return StepByStepSolution(
            is_solvable=False,
            scenario=scenario,
            target_code=target,
            target_spec=spec,
            target_unit=target_unit,
            known_inputs=inputs,
            diagnostic_error=error_msg
        )
