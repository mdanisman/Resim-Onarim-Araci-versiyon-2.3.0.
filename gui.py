from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk

from utils import is_image_file, detect_ffmpeg, DEST_SUBFOLDER_NAME
from core.repair_engine import repair_image_all_methods, pick_best_output
from core.jpeg_repair import build_header_library_from_folder


MAX_PREVIEW_SIZE = (420, 320)

DEFAULT_HEADER_SIZE = "16 KB"
DEFAULT_FFMPEG_QUALITY = "Normal"
OUTPUT_MODE_SAME = "same"
OUTPUT_MODE_CUSTOM = "custom"


class RepairApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Resim Onarım Aracı - Versiyon: 2.3.0 (Pro)")
        self.geometry("1100x900")

        self.ffmpeg_cmd: Optional[str] = detect_ffmpeg()
        self.ffmpeg_available: bool = self.ffmpeg_cmd is not None

        self.processing_thread: Optional[threading.Thread] = None
        self.cancel_requested: bool = False

        self.last_processed_file: Optional[Path] = None
        self.successful_outputs: Dict[Path, List[Path]] = {}
        self.ref_header_bytes: Optional[bytes] = None
        self.ref_header_path: Optional[Path] = None
        self.header_library: List[bytes] = []
        self.header_library_folder: Optional[Path] = None
        self.last_output_dir: Optional[Path] = None
        self.custom_output_dir: Optional[Path] = None

        self._init_settings()

        self.progress_var = tk.DoubleVar()
        self.stats_total = tk.IntVar(value=0)
        self.stats_fixed = tk.IntVar(value=0)
        self.stats_failed = tk.IntVar(value=0)
        self.stats_processed = tk.IntVar(value=0)

        self.structured_logs: List[Dict[str, Any]] = []
        self._preview_images: List[Any] = []
        self.preview_original_label: Optional[ttk.Label] = None
        self.preview_repaired_label: Optional[ttk.Label] = None
        self.preview_info_label: Optional[ttk.Label] = None

        self._build_ui()

        default_msg = (
            "Uygulama başlatıldı.\n"
            "- Sol panelden tek resim veya klasör seçebilirsiniz.\n"
            "- Sağ panelden onarım yöntemlerini ve ayarları yapılandırabilirsiniz.\n"
            "- Alt bölümde ilerleme, istatistik ve ayrıntılı günlükleri takip edebilirsiniz."
        )
        self.log(default_msg, color="blue")

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------------------------------------------------
    # Ayarların varsayılanları
    # ---------------------------------------------------
    def _init_settings(self):
        self.output_mode = tk.StringVar(value=OUTPUT_MODE_SAME)
        self.use_header = tk.BooleanVar(value=False)
        self.use_ffmpeg = tk.BooleanVar(value=self.ffmpeg_available)
        self.use_pillow = tk.BooleanVar(value=True)
        self.use_png_roundtrip = tk.BooleanVar(value=True)
        self.use_marker = tk.BooleanVar(value=True)
        self.stop_on_first_success = tk.BooleanVar(value=False)
        self.try_all_files = tk.BooleanVar(value=False)
        self.ffmpeg_quality = tk.StringVar(value=DEFAULT_FFMPEG_QUALITY)
        self.header_size_choice = tk.StringVar(value=DEFAULT_HEADER_SIZE)
        self.keep_apps = tk.BooleanVar(value=True)
        self.keep_com = tk.BooleanVar(value=True)
        self.use_embed_scan = tk.BooleanVar(value=True)
        self.use_partial_top = tk.BooleanVar(value=True)
        self.use_exif_thumb = tk.BooleanVar(value=True)
        self.use_png_crc = tk.BooleanVar(value=True)
        self.exif_thumb_upscale = tk.BooleanVar(value=False)
        self.png_crc_skip_ancillary = tk.BooleanVar(value=False)

    # ---------------------------------------------------
    # UI ana iskelet
    # ---------------------------------------------------
    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        left_frame = ttk.LabelFrame(
            main_frame,
            text="📂 İşlem Kontrolleri & Genel Ayarlar",
            padding=10,
        )
        left_frame.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 10))

        right_top = ttk.LabelFrame(main_frame, text="🛠 Onarım Yöntemleri", padding=10)
        right_top.grid(row=0, column=1, sticky="nsew")

        right_middle = ttk.LabelFrame(
            main_frame,
            text="🧠 Smart Header & PNG / Diğer Ayarlar",
            padding=10,
        )
        right_middle.grid(row=1, column=1, sticky="nsew", pady=(10, 0))

        bottom_frame = ttk.LabelFrame(
            main_frame,
            text="📊 İlerleme, İstatistik & Günlük",
            padding=8,
        )
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

        main_frame.rowconfigure(2, weight=1)

        self._build_left_panel(left_frame)
        self._build_methods_panel(right_top)
        self._build_smart_header_panel(right_middle)
        self._build_bottom_panel(bottom_frame)

    # ---------------------------------------------------
    # SOL PANEL: İşlem Kontrolleri + Çıktı Ayarları
    # ---------------------------------------------------
    def _build_left_panel(self, parent: ttk.LabelFrame):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(action_frame, text="İşlem türünü seç:", font=("", 10, "bold")).pack(
            anchor="w",
            pady=(0, 5),
        )

        self.btn_process_single = ttk.Button(
            action_frame,
            text="Tek Resim Seç ve Onar",
            command=self._process_single_file_thread_start,
            width=28,
        )
        self.btn_process_single.pack(anchor="w", pady=2)

        self.btn_process_folder = ttk.Button(
            action_frame,
            text="Klasör Seç ve Tümünü Onar",
            command=self._process_folder_thread_start,
            width=28,
        )
        self.btn_process_folder.pack(anchor="w", pady=2)

        self.btn_cancel = ttk.Button(
            action_frame,
            text="İşlemi İptal Et",
            command=self._cancel_processing,
            state="disabled",
            width=28,
        )
        self.btn_cancel.pack(anchor="w", pady=(8, 2))

        ttk.Separator(parent).pack(fill="x", pady=8)

        output_mode_frame = ttk.LabelFrame(parent, text="Çıktı Klasörü", padding=6)
        output_mode_frame.pack(fill="x", pady=4)

        ttk.Radiobutton(
            output_mode_frame,
            text="Girdi klasörüne alt klasör oluştur",
            variable=self.output_mode,
            value=OUTPUT_MODE_SAME,
        ).pack(anchor="w")

        out_custom_frame = ttk.Frame(output_mode_frame)
        out_custom_frame.pack(fill="x", pady=(4, 0))

        ttk.Radiobutton(
            out_custom_frame,
            text="Özel çıktı klasörü kullan",
            variable=self.output_mode,
            value=OUTPUT_MODE_CUSTOM,
        ).grid(row=0, column=0, sticky="w")

        self.lbl_output_dir = ttk.Label(
            out_custom_frame,
            text="(Seçilmedi)",
            foreground="gray",
        )
        self.lbl_output_dir.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        btn_sel_out = ttk.Button(
            out_custom_frame,
            text="Klasör Seç",
            width=12,
            command=self._select_output_dir,
        )
        btn_sel_out.grid(row=0, column=1, sticky="e", padx=(10, 0))

        out_custom_frame.columnconfigure(0, weight=1)

        file_scan_frame = ttk.LabelFrame(
            parent,
            text="Klasör Taraması",
            padding=6,
        )
        file_scan_frame.pack(fill="x", pady=4)

        ttk.Checkbutton(
            file_scan_frame,
            text="Sadece uzantıya göre değil, içeriğe göre de resim doğrula",
            variable=self.try_all_files,
        ).pack(anchor="w")

        info_lbl = ttk.Label(
            file_scan_frame,
            text="(Büyük klasörlerde daha yavaş olabilir, ama gizli bozuk resimleri de yakalar.)",
            wraplength=240,
        )
        info_lbl.pack(anchor="w", pady=(2, 0))

        ttk.Separator(parent).pack(fill="x", pady=8)

        log_save_frame = ttk.LabelFrame(
            parent,
            text="Kayıt & Log",
            padding=6,
        )
        log_save_frame.pack(fill="x", pady=(4, 0))

        ttk.Button(
            log_save_frame,
            text="Günlükleri TXT/CSV olarak kaydet",
            command=self._save_log_to_file,
            width=30,
        ).pack(anchor="w", pady=2)

        ttk.Button(
            log_save_frame,
            text="Onarılanı Önizle (Ayrı Pencere)",
            command=self._open_preview_window,
            width=30,
        ).pack(anchor="w", pady=2)

    # ---------------------------------------------------
    # SAĞ ÜST: Onarım yöntemleri (JPEG / Genel)
    # ---------------------------------------------------
    def _build_methods_panel(self, parent: ttk.LabelFrame):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        jpeg_frame = ttk.LabelFrame(parent, text="JPEG Yöntemleri", padding=6)
        jpeg_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        jpeg_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            jpeg_frame,
            text="Gömülü JPEG taraması (dosya içinde gizli resimleri çıkar)",
            variable=self.use_embed_scan,
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            jpeg_frame,
            text="Marker temizleme (SOI/EOI aralığını düzelt)",
            variable=self.use_marker,
        ).grid(row=1, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            jpeg_frame,
            text="Partial Top Recovery (dosyanın üst kısmını farklı oranlarda dene)",
            variable=self.use_partial_top,
        ).grid(row=2, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            jpeg_frame,
            text="EXIF thumbnail'den kurtarma (varsa ufak önizleme resmini kullan)",
            variable=self.use_exif_thumb,
        ).grid(row=3, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            jpeg_frame,
            text="EXIF thumbnail'i büyüt (daha büyük ama kalite sınırlı)",
            variable=self.exif_thumb_upscale,
        ).grid(row=4, column=0, sticky="w", pady=(0, 2))

        gen_frame = ttk.LabelFrame(parent, text="Genel Dönüştürme Yöntemleri", padding=6)
        gen_frame.grid(row=0, column=1, sticky="nsew")
        gen_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            gen_frame,
            text="Pillow ile yeniden kaydet (formatı koru)",
            variable=self.use_pillow,
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            gen_frame,
            text="PNG roundtrip (PNG'ye çevir, sonra geri dön)",
            variable=self.use_png_roundtrip,
        ).grid(row=1, column=0, sticky="w", pady=(0, 2))

        ff_frame = ttk.LabelFrame(gen_frame, text="FFmpeg ile Yeniden Encode", padding=6)
        ff_frame.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ff_frame.columnconfigure(1, weight=1)

        chk_ff = ttk.Checkbutton(
            ff_frame,
            text="FFmpeg kullan (JPEG/PNG destekliyorsa)",
            variable=self.use_ffmpeg,
        )
        chk_ff.grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(ff_frame, text="Kalite ön ayarı:").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0),
        )
        self.cmb_ffmpeg_quality = ttk.Combobox(
            ff_frame,
            textvariable=self.ffmpeg_quality,
            values=["Hızlı", "Normal", "Yüksek"],
            state="readonly",
            width=12,
        )
        self.cmb_ffmpeg_quality.grid(row=1, column=1, sticky="ew", pady=(2, 0))

        ff_info = ttk.Label(
            ff_frame,
            text="FFmpeg yoksa bu yöntem otomatik devre dışı kalır.",
            wraplength=260,
            foreground="gray",
        )
        ff_info.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

        ff_status_lbl = ttk.Label(
            ff_frame,
            text=(
                "FFmpeg bulundu: "
                + (self.ffmpeg_cmd or "yok")
            ),
            wraplength=260,
        )
        if self.ffmpeg_available:
            ff_status_lbl.configure(foreground="darkgreen")
        else:
            ff_status_lbl.configure(foreground="red")
        ff_status_lbl.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))

        if not self.ffmpeg_available:
            self.use_ffmpeg.set(False)
            chk_ff.configure(state="disabled")
            self.cmb_ffmpeg_quality.configure(state="disabled")

        general_opts = ttk.LabelFrame(parent, text="Genel Davranış", padding=6)
        general_opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        general_opts.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            general_opts,
            text="İlk başarılı yöntemden sonra diğerlerini deneme",
            variable=self.stop_on_first_success,
        ).grid(row=0, column=0, sticky="w")

    # ---------------------------------------------------
    # SAĞ ORTA: Smart Header, PNG ve JPEG ileri ayarları
    # ---------------------------------------------------
    def _build_smart_header_panel(self, parent: ttk.LabelFrame):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        sh_frame = ttk.LabelFrame(parent, text="JPEG Smart Header V3", padding=6)
        sh_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sh_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            sh_frame,
            text="Smart Header V3 kullan (referans header ile onarım)",
            variable=self.use_header,
            command=self._on_use_header_toggle,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        btn_sel_header = ttk.Button(
            sh_frame,
            text="Referans Header Dosyası Seç",
            command=self._select_header_file,
            width=26,
        )
        btn_sel_header.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.lbl_header_file = ttk.Label(
            sh_frame,
            text="(Seçilmedi)",
            foreground="gray",
        )
        self.lbl_header_file.grid(row=1, column=1, sticky="w", padx=(8, 0))

        btn_sel_header_lib = ttk.Button(
            sh_frame,
            text="Header Kütüphanesi Klasörü",
            command=self._select_header_library_folder,
            width=26,
        )
        btn_sel_header_lib.grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.lbl_header_lib = ttk.Label(
            sh_frame,
            text="(Kütüphane yok)",
            foreground="gray",
        )
        self.lbl_header_lib.grid(row=2, column=1, sticky="w", padx=(8, 0))

        size_frame = ttk.Frame(sh_frame)
        size_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Label(size_frame, text="Header kopyalama boyutu (fallback):").grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.cmb_header_size = ttk.Combobox(
            size_frame,
            textvariable=self.header_size_choice,
            values=["8 KB", "16 KB", "32 KB", "64 KB"],
            state="readonly",
            width=8,
        )
        self.cmb_header_size.grid(row=0, column=1, sticky="w", padx=(4, 0))

        opts_frame = ttk.Frame(sh_frame)
        opts_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        ttk.Checkbutton(
            opts_frame,
            text="APP segmentlerini koru (EXIF, IPTC vb.)",
            variable=self.keep_apps,
        ).grid(row=0, column=0, sticky="w")

        ttk.Checkbutton(
            opts_frame,
            text="COM segmentlerini koru",
            variable=self.keep_com,
        ).grid(row=1, column=0, sticky="w")

        sh_info = ttk.Label(
            sh_frame,
            text=(
                "Smart Header V3, bozuk JPEG dosyalarında DQT/DHT tablolarını "
                "referans veya kütüphane header'larından alarak header'ı yeniden inşa eder. "
                "FFDA bulunamazsa, fallback olarak belirtilen header boyutu kadar sabit kopyalama dener."
            ),
            wraplength=320,
            foreground="gray",
        )
        sh_info.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self._on_use_header_toggle()

        png_frame = ttk.LabelFrame(parent, text="PNG Onarım", padding=6)
        png_frame.grid(row=0, column=1, sticky="nsew")
        png_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(
            png_frame,
            text="PNG CRC onarımı (NORMAL + AGGR mod)",
            variable=self.use_png_crc,
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        ttk.Checkbutton(
            png_frame,
            text="CRC hatalı ancillary chunk'ları tamamen atla",
            variable=self.png_crc_skip_ancillary,
        ).grid(row=1, column=0, sticky="w", pady=(0, 2))

        png_info = ttk.Label(
            png_frame,
            text=(
                "PNG CRC onarımı önce NORMAL modda tüm CRC'leri düzeltir, "
                "gerekirse AGGR modda hatalı ancillary chunk'ları atar "
                "ve kritik chunk'lardaki hatalarda akışı keser."
            ),
            wraplength=320,
            foreground="gray",
        )
        png_info.grid(row=2, column=0, sticky="w", pady=(4, 0))

    # ---------------------------------------------------
    # ALT PANEL: İlerleme, istatistik, log, inline önizleme
    # ---------------------------------------------------
    def _build_bottom_panel(self, parent: ttk.LabelFrame):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=0, column=0, sticky="ew")
        progress_frame.columnconfigure(1, weight=1)

        ttk.Label(progress_frame, text="İlerleme:").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=200,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress_bar.grid(
            row=0,
            column=1,
            sticky="we",
            padx=8,
            pady=5,
        )

        stats_frame = ttk.Frame(parent)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        for col in range(8):
            stats_frame.columnconfigure(col, weight=1)

        ttk.Label(stats_frame, text="Toplam:").grid(row=0, column=0, sticky="e")
        ttk.Label(stats_frame, textvariable=self.stats_total).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(2, 10),
        )

        ttk.Label(stats_frame, text="Onarılan:").grid(row=0, column=2, sticky="e")
        ttk.Label(stats_frame, textvariable=self.stats_fixed).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(2, 10),
        )

        ttk.Label(stats_frame, text="Başarısız:").grid(row=0, column=4, sticky="e")
        ttk.Label(stats_frame, textvariable=self.stats_failed).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(2, 10),
        )

        ttk.Label(stats_frame, text="İşlenen:").grid(row=0, column=6, sticky="e")
        ttk.Label(stats_frame, textvariable=self.stats_processed).grid(
            row=0,
            column=7,
            sticky="w",
            padx=(2, 10),
        )

        bottom_split = ttk.Panedwindow(parent, orient="horizontal")
        bottom_split.grid(row=2, column=0, sticky="nsew")
        parent.rowconfigure(2, weight=1)

        preview_frame = ttk.LabelFrame(bottom_split, text="📷 Hızlı Önizleme", padding=6)
        bottom_split.add(preview_frame, weight=1)

        self.preview_original_label = ttk.Label(
            preview_frame,
            text="Orijinal",
            anchor="center",
        )
        self.preview_original_label.grid(row=0, column=0, padx=4, pady=4)

        self.preview_repaired_label = ttk.Label(
            preview_frame,
            text="En iyi onarım",
            anchor="center",
        )
        self.preview_repaired_label.grid(row=0, column=1, padx=4, pady=4)

        self.preview_info_label = ttk.Label(
            preview_frame,
            text="-",
            foreground="gray",
            wraplength=380,
        )
        self.preview_info_label.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 0))

        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)

        log_frame = ttk.Frame(bottom_split)
        bottom_split.add(log_frame, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.txt_log = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            state="disabled",
            wrap="word",
        )
        self.txt_log.grid(row=0, column=0, sticky="nsew")

        for color in ("black", "blue", "green", "darkgreen", "orange", "red"):
            self.txt_log.tag_configure(color, foreground=color)

    # ---------------------------------------------------
    # Yardımcı UI metotları
    # ---------------------------------------------------
    def log(self, msg: str, color: str = "black"):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"

        def _append():
            if hasattr(self, "txt_log") and self.txt_log is not None:
                self.txt_log.configure(state="normal")
                self.txt_log.insert("end", line, color)
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")

        # Tkinter thread-safe: UI güncellemelerini ana threade schedule et
        try:
            self.after(0, _append)
        except Exception:
            # Uygulama kapanırken veya henüz mainloop başlamadan log çağrılırsa
            _append()

        self.structured_logs.append(
            {
                "time": timestamp,
                "message": msg,
                "color": color,
            }
        )

    def _save_log_to_file(self):
        if not self.structured_logs:
            messagebox.showinfo("Bilgi", "Kaydedilecek günlük bulunmuyor.")
            return

        initial_dir = self._get_last_dir_or_cwd()

        file_path = filedialog.asksaveasfilename(
            title="Günlükleri Kaydet",
            initialdir=initial_dir,
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
            if out_path.suffix.lower() == ".csv":
                import csv

                with out_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["time", "color", "message"])
                    for item in self.structured_logs:
                        writer.writerow([item["time"], item["color"], item["message"]])
            else:
                with out_path.open("w", encoding="utf-8") as f:
                    for item in self.structured_logs:
                        f.write(f"[{item['time']}] ({item['color']}) {item['message']}\n")

            messagebox.showinfo("Başarılı", f"Günlükler kaydedildi:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Günlük kaydedilemedi: {e}")

    def _get_last_dir_or_cwd(self) -> str:
        if self.last_output_dir is not None:
            return str(self.last_output_dir)
        return os.getcwd()

    def _select_output_dir(self):
        folder = filedialog.askdirectory(
            title="Özel çıktı klasörü seç",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return
        self.custom_output_dir = Path(folder)
        self.lbl_output_dir.configure(text=str(self.custom_output_dir), foreground="black")
        self.log(f"Özel çıktı klasörü seçildi: {self.custom_output_dir}", color="blue")

    def _select_header_file(self):
        file_path = filedialog.askopenfilename(
            title="Referans JPEG dosyası seç",
            filetypes=[("JPEG Dosyaları", "*.jpg;*.jpeg"), ("Tüm Dosyalar", "*.*")],
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not file_path:
            return

        p = Path(file_path)
        try:
            with p.open("rb") as f:
                header_size = 64 * 1024
                self.ref_header_bytes = f.read(header_size)
            self.ref_header_path = p
            self.lbl_header_file.configure(text=str(p.name), foreground="black")
            self.log(f"Referans header dosyası seçildi: {p}", color="blue")
        except Exception as e:
            messagebox.showerror("Hata", f"Header dosyası okunamadı: {e}")
            self.log(f"Header dosyası okunamadı: {e}", color="red")

    def _select_header_library_folder(self):
        folder = filedialog.askdirectory(
            title="Header kütüphanesi klasörü seç",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return

        p = Path(folder)
        try:
            self.header_library = build_header_library_from_folder(p)
            self.header_library_folder = p
            self.lbl_header_lib.configure(
                text=f"{p.name} ({len(self.header_library)} header)",
                foreground="black",
            )
            self.log(
                f"Header kütüphanesi klasörü seçildi: {p} ({len(self.header_library)} header okundu)",
                color="blue",
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Header kütüphanesi okunamadı: {e}")
            self.log(f"Header kütüphanesi okunamadı: {e}", color="red")

    def _on_use_header_toggle(self):
        state = "normal" if self.use_header.get() else "disabled"
        for w in (self.cmb_header_size,):
            w.configure(state=state)

    def _create_preview_image(self, path: Path) -> Optional[ImageTk.PhotoImage]:
        try:
            with Image.open(path) as im:
                im.load()
                im.thumbnail(MAX_PREVIEW_SIZE)
                return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _update_preview_inline(self, original: Path, best_output: Optional[Path]):
        self._preview_images.clear()

        if self.preview_original_label and original.exists():
            pi = self._create_preview_image(original)
            if pi:
                self.preview_original_label.configure(image=pi, text="")
                self._preview_images.append(pi)
            else:
                self.preview_original_label.configure(
                    image="",
                    text="Orijinal önizleme yüklenemedi.",
                )

        if self.preview_repaired_label:
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

        if self.preview_info_label:
            if best_output and best_output.exists():
                try:
                    size_str = f"{best_output.stat().st_size / 1024:.1f} KB"
                    with Image.open(best_output) as im:
                        w, h = im.size
                    self.preview_info_label.configure(
                        text=f"Son işlenen dosya: {original.name}\n"
                        f"En iyi çıktı: {best_output.name} ({w}x{h}, {size_str})"
                    )
                except Exception:
                    self.preview_info_label.configure(
                        text=f"Son işlenen dosya: {original.name}\n"
                        f"En iyi çıktı: {best_output.name}",
                    )
            else:
                self.preview_info_label.configure(
                    text=f"Son işlenen dosya: {original.name}\n"
                    f"Henüz başarılı bir çıktı bulunamadı.",
                )

    def _open_preview_window(self):
        if not self.last_processed_file:
            messagebox.showinfo(
                "Bilgi",
                "Henüz işlenmiş bir dosya yok. Önce tek bir dosya veya klasör işlemi başlatın.",
            )
            return

        best = pick_best_output(self.successful_outputs.get(self.last_processed_file, []))
        if not best:
            messagebox.showinfo(
                "Bilgi",
                "Son işlenen dosya için başarılı bir çıktı bulunamadı.",
            )
            return

        win = tk.Toplevel(self)
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

        po = self._create_preview_image(self.last_processed_file)
        if po:
            orig_label.configure(image=po, text="")
            imgs.append(po)

        pf = self._create_preview_image(best)
        if pf:
            fix_label.configure(image=pf, text="")
            imgs.append(pf)

        win.preview_images = imgs  # type: ignore[attr-defined]

    # ---------------------------------------------------
    # Thread-safe istatistik / ilerleme güncellemesi
    # ---------------------------------------------------
    def _update_progress_threadsafe(self, best_output: Optional[Path], total_files: int):
        """İstatistik ve ilerleme çubuğunu ana thread üzerinde güvenli şekilde günceller."""
        if best_output:
            self.stats_fixed.set(self.stats_fixed.get() + 1)
        else:
            self.stats_failed.set(self.stats_failed.get() + 1)

        self.stats_processed.set(self.stats_processed.get() + 1)
        processed = self.stats_processed.get()
        progress = (processed / max(total_files, 1)) * 100
        self.progress_var.set(progress)

    # ---------------------------------------------------
    # İşlem başlatma ve worker thread
    # ---------------------------------------------------
    def _start_processing(self, files: List[Path]):
        total_files = len(files)
        self.cancel_requested = False

        self.stats_total.set(total_files)
        self.stats_fixed.set(0)
        self.stats_failed.set(0)
        self.stats_processed.set(0)
        self.progress_var.set(0.0)
        self.successful_outputs.clear()
        self.last_processed_file = None

        self.btn_cancel.config(state="normal")
        self.btn_process_single.config(state="disabled")
        self.btn_process_folder.config(state="disabled")

        self.log(
            f"Toplam {total_files} dosya için onarım işlemi başlatıldı.",
            color="blue",
        )

        def worker():
            try:
                for f in files:
                    if self.cancel_requested:
                        self.log("İşlem kullanıcı tarafından iptal edildi.", color="red")
                        break

                    out_dir = self._get_output_dir_for_input(f)
                    if out_dir is None:
                        self.log(
                            f"Çıktı klasörü oluşturulamadığı için atlandı: {f}",
                            color="red",
                        )
                        continue

                    use_pillow = self.use_pillow.get()
                    use_png_roundtrip = self.use_png_roundtrip.get()
                    use_header = self.use_header.get()
                    use_marker = self.use_marker.get()
                    use_ffmpeg = self.use_ffmpeg.get() and self.ffmpeg_available
                    stop_on_first_success = self.stop_on_first_success.get()
                    use_embed_scan = self.use_embed_scan.get()
                    use_partial_top = self.use_partial_top.get()
                    use_exif_thumb = self.use_exif_thumb.get()
                    use_png_crc = self.use_png_crc.get()
                    exif_thumb_upscale = self.exif_thumb_upscale.get()
                    png_crc_skip_ancillary = self.png_crc_skip_ancillary.get()

                    ref_header_bytes = self.ref_header_bytes
                    header_library = self.header_library if self.header_library else None

                    size_map = {
                        "8 KB": 8 * 1024,
                        "16 KB": 16 * 1024,
                        "32 KB": 32 * 1024,
                        "64 KB": 64 * 1024,
                    }
                    header_size = size_map.get(self.header_size_choice.get(), 16 * 1024)

                    ffmpeg_cmd = self.ffmpeg_cmd
                    quality_label = self.ffmpeg_quality.get()
                    if quality_label == "Hızlı":
                        q_list = [6, 5]
                    elif quality_label == "Yüksek":
                        q_list = [3, 4, 5]
                    else:
                        q_list = [4, 5]

                    self.log(f"İşleniyor: {f}", color="black")

                    outputs = repair_image_all_methods(
                        input_path=f,
                        base_output_dir=out_dir,
                        ref_header_bytes=ref_header_bytes,
                        ffmpeg_cmd=ffmpeg_cmd,
                        use_pillow=use_pillow,
                        use_png_roundtrip=use_png_roundtrip,
                        use_header=use_header,
                        use_marker=use_marker,
                        use_ffmpeg=use_ffmpeg,
                        ffmpeg_qscale_list=q_list,
                        stop_on_first_success=stop_on_first_success,
                        header_size=header_size,
                        log=self.log,
                        keep_apps=self.keep_apps.get(),
                        keep_com=self.keep_com.get(),
                        header_library=header_library,
                        use_embed_scan=use_embed_scan,
                        use_partial_top=use_partial_top,
                        use_exif_thumb=use_exif_thumb,
                        use_png_crc=use_png_crc,
                        exif_thumb_upscale=exif_thumb_upscale,
                        png_crc_skip_ancillary=png_crc_skip_ancillary,
                    )
                    self.successful_outputs[f] = outputs
                    best = pick_best_output(outputs) if outputs else None

                    self.last_processed_file = f
                    self.after(0, self._update_preview_inline, f, best)

                    # İstatistik ve ilerleme çubuğu güncellemesini ana threade schedule et
                    self.after(0, self._update_progress_threadsafe, best, total_files)

                self.after(0, self._on_processing_finished)
            except Exception as e:
                self.log(f"İşleme sırasında beklenmeyen hata: {e}", color="red")
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Hata",
                        f"İşleme sırasında beklenmeyen hata oluştu:\n{e}",
                    ),
                )
                self.after(0, self._on_processing_finished)

        self.processing_thread = threading.Thread(target=worker, daemon=True)
        self.processing_thread.start()

    def _on_processing_finished(self):
        self.btn_cancel.config(state="disabled")
        self.btn_process_single.config(state="normal")
        self.btn_process_folder.config(state="normal")

        total = self.stats_total.get()
        fixed = self.stats_fixed.get()
        failed = self.stats_failed.get()
        self.log(
            f"İşlem tamamlandı. Toplam: {total}, Onarılan: {fixed}, Başarısız: {failed}",
            color="blue",
        )

        messagebox.showinfo(
            "Tamamlandı",
            f"Onarım işlemi tamamlandı.\nToplam: {total}\nOnarılan: {fixed}\nBaşarısız: {failed}",
        )

    def _cancel_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            self.cancel_requested = True
            self.log("İşlem iptal isteği gönderildi. Devam eden dosya tamamlanınca duracak.", color="orange")

    # ---------------------------------------------------
    # Girdi seçimi (tek dosya / klasör)
    # ---------------------------------------------------
    def _process_single_file_thread_start(self):
        if self.processing_thread and self.processing_thread.is_alive():
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

        p = Path(file_path)
        if not is_image_file(p, check_content=True):
            messagebox.showerror(
                "Hata",
                "Seçilen dosya geçerli bir resim dosyası değil.",
            )
            return

        self._start_processing([p])

    def _process_folder_thread_start(self):
        if self.processing_thread and self.processing_thread.is_alive():
            messagebox.showwarning("Uyarı", "Zaten devam eden bir işlem var.")
            return

        folder = filedialog.askdirectory(
            title="Onarılacak resimlerin bulunduğu klasörü seçin",
            initialdir=self._get_last_dir_or_cwd(),
        )
        if not folder:
            return

        root_path = Path(folder)

        def iter_images(root: Path):
            use_content_check = self.try_all_files.get()
            for dirpath, _, filenames in os.walk(root):
                dpath = Path(dirpath)
                for name in filenames:
                    p = dpath / name
                    if is_image_file(p, check_content=use_content_check):
                        yield p

        files = list(iter_images(root_path))

        if not files:
            messagebox.showinfo(
                "Bilgi",
                "Seçilen klasörde onarılabilecek resim dosyası bulunamadı.",
            )
            return

        self._start_processing(files)

    def _get_output_dir_for_input(self, input_path: Path) -> Optional[Path]:
        try:
            if self.output_mode.get() == OUTPUT_MODE_CUSTOM:
                if not self.custom_output_dir:
                    messagebox.showerror(
                        "Hata",
                        "Özel çıktı klasörü seçilmedi.",
                    )
                    return None
                out_dir = self.custom_output_dir / DEST_SUBFOLDER_NAME
            else:
                out_dir = input_path.parent / DEST_SUBFOLDER_NAME

            out_dir.mkdir(parents=True, exist_ok=True)
            self.last_output_dir = out_dir
            return out_dir
        except Exception as e:
            self.log(f"Çıktı klasörü oluşturulamadı: {e}", color="red")
            return None

    def _on_closing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            if not messagebox.askyesno(
                "Kapat",
                "Devam eden bir işlem var. Yine de çıkmak istiyor musunuz?",
            ):
                return
        self.destroy()


def run_app():
    app = RepairApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
