from __future__ import annotations

import tkinter as tk

from .controllers import RepairController


class RepairApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Resim Onarım Aracı - Versiyon: 2.3.0 (Pro)")
        self.geometry("1100x1000")

        self.controller = RepairController(self)
        self.protocol("WM_DELETE_WINDOW", self.controller.on_closing)


def run_app() -> None:
    app = RepairApp()
    app.mainloop()