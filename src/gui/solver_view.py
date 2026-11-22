"""
Módulo de la Vista del Solucionador de Problemas de Cinemática Paso a Paso.

Proporciona un entorno interactivo dedicado exclusivamente a la resolución analítica
de problemas de física de MRUA y Caída Libre:
- Selector de escenario (MRUA Horizontal o Caída Libre Vertical).
- Catálogo de ejercicios tipo de examen para carga inmediata.
- Formulario de entrada de datos con selección de unidades multidimensionales.
- Selector de la variable incógnita a encontrar.
- Despliegue pedagógico completo en 10 pasos estructurados:
    1. Datos conocidos con unidades originales y conversión al SI.
    2. Incógnita a despejar.
    3. Ecuación seleccionada con justificación física.
    4. Despeje algebraico paso a paso.
    5. Sustitución numérica.
    6. Operaciones matemáticas detalladas.
    7. Resultado final con unidad correspondiente.
    8. Interpretación física del resultado.
    9. Análisis de soluciones múltiples (raíces cuadráticas y signos ±√).
- Diagnóstico inteligente si los datos son insuficientes.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional, Tuple, Any
from .theme import Theme
from ..models.solver import KinematicsSolver, StepByStepSolution, VARIABLES_CATALOG, VariableSpec
from ..models.units import LengthUnit, TimeUnit, VelocityUnit, AccelerationUnit


class SolverView(tk.Frame):
    """Panel principal de Resolución de Problemas de Física Paso a Paso."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)

        self.scenario_var = tk.StringVar(value="MRUA")  # "MRUA" o "CAIDA_LIBRE"
        self.preset_problem_var = tk.StringVar(value="-- Seleccionar Ejercicio Tipo de Examen --")

        # Variables de entrada dinámicas
        self.entry_vars: Dict[str, tk.StringVar] = {}
        self.unit_vars: Dict[str, tk.StringVar] = {}
        self.target_var = tk.StringVar(value="v")
        self.target_unit_var = tk.StringVar(value="m/s")

        self._build_ui()
        self._on_scenario_changed()

    def _build_ui(self) -> None:
        # Encabezado
        header_box = tk.Frame(self, bg=Theme.BG_CARD, padx=16, pady=10)
        header_box.pack(fill=tk.X, padx=10, pady=(10, 6))

        tk.Label(
            header_box,
            text="🧮 RESOLUCIÓN DE PROBLEMAS DE CINEMÁTICA PASO A PASO",
            bg=Theme.BG_CARD,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 13, "bold")
        ).pack(anchor="w")

        tk.Label(
            header_box,
            text="Solucionador analítico riguroso | Despejes algebraicos, operaciones intermedias e interpretación física",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", pady=(2, 0))

        # Contenedor dividido en dos columnas: Izquierda (Entradas) y Derecha (Solución)
        main_split = tk.Frame(self, bg=Theme.BG_DARK)
        main_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # === COLUMNA IZQUIERDA: FORMULARIO DE DATOS ===
        left_col = tk.Frame(main_split, bg=Theme.BG_CARD, width=380, padx=12, pady=10)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_col.pack_propagate(False)

        # 1. Selector de Escenario
        sec_scenario = tk.LabelFrame(
            left_col, text=" 1. Tipo de Movimiento ",
            bg=Theme.BG_CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold"), padx=6, pady=4
        )
        sec_scenario.pack(fill=tk.X, pady=(0, 6))

        tk.Radiobutton(
            sec_scenario, text="MRUA Horizontal (Aceleración Cte)", variable=self.scenario_var,
            value="MRUA", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, command=self._on_scenario_changed, font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", pady=1)

        tk.Radiobutton(
            sec_scenario, text="Caída Libre / Lanzamiento Vertical", variable=self.scenario_var,
            value="CAIDA_LIBRE", bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, selectcolor=Theme.BG_DARK,
            activebackground=Theme.BG_CARD, command=self._on_scenario_changed, font=(Theme.FONT_FAMILY, 9)
        ).pack(anchor="w", pady=1)

        # 2. Selector de Ejercicios Predefinidos
        sec_exam = tk.LabelFrame(
            left_col, text=" 2. Ejercicios Tipo de Examen ",
            bg=Theme.BG_CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold"), padx=6, pady=4
        )
        sec_exam.pack(fill=tk.X, pady=(0, 6))

        self.cmb_exam = ttk.Combobox(
            sec_exam, textvariable=self.preset_problem_var, state="readonly"
        )
        self.cmb_exam.pack(fill=tk.X, pady=2)
        self.cmb_exam.bind("<<ComboboxSelected>>", self._on_preset_problem_selected)

        # 3. Selector de Incógnita
        self.sec_target = tk.LabelFrame(
            left_col, text=" 3. ¿Qué variable desea calcular? ",
            bg=Theme.BG_CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold"), padx=6, pady=4
        )
        self.sec_target.pack(fill=tk.X, pady=(0, 6))

        f_target_sel = tk.Frame(self.sec_target, bg=Theme.BG_CARD)
        f_target_sel.pack(fill=tk.X, pady=2)

        self.cmb_target = ttk.Combobox(f_target_sel, textvariable=self.target_var, state="readonly", width=18)
        self.cmb_target.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmb_target.bind("<<ComboboxSelected>>", self._on_target_changed)

        tk.Label(f_target_sel, text=" en: ", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(side=tk.LEFT)
        self.cmb_target_unit = ttk.Combobox(f_target_sel, textvariable=self.target_unit_var, state="readonly", width=6)
        self.cmb_target_unit.pack(side=tk.LEFT)

        # 4. Formulario de Datos Conocidos
        self.sec_inputs = tk.LabelFrame(
            left_col, text=" 4. Datos Conocidos del Problema ",
            bg=Theme.BG_CARD, fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold"), padx=6, pady=4
        )
        self.sec_inputs.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.inputs_container = tk.Frame(self.sec_inputs, bg=Theme.BG_CARD)
        self.inputs_container.pack(fill=tk.BOTH, expand=True)

        # Botón Resolver
        btn_action_box = tk.Frame(left_col, bg=Theme.BG_CARD)
        btn_action_box.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(
            btn_action_box,
            text="🚀 Resolver Paso a Paso",
            style="Primary.TButton",
            command=self.solve_problem
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            btn_action_box,
            text="🧹 Limpiar Campos",
            style="Secondary.TButton",
            command=self.clear_fields
        ).pack(fill=tk.X, pady=2)

        # === COLUMNA DERECHA: DESPLIEGUE PASO A PASO ===
        right_col = tk.Frame(main_split, bg=Theme.BG_CARD)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Barra superior de la solución con botón Copiar
        sol_header = tk.Frame(right_col, bg=Theme.BG_CARD_LIGHT, padx=12, pady=6)
        sol_header.pack(fill=tk.X)

        tk.Label(
            sol_header,
            text="DESARROLLO PEDAGÓGICO COMPLETO",
            bg=Theme.BG_CARD_LIGHT,
            fg=Theme.PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(side=tk.LEFT)

        ttk.Button(
            sol_header,
            text="📋 Copiar Solución",
            style="Secondary.TButton",
            command=self.copy_solution_to_clipboard
        ).pack(side=tk.RIGHT)

        # Área de texto enriquecido scrollable para la solución
        text_container = tk.Frame(right_col, bg=Theme.BG_DARK)
        text_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.txt_solution = tk.Text(
            text_container,
            bg=Theme.BG_CANVAS,
            fg=Theme.TEXT_LIGHT,
            font=("DejaVu Sans Mono", 10),
            padx=16,
            pady=14,
            wrap=tk.WORD,
            relief=tk.FLAT,
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.txt_solution.yview)
        self.txt_solution.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_solution.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configurar tags de estilo en el texto
        self._setup_text_tags()
        self._display_welcome_message()

    def _setup_text_tags(self) -> None:
        self.txt_solution.tag_configure("title", font=(Theme.FONT_FAMILY, 12, "bold"), foreground=Theme.PRIMARY)
        self.txt_solution.tag_configure("subtitle", font=(Theme.FONT_FAMILY, 10, "bold"), foreground="#38bdf8")
        self.txt_solution.tag_configure("step_header", font=(Theme.FONT_FAMILY, 10, "bold"), foreground="#f59e0b")
        self.txt_solution.tag_configure("formula", font=("DejaVu Sans Mono", 11, "bold"), foreground="#4ade80")
        self.txt_solution.tag_configure("highlight", font=("DejaVu Sans Mono", 11, "bold"), foreground="#facc15")
        self.txt_solution.tag_configure("success_box", font=(Theme.FONT_FAMILY, 12, "bold"), foreground="#22c55e")
        self.txt_solution.tag_configure("error_box", font=(Theme.FONT_FAMILY, 10, "bold"), foreground="#ef4444")
        self.txt_solution.tag_configure("notes", font=(Theme.FONT_FAMILY, 9, "italic"), foreground=Theme.TEXT_MUTED)

    def _display_welcome_message(self) -> None:
        self.txt_solution.config(state="normal")
        self.txt_solution.delete("1.0", tk.END)
        self.txt_solution.insert(tk.END, "BIENVENIDO AL SOLUCIONADOR PASO A PASO DE CINEMÁTICA\n\n", "title")
        self.txt_solution.insert(
            tk.END,
            "Este módulo resuelve problemas de MRUA y Caída Libre mostrando todos los pasos algebraicos:\n\n"
            "1. Seleccione el tipo de movimiento (MRUA o Caída Libre).\n"
            "2. Elija qué incógnita desea encontrar en la lista desplegable.\n"
            "3. Ingrese los datos conocidos que tenga en su enunciado (con sus respectivas unidades).\n"
            "4. Presione '🚀 Resolver Paso a Paso' o cargue uno de los 'Ejercicios Tipo de Examen'.\n\n"
            "El sistema seleccionará la ecuación óptima, mostrará el despeje algebraico literal,\n"
            "sustituirá los valores, resolverá paso a paso las operaciones aritméticas,\n"
            "analizará multiplicidad de soluciones (raíces cuadráticas) y explicará la interpretación física.\n",
            "notes"
        )
        self.txt_solution.config(state="disabled")

    def _on_scenario_changed(self) -> None:
        scenario = self.scenario_var.get()
        # Actualizar lista de presets
        if scenario == "MRUA":
            exam_presets = [
                "-- Seleccionar Ejercicio Tipo de Examen --",
                "1. Automóvil acelera desde reposo: v₀=0, a=2 m/s², t=5 s -> ¿v?",
                "2. Tren frena hasta detenerse: v₀=72 km/h, v=0, a=-2.5 m/s² -> ¿t?",
                "3. Móvil con velocidad y aceleración: v₀=10 m/s, a=3 m/s², dx=100 m -> ¿v?",
                "4. Cálculo de tiempo cuadrático: v₀=4 m/s, a=2 m/s², dx=12 m -> ¿t?",
                "5. Desplazamiento por velocidad media: v₀=10 m/s, v=30 m/s, t=8 s -> ¿Δx?"
            ]
            target_codes = ["v", "v0", "a", "t", "dx", "x", "d"]
        else:
            exam_presets = [
                "-- Seleccionar Ejercicio Tipo de Examen --",
                "1. Dejado caer desde reposo: y₀=45 m, v₀=0, g=9.81 m/s² -> ¿t_impacto?",
                "2. Tiro vertical hacia arriba: y₀=0, v₀=30 m/s -> ¿h_máx?",
                "3. Tiempo de subida y vuelo: y₀=0, v₀=20 m/s -> ¿t_subida?",
                "4. Velocidad de impacto contra el suelo: y₀=80 m, v₀=0 -> ¿v_impacto?",
                "5. Tiro vertical desde edificio: y₀=50 m, v₀=15 m/s, t=2 s -> ¿y?"
            ]
            target_codes = ["h_max", "t_subida", "t_vuelo", "t_impacto", "v_impacto", "y", "dy", "v", "v0", "t"]

        self.cmb_exam["values"] = exam_presets
        self.preset_problem_var.set(exam_presets[0])

        target_display = [f"{VARIABLES_CATALOG[c].symbol} ({VARIABLES_CATALOG[c].name})" for c in target_codes]
        self.cmb_target["values"] = target_display
        if target_display:
            self.cmb_target.current(0)
            self._on_target_changed()

        self._rebuild_input_fields(scenario)

    def _on_target_changed(self, event=None) -> None:
        target_str = self.target_var.get()
        # Extraer código
        symbol = target_str.split(" ")[0].strip()
        code = None
        for c, spec in VARIABLES_CATALOG.items():
            if spec.symbol == symbol:
                code = c
                break
        if not code:
            code = "v"

        spec = VARIABLES_CATALOG.get(code)
        if spec:
            dim = spec.dimension
            if dim == "velocity":
                units = ["m/s", "km/h", "cm/s"]
            elif dim == "acceleration":
                units = ["m/s²", "cm/s²"]
            elif dim == "time":
                units = ["s", "min", "h"]
            else:
                units = ["m", "cm", "km", "mm"]
            self.cmb_target_unit["values"] = units
            self.target_unit_var.set(spec.default_unit)

    def _rebuild_input_fields(self, scenario: str) -> None:
        for widget in self.inputs_container.winfo_children():
            widget.destroy()

        self.entry_vars.clear()
        self.unit_vars.clear()

        if scenario == "MRUA":
            fields = [
                ("v0", "Velocidad inicial (v₀):", ["m/s", "km/h", "cm/s"]),
                ("v", "Velocidad final (v):", ["m/s", "km/h", "cm/s"]),
                ("a", "Aceleración (a):", ["m/s²", "cm/s²", "km/h²"]),
                ("t", "Tiempo transcurrido (t):", ["s", "min", "h"]),
                ("dx", "Desplazamiento (Δx):", ["m", "km", "cm"]),
                ("x0", "Posición inicial (x₀):", ["m", "km", "cm"]),
                ("x", "Posición final (x):", ["m", "km", "cm"])
            ]
        else:
            fields = [
                ("y0", "Altura inicial (y₀):", ["m", "km", "cm"]),
                ("v0", "Velocidad inicial (v₀):", ["m/s", "km/h", "cm/s"]),
                ("g", "Gravedad (g):", ["m/s²", "cm/s²"]),
                ("t", "Tiempo transcurrido (t):", ["s", "min", "h"]),
                ("y", "Altura final (y):", ["m", "km", "cm"]),
                ("dy", "Desplazamiento (Δy):", ["m", "km", "cm"])
            ]

        for code, label, units in fields:
            row = tk.Frame(self.inputs_container, bg=Theme.BG_CARD)
            row.pack(fill=tk.X, pady=2)

            tk.Label(row, text=label, bg=Theme.BG_CARD, fg=Theme.TEXT_LIGHT, font=(Theme.FONT_FAMILY, 8), width=20, anchor="w").pack(side=tk.LEFT)

            var_val = tk.StringVar(value="")
            self.entry_vars[code] = var_val
            ent = ttk.Entry(row, textvariable=var_val, width=8)
            ent.pack(side=tk.LEFT, padx=3)
            ent.bind("<Return>", lambda e: self.solve_problem())

            var_unit = tk.StringVar(value=units[0])
            self.unit_vars[code] = var_unit
            cmb = ttk.Combobox(row, textvariable=var_unit, values=units, state="readonly", width=5)
            cmb.pack(side=tk.RIGHT)

            if scenario == "CAIDA_LIBRE" and code == "g":
                var_val.set("9.81")

    def _on_preset_problem_selected(self, event=None) -> None:
        sel = self.preset_problem_var.get()
        if "--" in sel:
            return

        self.clear_fields()
        scenario = self.scenario_var.get()

        if scenario == "MRUA":
            if "1. Automóvil acelera desde reposo" in sel:
                self._select_target_by_code("v")
                self.entry_vars["v0"].set("0")
                self.entry_vars["a"].set("2")
                self.entry_vars["t"].set("5")
            elif "2. Tren frena hasta detenerse" in sel:
                self._select_target_by_code("t")
                self.entry_vars["v0"].set("72")
                self.unit_vars["v0"].set("km/h")
                self.entry_vars["v"].set("0")
                self.entry_vars["a"].set("-2.5")
            elif "3. Móvil con velocidad y aceleración" in sel:
                self._select_target_by_code("v")
                self.entry_vars["v0"].set("10")
                self.entry_vars["a"].set("3")
                self.entry_vars["dx"].set("100")
            elif "4. Cálculo de tiempo cuadrático" in sel:
                self._select_target_by_code("t")
                self.entry_vars["v0"].set("4")
                self.entry_vars["a"].set("2")
                self.entry_vars["dx"].set("12")
            elif "5. Desplazamiento por velocidad media" in sel:
                self._select_target_by_code("dx")
                self.entry_vars["v0"].set("10")
                self.entry_vars["v"].set("30")
                self.entry_vars["t"].set("8")
        else:
            if "1. Dejado caer desde reposo" in sel:
                self._select_target_by_code("t_impacto")
                self.entry_vars["y0"].set("45")
                self.entry_vars["v0"].set("0")
                self.entry_vars["g"].set("9.81")
            elif "2. Tiro vertical hacia arriba" in sel:
                self._select_target_by_code("h_max")
                self.entry_vars["y0"].set("0")
                self.entry_vars["v0"].set("30")
                self.entry_vars["g"].set("9.81")
            elif "3. Tiempo de subida y vuelo" in sel:
                self._select_target_by_code("t_subida")
                self.entry_vars["y0"].set("0")
                self.entry_vars["v0"].set("20")
                self.entry_vars["g"].set("9.81")
            elif "4. Velocidad de impacto contra el suelo" in sel:
                self._select_target_by_code("v_impacto")
                self.entry_vars["y0"].set("80")
                self.entry_vars["v0"].set("0")
                self.entry_vars["g"].set("9.81")
            elif "5. Tiro vertical desde edificio" in sel:
                self._select_target_by_code("y")
                self.entry_vars["y0"].set("50")
                self.entry_vars["v0"].set("15")
                self.entry_vars["t"].set("2")
                self.entry_vars["g"].set("9.81")

        self.solve_problem()

    def _select_target_by_code(self, code: str) -> None:
        spec = VARIABLES_CATALOG.get(code)
        if not spec:
            return
        target_display = f"{spec.symbol} ({spec.name})"
        values = list(self.cmb_target["values"])
        for idx, val in enumerate(values):
            if spec.symbol in val:
                self.cmb_target.current(idx)
                self._on_target_changed()
                break

    def clear_fields(self) -> None:
        for code, var in self.entry_vars.items():
            if code == "g" and self.scenario_var.get() == "CAIDA_LIBRE":
                var.set("9.81")
            else:
                var.set("")
        self._display_welcome_message()

    def solve_problem(self) -> None:
        """Recolecta los datos, ejecuta el motor analítico y formatea la solución."""
        scenario = self.scenario_var.get()

        # Determinar código de la incógnita
        target_str = self.target_var.get()
        target_symbol = target_str.split(" ")[0].strip()
        target_code = None
        for c, spec in VARIABLES_CATALOG.items():
            if spec.symbol == target_symbol:
                target_code = c
                break
        if not target_code:
            target_code = "v"

        target_unit = self.target_unit_var.get().strip()

        # Recolectar variables conocidas
        known_inputs: Dict[str, Tuple[float, str]] = {}
        for code, var in self.entry_vars.items():
            val_str = var.get().strip()
            if not val_str:
                continue
            try:
                val_num = float(val_str)
                unit_str = self.unit_vars[code].get().strip()
                known_inputs[code] = (val_num, unit_str)
            except ValueError:
                messagebox.showerror("Error de Entrada", f"El valor '{val_str}' para {code} no es un número válido.")
                return

        if not known_inputs:
            messagebox.showinfo("Aviso", "Por favor ingrese al menos 2 datos conocidos para resolver.")
            return

        # Resolver mediante el motor cinemático
        try:
            solution = KinematicsSolver.solve(
                scenario=scenario,
                known_inputs=known_inputs,
                target_code=target_code,
                target_unit=target_unit
            )
            self._render_solution(solution)
        except Exception as err:
            messagebox.showerror("Error de Cálculo", f"Ocurrió un error al procesar el ejercicio:\n{err}")

    def _render_solution(self, sol: StepByStepSolution) -> None:
        """Renderiza la solución completa con diseño limpio y tipografía científica."""
        self.txt_solution.config(state="normal")
        self.txt_solution.delete("1.0", tk.END)

        # Encabezado del reporte
        self.txt_solution.insert(tk.END, "═══════════════════════════════════════════════════════════════════════════\n", "notes")
        self.txt_solution.insert(tk.END, f"  RESOLUCIÓN PEDAGÓGICA PASO A PASO: {sol.scenario.replace('_', ' ')}\n", "title")
        self.txt_solution.insert(tk.END, "═══════════════════════════════════════════════════════════════════════════\n\n", "notes")

        # PASO 1: DATOS CONOCIDOS
        self.txt_solution.insert(tk.END, "PASO 1. IDENTIFICACIÓN DE DATOS CONOCIDOS Y CONVERSIÓN AL SI\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        if sol.known_inputs:
            for inp in sol.known_inputs:
                spec = VARIABLES_CATALOG.get(inp.code)
                sym = spec.symbol if spec else inp.code
                name = spec.name if spec else inp.code
                self.txt_solution.insert(tk.END, f"  • {name} ({sym}): ", "subtitle")
                self.txt_solution.insert(tk.END, f"{inp.value:g} {inp.unit}")
                if inp.conversion_note and "no requiere" not in inp.conversion_note:
                    self.txt_solution.insert(tk.END, f"  ➜  Conversión: {inp.conversion_note}\n", "notes")
                else:
                    self.txt_solution.insert(tk.END, f"  (= {inp.si_value:g} {spec.default_unit if spec else ''})\n")
        else:
            self.txt_solution.insert(tk.END, "  No se ingresaron datos conocidos.\n")
        self.txt_solution.insert(tk.END, "\n")

        # PASO 2: VARIABLE INCÓGNITA
        self.txt_solution.insert(tk.END, "PASO 2. VARIABLE DESCONOCIDA (INCÓGNITA)\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        self.txt_solution.insert(tk.END, f"  • Incógnita: ", "subtitle")
        self.txt_solution.insert(tk.END, f"{sol.target_spec.name} ")
        self.txt_solution.insert(tk.END, f"[{sol.target_spec.symbol}]\n", "formula")
        self.txt_solution.insert(tk.END, f"  • Unidad destino solicitada: {sol.target_unit}\n\n")

        # SI NO ES RESOLUBLE -> DIAGNÓSTICO
        if not sol.is_solvable:
            self.txt_solution.insert(tk.END, "❌ NO ES POSIBLE RESOLVER CON LOS DATOS SUMINISTRADOS\n", "error_box")
            self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
            self.txt_solution.insert(tk.END, f"{sol.diagnostic_error}\n\n", "highlight")
            self.txt_solution.config(state="disabled")
            return

        # PASO 3: ECUACIÓN SELECCIONADA Y JUSTIFICACIÓN
        self.txt_solution.insert(tk.END, "PASO 3. ECUACIÓN CINEMÁTICA SELECCIONADA Y JUSTIFICACIÓN\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        self.txt_solution.insert(tk.END, f"  Ecuación elegida: {sol.equation_name}\n", "subtitle")
        self.txt_solution.insert(tk.END, f"  Fórmula:  {sol.equation_formula}\n", "formula")
        self.txt_solution.insert(tk.END, f"  Justificación: {sol.justification}\n\n", "notes")

        # PASO 4: DESPEJE ALGEBRAICO
        self.txt_solution.insert(tk.END, "PASO 4. DESPEJE ALGEBRAICO DE LA INCÓGNITA\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        for step in sol.derivation_steps:
            self.txt_solution.insert(tk.END, f"  {step}\n")
        self.txt_solution.insert(tk.END, "\n")

        # PASO 5: SUSTITUCIÓN DE VALORES
        self.txt_solution.insert(tk.END, "PASO 5. SUSTITUCIÓN DE LOS VALORES EN UNIDADES DEL SI\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        self.txt_solution.insert(tk.END, f"  {sol.substitution_text}\n\n", "formula")

        # PASO 6: OPERACIONES MATEMÁTICAS INTERMEDIAS
        self.txt_solution.insert(tk.END, "PASO 6. OPERACIONES MATEMÁTICAS PASO A PASO\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        for cstep in sol.calculation_steps:
            self.txt_solution.insert(tk.END, f"  • {cstep}\n")
        self.txt_solution.insert(tk.END, "\n")

        # PASO 7: RESULTADO FINAL
        self.txt_solution.insert(tk.END, "PASO 7. RESULTADO FINAL\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        res_si_str = f"{sol.final_value_si:+.4g} {sol.final_unit_si}"
        self.txt_solution.insert(tk.END, f"  Resultado en el SI: ", "subtitle")
        self.txt_solution.insert(tk.END, f"{sol.target_spec.symbol} = {res_si_str}\n", "success_box")

        if sol.target_unit != sol.final_unit_si and sol.final_value_target is not None:
            res_target_str = f"{sol.final_value_target:+.4g} {sol.target_unit}"
            self.txt_solution.insert(tk.END, f"  Resultado en unidad solicitada: ", "subtitle")
            self.txt_solution.insert(tk.END, f"{sol.target_spec.symbol} = {res_target_str}\n", "highlight")
        self.txt_solution.insert(tk.END, "\n")

        # PASO 8: INTERPRETACIÓN FÍSICA
        self.txt_solution.insert(tk.END, "PASO 8. INTERPRETACIÓN FÍSICA DEL RESULTADO\n", "step_header")
        self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
        self.txt_solution.insert(tk.END, f"  {sol.physical_interpretation}\n\n")

        # PASO 9: ANÁLISIS DE SOLUCIONES MÚLTIPLES O NOTAS ESPECIALES
        if sol.multiple_solutions_note:
            self.txt_solution.insert(tk.END, "PASO 9. ANÁLISIS DE RAÍCES CUADRÁTICAS Y CONDICIONES DE FRONTERA\n", "step_header")
            self.txt_solution.insert(tk.END, "---------------------------------------------------------------------------\n", "notes")
            self.txt_solution.insert(tk.END, f"  {sol.multiple_solutions_note}\n\n", "notes")

        self.txt_solution.insert(tk.END, "═══════════════════════════════════════════════════════════════════════════\n", "notes")
        self.txt_solution.config(state="disabled")

    def copy_solution_to_clipboard(self) -> None:
        try:
            content = self.txt_solution.get("1.0", tk.END).strip()
            if not content or "BIENVENIDO" in content:
                messagebox.showinfo("Aviso", "No hay ninguna solución calculada para copiar.")
                return
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copiado", "¡La solución paso a paso ha sido copiada al portapapeles con éxito!")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar al portapapeles: {e}")
