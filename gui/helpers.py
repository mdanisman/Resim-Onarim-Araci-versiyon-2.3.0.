from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk


@dataclass
class LogEntry:
    time: str
    message: str
    color: str = "black"


@dataclass
class LogHelper:
    text_widget: scrolledtext.ScrolledText
    structured_logs: List[LogEntry] = field(default_factory=list)

    def log(self, message: str, color: str = "black") -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        def _append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", line, color)
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")

        try:
            self.text_widget.after(0, _append)
        except Exception:
            _append()

        self.structured_logs.append(LogEntry(time=timestamp, message=message, color=color))

    def save_to_path(self, output_path: Path) -> None:
        if output_path.suffix.lower() == ".csv":
            import csv

            with output_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["time", "color", "message"])
                for item in self.structured_logs:
                    writer.writerow([item.time, item.color, item.message])
        else:
            with output_path.open("w", encoding="utf-8") as f:
                for item in self.structured_logs:
                    f.write(f"[{item.time}] ({item.color}) {item.message}\n")


class PreviewHelper:
    def __init__(self, max_size: tuple[int, int]):
        self.max_size = max_size
        self._preview_images: List[ImageTk.PhotoImage] = []
        self.preview_original_label: Optional[ttk.Label] = None
        self.preview_repaired_label: Optional[ttk.Label] = None
        self.preview_info_label: Optional[ttk.Label] = None

    def set_inline_targets(
        self,
        original_label: ttk.Label,
        repaired_label: ttk.Label,
        info_label: ttk.Label,
    ) -> None:
        self.preview_original_label = original_label
        self.preview_repaired_label = repaired_label
        self.preview_info_label = info_label

    def _create_preview_image(self, path: Path) -> Optional[ImageTk.PhotoImage]:
        try:
            with Image.open(path) as im:
                im.load()
                im.thumbnail(self.max_size)
                return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def update_inline(self, original: Path, best_output: Optional[Path]) -> None:
        if not (self.preview_original_label and self.preview_repaired_label and self.preview_info_label):
            return

        self._preview_images.clear()

        if original.exists():
            pi = self._create_preview_image(original)
            if pi:
                self.preview_original_label.configure(image=pi, text="")
                self._preview_images.append(pi)
            else:
                self.preview_original_label.configure(
                    image="",
                    text="Orijinal önizleme yüklenemedi.",
                )

        if best_output and best_output.exists():
            pr = self._create_preview_image(best_output)
            if pr:
                self.preview_repaired_label.configure(image=pr, text="")
                self._preview_images.append(pr)
            else:
                self.preview_repaired_label.configure(
                    image="",
                    text="Onarılan önizleme yüklenemedi.",
                )
        else:
            self.preview_repaired_label.configure(
                image="",
                text="Henüz başarılı bir onarım yok.",
            )

        if best_output and best_output.exists():
            try:
                size_str = f"{best_output.stat().st_size / 1024:.1f} KB"
                with Image.open(best_output) as im:
                    w, h = im.size
                self.preview_info_label.configure(
                    text=(
                        f"Son işlenen dosya: {original.name}\n"
                        f"En iyi çıktı: {best_output.name} ({w}x{h}, {size_str})"
                    )
                )
            except Exception:
                self.preview_info_label.configure(
                    text=(
                        f"Son işlenen dosya: {original.name}\n"
                        f"En iyi çıktı: {best_output.name}"
                    )
                )
        else:
            self.preview_info_label.configure(
                text=(
                    f"Son işlenen dosya: {original.name}\n"
                    f"Henüz başarılı bir çıktı bulunamadı."
                )
            )

    def open_preview_window(self, root: tk.Tk, original: Path, best_output: Optional[Path]) -> None:
        if not best_output:
            messagebox.showinfo(
                "Bilgi",
                "Son işlenen dosya için başarılı bir çıktı bulunamadı.",
            )
            return

        win = tk.Toplevel(root)
        win.title("Onarılan Önizleme")
        win.geometry("900x500")

        main_frame = ttk.Frame(win, padding=10)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        orig_label = ttk.Label(main_frame, text="Orijinal", anchor="center")
        orig_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        fix_label = ttk.Label(main_frame, text="En İyi Onarım", anchor="center")
        fix_label.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        imgs: List[ImageTk.PhotoImage] = []

        po = self._create_preview_image(original)
        if po:
            orig_label.configure(image=po, text="")
            imgs.append(po)

        pf = self._create_preview_image(best_output)
        if pf:
            fix_label.configure(image=pf, text="")
            imgs.append(pf)

        win.preview_images = imgs  # type: ignore[attr-defined]