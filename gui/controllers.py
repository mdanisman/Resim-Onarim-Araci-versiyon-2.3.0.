from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import tkinter as tk
from tkinter import filedialog, messagebox

from core.jpeg_repair import build_header_library_from_folder
from core.repair_engine import pick_best_output
from utils import DEST_SUBFOLDER_NAME, detect_ffmpeg, is_image_file
from logging_utils import create_logger

from .helpers import LogHelper, PreviewHelper
from .services import ProcessingOptions, RepairService
from .widgets import CommandBindings, WidgetRefs, build_ui

MAX_PREVIEW_SIZE = (420, 320)
DEFAULT_HEADER_SIZE = "16 KB"
DEFAULT_FFMPEG_QUALITY = "Normal"
OUTPUT_MODE_SAME = "same"
OUTPUT_MODE_CUSTOM = "custom"


@dataclass
class AppVariables:
    output_mode: tk.StringVar
    use_header: tk.BooleanVar
    use_ffmpeg: tk.BooleanVar
    use_pillow: tk.BooleanVar
    use_png_roundtrip: tk.BooleanVar
    use_marker: tk.BooleanVar
    stop_on_first_success: tk.BooleanVar
    try_all_files: tk.BooleanVar
    ffmpeg_quality: tk.StringVar
    header_size_choice: tk.StringVar
    keep_apps: tk.BooleanVar
    keep_com: tk.BooleanVar
    use_embed_scan: tk.BooleanVar
    use_partial_top: tk.BooleanVar
    use_exif_thumb: tk.BooleanVar
    use_png_crc: tk.BooleanVar
    exif_thumb_upscale: tk.BooleanVar
    png_crc_skip_ancillary: tk.BooleanVar

    # AI JPEG Patch Reconstruction değişkenleri
    use_ai_patch: tk.BooleanVar
    ai_use_realesrgan: tk.BooleanVar
    ai_use_gfpgan: tk.BooleanVar
    ai_use_inpaint: tk.BooleanVar
    ai_damage_threshold: tk.DoubleVar

    def as_dict(self) -> Dict[str, tk.Variable]:
        return {
            "output_mode": self.output_mode,
            "use_header": self.use_header,
            "use_ffmpeg": self.use_ffmpeg,
            "use_pillow": self.use_pillow,
            "use_png_roundtrip": self.use_png_roundtrip,
            "use_marker": self.use_marker,
            "stop_on_first_success": self.stop_on_first_success,
            "try_all_files": self.try_all_files,
            "ffmpeg_quality": self.ffmpeg_quality,
            "header_size_choice": self.header_size_choice,
            "keep_apps": self.keep_apps,
            "keep_com": self.keep_com,
            "use_embed_scan": self.use_embed_scan,
            "use_partial_top": self.use_partial_top,
            "use_exif_thumb": self.use_exif_thumb,
            "use_png_crc": self.use_png_crc,
            "exif_thumb_upscale": self.exif_thumb_upscale,
            "png_crc_skip_ancillary": self.png_crc_skip_ancillary,
            # AI alanları
            "use_ai_patch": self.use_ai_patch,
            "ai_use_realesrgan": self.ai_use_realesrgan,
            "ai_use_gfpgan": self.ai_use_gfpgan,
            "ai_use_inpaint": self.ai_use_inpaint,
            "ai_damage_threshold": self.ai_damage_threshold,
        }


class RepairController:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.ffmpeg_cmd: Optional[str] = detect_ffmpeg()
        self.ffmpeg_available: bool = self.ffmpeg_cmd is not None

        self.operation_id = f"GUI-{uuid4()}"
        self.logger = create_logger(operation_id=self.operation_id, step="gui")

        self.progress_var = tk.DoubleVar()
        self.stats_total = tk.IntVar(value=0)
        self.stats_fixed = tk.IntVar(value=0)
        self.stats_failed = tk.IntVar(value=0)
        self.stats_processed = tk.IntVar(value=0)

        self.variables = self._init_settings()

        commands = CommandBindings(
            process_single=self.process_single,
            process_folder=self.process_folder,
            cancel_processing=self.cancel_processing,
            select_output_dir=self.select_output_dir,
            select_header_file=self.select_header_file,
            select_header_library=self.select_header_library,
            save_log=self.save_log,
            open_preview_window=self.open_preview_window,
            on_use_header_toggle=self.on_use_header_toggle,
        )

        self.widgets: WidgetRefs = build_ui(
            root,
            self.variables.as_dict(),
            commands,
            self.progress_var,
            self.stats_total,
            self.stats_fixed,
            self.stats_failed,
            self.stats_processed,
            self.ffmpeg_available,
            self.ffmpeg_cmd,
            OUTPUT_MODE_SAME,
        )

        self.log_helper = LogHelper(self.widgets.txt_log, logger=self.logger)
        self.preview_helper = PreviewHelper(MAX_PREVIEW_SIZE)
        self.preview_helper.set_inline_targets(
            self.widgets.preview_original_label,
            self.widgets.preview_repaired_label,
            self.widgets.preview_info_label,
        )

        self.service = RepairService(
            on_file_processed=self._schedule_file_processed,
            on_finished=self._schedule_finished,
            on_error=self._schedule_error,
        )

        self.ref_header_bytes: Optional[bytes] = None
        self.ref_header_path: Optional[Path] = None
        self.header_library: List[bytes] = []
        self.header_library_folder: Optional[Path] = None
        self.last_output_dir: Optional[Path] = None
        self.custom_output_dir: Optional[Path] = None
        self.start_time: Optional[float] = None

        default_msg = (
            "Uygulama başlatıldı.\n"
            "- Sol panelden tek resim veya klasör seçebilirsiniz.\n"
            "- Sağ panelden onarım yöntemlerini ve ayarları yapılandırabilirsiniz.\n"
            "- Alt bölümde ilerleme, istatistik ve ayrıntılı günlükleri takip edebilirsiniz."
        )
        self.log(default_msg, color="blue", extra={"step": "ui-init", "result": "ready"})
        ffmpeg_status = "available" if self.ffmpeg_available else "missing"
        self.log(
            f"FFmpeg durumu: {ffmpeg_status} ({self.ffmpeg_cmd or 'komut bulunamadı'})",
            color="orange" if not self.ffmpeg_available else "blue",
            extra={"step": "ffmpeg-check", "method": "ffmpeg", "result": ffmpeg_status},
        )
        self.on_use_header_toggle()

    # --------------------------------------
    # Logging helpers
    # --------------------------------------
    def log(self, message: str, color: str = "black", extra: Optional[dict] = None) -> None:
        self.log_helper.log(message, color=color, extra=extra)

    # --------------------------------------
    # Settings
    # --------------------------------------
    def _init_settings(self) -> AppVariables:
        return AppVariables(
            output_mode=tk.StringVar(value=OUTPUT_MODE_SAME),
            use_header=tk.BooleanVar(value=False),
            use_ffmpeg=tk.BooleanVar(value=self.ffmpeg_available),
            use_pillow=tk.BooleanVar(value=True),
            use_png_roundtrip=tk.BooleanVar(value=True),
            use_marker=tk.BooleanVar(value=True),
            stop_on_first_success=tk.BooleanVar(value=False),
            try_all_files=tk.BooleanVar(value=False),
            ffmpeg_quality=tk.StringVar(value=DEFAULT_FFMPEG_QUALITY),
            header_size_choice=tk.StringVar(value=DEFAULT_HEADER_SIZE),
            keep_apps=tk.BooleanVar(value=True),
            keep_com=tk.BooleanVar(value=True),
            use_embed_scan=tk.BooleanVar(value=True),
            use_partial_top=tk.BooleanVar(value=True),
            use_exif_thumb=tk.BooleanVar(value=True),
            use_png_crc=tk.BooleanVar(value=True),
            exif_thumb_upscale=tk.BooleanVar(value=False),
            png_crc_skip_ancillary=tk.BooleanVar(value=False),
            # AI varsayılanları
            use_ai_patch=tk.BooleanVar(value=False),
            ai_use_realesrgan=tk.BooleanVar(value=True),
            ai_use_gfpgan=tk.BooleanVar(value=False),
            ai_use_inpaint=tk.BooleanVar(value=False),
            ai_damage_threshold=tk.DoubleVar(value=0.7),
        )

    # --------------------------------------
    # Command handlers
    # --------------------------------------
    def process_single(self) -> None:
        if self._is_processing():
            messagebox.showwarning("Uyarı", "Zaten devam eden bir işlem var.")
            return

        file_path = filedialog.askopenfilename(
            title="Onarılacak resmi seçin",
            filetypes=[
                ("Resim Dosyaları", "*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff;*.webp"),
                ("Tüm Dosyalar", "*.*"),
            ],
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not file_path:
            return

        path = Path(file_path)
        if not is_image_file(path, check_content=True):
            messagebox.showerror("Hata", "Seçilen dosya geçerli bir resim dosyası değil.")
            self.log(
                f"Geçersiz resim dosyası nedeniyle atlandı: {path}",
                color="orange",
                extra={"step": "input-validate", "file": str(path), "result": "skipped"},
            )
            return

        self._start_processing([path])

    def process_folder(self) -> None:
        if self._is_processing():
            messagebox.showwarning("Uyarı", "Zaten devam eden bir işlem var.")
            return

        folder = filedialog.askdirectory(
            title="Onarılacak resimlerin bulunduğu klasörü seçin",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return

        root_path = Path(folder)
        files = list(self._iter_images(root_path))
        if not files:
            messagebox.showinfo("Bilgi", "Seçilen klasörde onarılabilecek resim dosyası bulunamadı.")
            self.log(
                f"Klasörde uygun resim bulunamadı: {root_path}",
                color="orange",
                extra={"step": "input-scan", "file": str(root_path), "result": "skipped"},
            )
            return

        self._start_processing(files)

    def cancel_processing(self) -> None:
        self.service.cancel()
        if self._is_processing():
            self.log(
                "İşlem iptal isteği gönderildi. Devam eden dosya tamamlanınca duracak.",
                color="orange",
                extra={"step": "cancel", "result": "requested"},
            )

    def select_output_dir(self) -> None:
        folder = filedialog.askdirectory(
            title="Özel çıktı klasörü seç",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return
        self.custom_output_dir = Path(folder)
        self.widgets.lbl_output_dir.configure(text=str(self.custom_output_dir), foreground="black")
        self.log(f"Özel çıktı klasörü seçildi: {self.custom_output_dir}", color="blue")

    def select_header_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Referans JPEG dosyası seç",
            filetypes=[("JPEG Dosyaları", "*.jpg;*.jpeg"), ("Tüm Dosyalar", "*.*")],
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not file_path:
            return

        header_path = Path(file_path)
        try:
            with header_path.open("rb") as f:
                header_size = 64 * 1024
                self.ref_header_bytes = f.read(header_size)
            self.ref_header_path = header_path
            self.widgets.lbl_header_file.configure(text=str(header_path.name), foreground="black")
            self.log(f"Referans header dosyası seçildi: {header_path}", color="blue")
        except Exception as exc:
            messagebox.showerror("Hata", f"Header dosyası okunamadı: {exc}")
            self.log(f"Header dosyası okunamadı: {exc}", color="red")

    def select_header_library(self) -> None:
        folder = filedialog.askdirectory(
            title="Header kütüphanesi klasörü seç",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return

        lib_path = Path(folder)
        try:
            self.header_library = build_header_library_from_folder(lib_path)
            self.header_library_folder = lib_path
            self.widgets.lbl_header_lib.configure(
                text=f"{lib_path.name} ({len(self.header_library)} header)",
                foreground="black",
            )
            self.log(
                f"Header kütüphanesi klasörü seçildi: {lib_path} ({len(self.header_library)} header okundu)",
                color="blue",
            )
        except Exception as exc:
            messagebox.showerror("Hata", f"Header kütüphanesi okunamadı: {exc}")
            self.log(f"Header kütüphanesi okunamadı: {exc}", color="red")

    def on_use_header_toggle(self) -> None:
        state = "normal" if self.variables.use_header.get() else "disabled"
        self.widgets.cmb_header_size.configure(state=state)

    def save_log(self) -> None:
        if not self.log_helper.structured_logs:
            messagebox.showinfo("Bilgi", "Kaydedilecek günlük bulunmuyor.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Günlükleri Kaydet",
            initialdir=self._get_last_dir_or_cwd(),
            defaultextension=".txt",
            filetypes=[
                ("Metin Dosyası", "*.txt"),
                ("CSV Dosyası", "*.csv"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if not file_path:
            return

        out_path = Path(file_path)
        try:
            self.log_helper.save_to_path(out_path)
            messagebox.showinfo("Başarılı", f"Günlükler kaydedildi:\n{out_path}")
        except Exception as exc:
            messagebox.showerror("Hata", f"Günlük kaydedilemedi: {exc}")

    def open_preview_window(self) -> None:
        last = self.service.last_processed_file
        if not last:
            messagebox.showinfo(
                "Bilgi",
                "Henüz işlenmiş bir dosya yok. Önce tek bir dosya veya klasör işlemi başlatın.",
            )
            return

        best = pick_best_output(self.service.successful_outputs.get(last, []))
        self.preview_helper.open_preview_window(self.root, last, best)

    # --------------------------------------
    # Processing helpers
    # --------------------------------------
    def _start_processing(self, files: List[Path]) -> None:
        total_files = len(files)
        self.service.cancel_requested = False

        self.stats_total.set(total_files)
        self.stats_fixed.set(0)
        self.stats_failed.set(0)
        self.stats_processed.set(0)
        self.progress_var.set(0.0)
        self.service.successful_outputs.clear()
        self.start_time = time.perf_counter()

        self.widgets.btn_cancel.config(state="normal")
        self.widgets.btn_process_single.config(state="disabled")
        self.widgets.btn_process_folder.config(state="disabled")

        self.log(
            f"Toplam {total_files} dosya için onarım işlemi başlatıldı.",
            color="blue",
            extra={"step": "process-start", "result": "running"},
        )

        options = self._build_processing_options()
        self.service.start(files, options)

    def _build_processing_options(self) -> ProcessingOptions:
        size_map = {
            "8 KB": 8 * 1024,
            "16 KB": 16 * 1024,
            "32 KB": 32 * 1024,
            "64 KB": 64 * 1024,
        }
        header_size = size_map.get(self.variables.header_size_choice.get(), 16 * 1024)

        if self.variables.use_ffmpeg.get() and not self.ffmpeg_available:
            self.log(
                "FFmpeg seçili ancak sistemde bulunamadı, devre dışı bırakılıyor.",
                color="orange",
                extra={"step": "ffmpeg-check", "method": "ffmpeg", "result": "skipped"},
            )

        return ProcessingOptions(
            use_pillow=self.variables.use_pillow.get(),
            use_png_roundtrip=self.variables.use_png_roundtrip.get(),
            use_header=self.variables.use_header.get(),
            use_marker=self.variables.use_marker.get(),
            use_ffmpeg=self.variables.use_ffmpeg.get() and self.ffmpeg_available,
            stop_on_first_success=self.variables.stop_on_first_success.get(),
            use_embed_scan=self.variables.use_embed_scan.get(),
            use_partial_top=self.variables.use_partial_top.get(),
            use_exif_thumb=self.variables.use_exif_thumb.get(),
            use_png_crc=self.variables.use_png_crc.get(),
            exif_thumb_upscale=self.variables.exif_thumb_upscale.get(),
            png_crc_skip_ancillary=self.variables.png_crc_skip_ancillary.get(),
            header_size=header_size,
            ffmpeg_cmd=self.ffmpeg_cmd,
            ffmpeg_quality=self.variables.ffmpeg_quality.get(),
            ref_header_bytes=self.ref_header_bytes,
            header_library=self.header_library if self.header_library else None,
            keep_apps=self.variables.keep_apps.get(),
            keep_com=self.variables.keep_com.get(),
            resolve_output_dir=self._resolve_output_dir,
            log=self.log,
            # AI seçenekleri
            use_ai_patch=self.variables.use_ai_patch.get(),
            ai_damage_threshold=float(self.variables.ai_damage_threshold.get()),
            ai_use_realesrgan=self.variables.ai_use_realesrgan.get(),
            ai_use_gfpgan=self.variables.ai_use_gfpgan.get(),
            ai_use_inpaint=self.variables.ai_use_inpaint.get(),
            ai_external_cmd=None,
        )

    def _schedule_file_processed(self, original: Path, outputs: List[Path]) -> None:
        self.root.after(0, lambda: self._handle_file_processed(original, outputs))

    def _handle_file_processed(self, original: Path, outputs: List[Path]) -> None:
        best = pick_best_output(outputs) if outputs else None
        self.service.last_processed_file = original
        self.service.successful_outputs[original] = outputs
        self.preview_helper.update_inline(original, best)

        if best:
            self.stats_fixed.set(self.stats_fixed.get() + 1)
        else:
            self.stats_failed.set(self.stats_failed.get() + 1)

        self.stats_processed.set(self.stats_processed.get() + 1)
        processed = self.stats_processed.get()
        total = max(self.stats_total.get(), 1)
        self.progress_var.set((processed / total) * 100)

    def _schedule_finished(self) -> None:
        self.root.after(0, self._on_processing_finished)

    def _schedule_error(self, exc: Exception) -> None:
        self.root.after(0, lambda: self._on_processing_error(exc))

    def _on_processing_finished(self) -> None:
        self.widgets.btn_cancel.config(state="disabled")
        self.widgets.btn_process_single.config(state="normal")
        self.widgets.btn_process_folder.config(state="normal")

        total = self.stats_total.get()
        fixed = self.stats_fixed.get()
        failed = self.stats_failed.get()
        duration_ms = None
        if self.start_time is not None:
            duration_ms = int((time.perf_counter() - self.start_time) * 1000)
            self.start_time = None
        self.log(
            f"İşlem tamamlandı. Toplam: {total}, Onarılan: {fixed}, Başarısız: {failed}",
            color="blue",
            extra={
                "step": "process-end",
                "result": "finished",
                "duration_ms": duration_ms if duration_ms is not None else "-",
            },
        )

        messagebox.showinfo(
            "Tamamlandı",
            f"Onarım işlemi tamamlandı.\nToplam: {total}\nOnarılan: {fixed}\nBaşarısız: {failed}",
        )

   def _on_processing_error(self, exc: Exception) -> None:
        messagebox.showerror(
            "Hata",
            f"İşleme sırasında beklenmeyen hata oluştu:\n{exc}",
        )
        self.log(
            f"Beklenmeyen hata: {exc}",
            color="red",
            extra={"step": "process-error", "result": "failed"},
        )␊
        self._on_processing_finished()

    # --------------------------------------
    # Utils
    # --------------------------------------
    def _iter_images(self, root_path: Path):
        use_content_check = self.variables.try_all_files.get()
        for dirpath, _, filenames in os.walk(root_path):
            dpath = Path(dirpath)
            for name in filenames:
                p = dpath / name
                if is_image_file(p, check_content=use_content_check):
                    yield p
                else:
                    self.log(
                        f"Girdi taramasında atlandı (resim değil veya bozuk): {p}",
                        color="orange",
                        extra={"step": "input-scan", "file": str(p), "result": "skipped"},
                    )

    def _resolve_output_dir(self, input_path: Path) -> Optional[Path]:
        try:
            if self.variables.output_mode.get() == OUTPUT_MODE_CUSTOM:
                if not self.custom_output_dir:
                    messagebox.showerror("Hata", "Özel çıktı klasörü seçilmedi.")
                    return None
                out_dir = self.custom_output_dir / DEST_SUBFOLDER_NAME
            else:
                out_dir = input_path.parent / DEST_SUBFOLDER_NAME

            out_dir.mkdir(parents=True, exist_ok=True)
            self.last_output_dir = out_dir
            return out_dir
        except Exception as exc:
            self.log(f"Çıktı klasörü oluşturulamadı: {exc}", color="red")
            return None

    def _get_last_dir_or_cwd(self) -> str:
        if self.last_output_dir is not None:
            return str(self.last_output_dir)
        return os.getcwd()

    def _is_processing(self) -> bool:
        thread = self.service.processing_thread
        return bool(thread and thread.is_alive())

    def on_closing(self) -> None:
        if self._is_processing():
            if not messagebox.askyesno(
                "Kapat",
                "Devam eden bir işlem var. Yine de çıkmak istiyor musunuz?",
            ):
                return
        self.root.destroy()
