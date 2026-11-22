#!/usr/bin/env python3
"""
Punto de Entrada Principal - Laboratorio Virtual de Cinemática (MRU, MRUA y Caída Libre).

Simulador interactivo y asistente de resolución de problemas para el estudio
de la cinemática en Física I, diseñado con rigor pedagógico y computacional.

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
            if hasattr(app, "controller") and app.controller:
                app.controller._cancel_scheduled_frame()
            if hasattr(app, "mrua_controller") and app.mrua_controller:
                app.mrua_controller._cancel_scheduled_frame()
            if hasattr(app, "free_fall_controller") and app.free_fall_controller:
                app.free_fall_controller._cancel_scheduled_frame()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
