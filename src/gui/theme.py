"""
Módulo de Estilos y Paleta de Colores para la Interfaz Gráfica.

Define una estética moderna, limpia y de contraste óptimo inspirada en entornos
de simulación científica y tableros de ingeniería modernos.
"""

import tkinter as tk
from tkinter import ttk


class Theme:
    """Constantes de color, fuentes y estilos para la aplicación."""

    # Paleta principal (Dark Slate Modern Theme)
    BG_DARK = "#0f172a"        # Fondo principal ventana (Slate 900)
    BG_CARD = "#1e293b"        # Fondo tarjetas y contenedores (Slate 800)
    BG_CARD_LIGHT = "#334155"  # Fondo secundario elementos (Slate 700)
    BG_CANVAS = "#090d16"      # Fondo para la pista y canvas

    # Colores de acento y estado
    PRIMARY = "#38bdf8"        # Celeste / Cyan brillante (Sky 400)
    PRIMARY_HOVER = "#0284c7"  # Cyan oscuro
    SUCCESS = "#22c55e"        # Verde esmeralda (Green 500)
    SUCCESS_HOVER = "#16a34a"  # Verde oscuro
    WARNING = "#f59e0b"        # Ámbar / Naranja (Amber 500)
    WARNING_HOVER = "#d97706"  # Ámbar oscuro
    DANGER = "#ef4444"         # Rojo (Red 500)
    DANGER_HOVER = "#dc2626"   # Rojo oscuro
    ACCENT = "#818cf8"         # Índigo suave (Indigo 400)

    # Texto
    TEXT_LIGHT = "#f8fafc"     # Blanco brillante
    TEXT_MUTED = "#94a3b8"     # Gris azulado tenue
    TEXT_DARK = "#0f172a"      # Oscuro para contrastar en fondos claros

    # Elementos de la pista
    TRACK_SURFACE = "#1e293b"
    TRACK_BORDER = "#475569"
    TRACK_MARK_MAJOR = "#f8fafc"
    TRACK_MARK_MINOR = "#64748b"
    ORIGIN_MARKER = "#38bdf8"
    CAR_COLOR = "#0ea5e9"
    CAR_ACCENT = "#38bdf8"
    CAR_WHEEL = "#020617"
    CAR_RIM = "#94a3b8"
    VECTOR_ARROW = "#ec4899"   # Rosa brillante para vector velocidad
    DISPLACEMENT_BAR = "#34d399" # Verde agua para vector desplazamiento

    # Fuentes
    FONT_FAMILY = "DejaVu Sans"
    FONT_TITLE = (FONT_FAMILY, 15, "bold")
    FONT_SUBTITLE = (FONT_FAMILY, 11, "bold")
    FONT_BODY = (FONT_FAMILY, 10, "normal")
    FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
    FONT_MONO = ("DejaVu Sans Mono", 11, "bold")
    FONT_MONO_LARGE = ("DejaVu Sans Mono", 18, "bold")
    FONT_BADGE = (FONT_FAMILY, 9, "bold")

    @classmethod
    def apply_ttk_styles(cls, root: tk.Tk) -> None:
        """Configura los estilos de TTK para armonizar con el tema general."""
        style = ttk.Style(root)
        style.theme_use("clam")

        # Configuración base de TFrame
        style.configure("TFrame", background=cls.BG_DARK)
        style.configure("Card.TFrame", background=cls.BG_CARD)
        style.configure("CardLight.TFrame", background=cls.BG_CARD_LIGHT)

        # Configuración de TLabel
        style.configure(
            "TLabel",
            background=cls.BG_DARK,
            foreground=cls.TEXT_LIGHT,
            font=cls.FONT_BODY
        )
        style.configure(
            "Card.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT_LIGHT,
            font=cls.FONT_BODY
        )
        style.configure(
            "CardTitle.TLabel",
            background=cls.BG_CARD,
            foreground=cls.PRIMARY,
            font=cls.FONT_SUBTITLE
        )
        style.configure(
            "CardMuted.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT_MUTED,
            font=(cls.FONT_FAMILY, 9)
        )
        style.configure(
            "HeaderTitle.TLabel",
            background=cls.BG_DARK,
            foreground=cls.TEXT_LIGHT,
            font=cls.FONT_TITLE
        )
        style.configure(
            "HeaderSubtitle.TLabel",
            background=cls.BG_DARK,
            foreground=cls.PRIMARY,
            font=cls.FONT_BODY
        )

        # Configuración de TButton
        style.configure(
            "Primary.TButton",
            background=cls.PRIMARY,
            foreground=cls.TEXT_DARK,
            font=cls.FONT_BODY_BOLD,
            borderwidth=0,
            focuscolor=cls.PRIMARY_HOVER,
            padding=6
        )
        style.map(
            "Primary.TButton",
            background=[("active", cls.PRIMARY_HOVER), ("disabled", cls.BG_CARD_LIGHT)],
            foreground=[("disabled", cls.TEXT_MUTED)]
        )

        style.configure(
            "Success.TButton",
            background=cls.SUCCESS,
            foreground=cls.TEXT_DARK,
            font=cls.FONT_BODY_BOLD,
            borderwidth=0,
            padding=6
        )
        style.map(
            "Success.TButton",
            background=[("active", cls.SUCCESS_HOVER), ("disabled", cls.BG_CARD_LIGHT)],
            foreground=[("disabled", cls.TEXT_MUTED)]
        )

        style.configure(
            "Warning.TButton",
            background=cls.WARNING,
            foreground=cls.TEXT_DARK,
            font=cls.FONT_BODY_BOLD,
            borderwidth=0,
            padding=6
        )
        style.map(
            "Warning.TButton",
            background=[("active", cls.WARNING_HOVER), ("disabled", cls.BG_CARD_LIGHT)],
            foreground=[("disabled", cls.TEXT_MUTED)]
        )

        style.configure(
            "Danger.TButton",
            background=cls.DANGER,
            foreground=cls.TEXT_LIGHT,
            font=cls.FONT_BODY_BOLD,
            borderwidth=0,
            padding=6
        )
        style.map(
            "Danger.TButton",
            background=[("active", cls.DANGER_HOVER), ("disabled", cls.BG_CARD_LIGHT)],
            foreground=[("disabled", cls.TEXT_MUTED)]
        )

        style.configure(
            "Secondary.TButton",
            background=cls.BG_CARD_LIGHT,
            foreground=cls.TEXT_LIGHT,
            font=cls.FONT_BODY,
            borderwidth=0,
            padding=6
        )
        style.map(
            "Secondary.TButton",
            background=[("active", cls.PRIMARY_HOVER)],
            foreground=[("disabled", cls.TEXT_MUTED)]
        )

        # Configuración de Notebook (Pestañas)
        style.configure(
            "TNotebook",
            background=cls.BG_DARK,
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=cls.BG_CARD,
            foreground=cls.TEXT_MUTED,
            font=cls.FONT_BODY_BOLD,
            padding=[12, 6]
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", cls.BG_CARD_LIGHT)],
            foreground=[("selected", cls.PRIMARY)]
        )

        # TCombobox & TEntry
        style.configure(
            "TCombobox",
            fieldbackground=cls.BG_CARD_LIGHT,
            background=cls.BG_CARD,
            foreground=cls.TEXT_LIGHT,
            darkcolor=cls.BG_CARD,
            lightcolor=cls.BG_CARD
        )
        style.configure(
            "TEntry",
            fieldbackground=cls.BG_CARD_LIGHT,
            foreground=cls.TEXT_LIGHT,
            insertcolor=cls.TEXT_LIGHT
        )
        style.configure(
            "TScale",
            background=cls.BG_CARD,
            troughcolor=cls.BG_DARK
        )
