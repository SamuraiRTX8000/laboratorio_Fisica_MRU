#!/usr/bin/env python3
"""
Punto de Entrada Principal - Laboratorio Virtual de Cinemática (MRU).

Simulador interactivo para el estudio del Movimiento Rectilíneo Uniforme en Física I,
diseñado para estudiantes de Ingeniería de Sistemas.

Uso:
    python3 main.py
"""

import sys
import tkinter as tk
from src.gui.main_window import MainWindow


def main() -> None:
    """Inicializa y ejecuta la aplicación de escritorio del laboratorio virtual."""
    root = tk.Tk()

    # Configuración de propiedades de la ventana para sistemas X11/Wayland/Windows
    try:
        root.tk.call('tk', 'scaling', 1.0)
    except Exception:
        pass

    app = MainWindow(root)

    def on_closing():
        try:
            if app.controller:
                app.controller._cancel_scheduled_frame()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
