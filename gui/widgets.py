from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import tkinter as tk
from tkinter import scrolledtext, ttk

from utils import DEST_SUBFOLDER_NAME


@dataclass
class CommandBindings:
    process_single: callable
    process_folder: callable
    cancel_processing: callable
    select_output_dir: callable
    select_header_file: callable
    select_header_library: callable
    save_log: callable
    open_preview_window: callable
    on_use_header_toggle: callable


@dataclass
class WidgetRefs:
    btn_process_single: ttk.Button
    btn_process_folder: ttk.Button
    btn_cancel: ttk.Button
    lbl_output_dir: ttk.Label
    lbl_header_file: ttk.Label
    lbl_header_lib: ttk.Label
    cmb_header_size: ttk.Combobox
    txt_log: scrolledtext.ScrolledText
    preview_original_label: ttk.Label
    preview_repaired_label: ttk.Label
    preview_info_label: ttk.Label


def build_ui(
    root: tk.Tk,
    variables: Dict[str, tk.Variable],
    commands: CommandBindings,
    progress_var: tk.DoubleVar,
    stats_total: tk.IntVar,
    stats_fixed: tk.IntVar,
    stats_failed: tk.IntVar,
    stats_processed: tk.IntVar,
    ffmpeg_available: bool,
    ffmpeg_cmd: Optional[str],
    default_output_mode_same: str,
) -> WidgetRefs:
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=0)
    root.grid_columnconfigure(1, weight=1)

    # Sol panel
    left_frame = ttk.Frame(root, padding=8)
    left_frame.grid(row=0, column=0, sticky="nsw")
    left_frame.grid_rowconfigure(1, weight=1)
    left_frame.grid_columnconfigure(0, weight=1)

    # Sağ panel
    right_frame = ttk.Frame(root, padding=8)
    right_frame.grid(row=0, column=1, sticky="nsew")
    right_frame.grid_rowconfigure(0, weight=1)
    right_frame.grid_rowconfigure(1, weight=0)
    right_frame.grid_rowconfigure(2, weight=0)
    right_frame.grid_columnconfigure(0, weight=1)

    # Sol panel: Girdi / çıktı / butonlar
    (
        btn_process_single,
        btn_process_folder,
        btn_cancel,
        lbl_output_dir,
    ) = _build_left_panel(left_frame, variables, commands, default_output_mode_same)

    # Sağ üst: yöntemler ve ayarlar
    (
        lbl_header_file,
        lbl_header_lib,
        cmb_header_size,
    ) = _build_methods_panel(right_frame, variables, commands, ffmpeg_available, ffmpeg_cmd)

    # Sağ orta: log ve istatistikler
    txt_log, preview_original_label, preview_repaired_label, preview_info_label = _build_bottom_panel(
        right_frame,
        progress_var,
        stats_total,
        stats_fixed,
        stats_failed,
        stats_processed,
        commands,
    )

    return WidgetRefs(
        btn_process_single=btn_process_single,
        btn_process_folder=btn_process_folder,
        btn_cancel=btn_cancel,
        lbl_output_dir=lbl_output_dir,
        lbl_header_file=lbl_header_file,
        lbl_header_lib=lbl_header_lib,
        cmb_header_size=cmb_header_size,
        txt_log=txt_log,
        preview_original_label=preview_original_label,
        preview_repaired_label=preview_repaired_label,
        preview_info_label=preview_info_label,
    )


# -------------------------------------------------------------------
# Sol panel (Girdi / Çıktı / İşlem Butonları)
# -------------------------------------------------------------------
def _build_left_panel(
    parent: ttk.Frame,
    variables: Dict[str, tk.Variable],
    commands: CommandBindings,
    default_output_mode_same: str,
):
    parent.grid_rowconfigure(0, weight=0)
    parent.grid_rowconfigure(1, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    # Girdi seçimi
    group_input = ttk.LabelFrame(parent, text="Girdi Seçimi", padding=6)
    group_input.grid(row=0, column=0, sticky="ew")
    group_input.grid_columnconfigure(0, weight=1)

    btn_process_single = ttk.Button(
        group_input,
        text="Tek Resim Seç ve Onar",
        command=commands.process_single,
        width=24,
    )
    btn_process_single.grid(row=0, column=0, sticky="ew", pady=(0, 4))

    btn_process_folder = ttk.Button(
        group_input,
        text="Klasördeki Tüm Resimleri Onar",
        command=commands.process_folder,
        width=24,
    )
    btn_process_folder.grid(row=1, column=0, sticky="ew")

    # Çıktı ayarları
    group_output = ttk.LabelFrame(parent, text="Çıktı Ayarları", padding=6)
    group_output.grid(row=1, column=0, sticky="new", pady=(8, 0))
    group_output.grid_columnconfigure(0, weight=1)

    # Çıktı modu
    frame_output_mode = ttk.Frame(group_output)
    frame_output_mode.grid(row=0, column=0, sticky="w")

    ttk.Label(frame_output_mode, text="Çıktı konumu:").grid(row=0, column=0, sticky="w")

    rb_same = ttk.Radiobutton(
        frame_output_mode,
        text=f"Aynı klasörde '{DEST_SUBFOLDER_NAME}' altına",
        variable=variables["output_mode"],
        value=default_output_mode_same,
    )
    rb_same.grid(row=1, column=0, sticky="w", pady=(2, 0))

    rb_custom = ttk.Radiobutton(
        frame_output_mode,
        text="Özel çıktı klasörü kullan",
        variable=variables["output_mode"],
        value="custom",
    )
    rb_custom.grid(row=2, column=0, sticky="w", pady=(0, 4))

    # Özel çıktı klasörü seçimi
    frame_custom_out = ttk.Frame(group_output)
    frame_custom_out.grid(row=1, column=0, sticky="ew")

    btn_select_output = ttk.Button(
        frame_custom_out,
        text="Klasör Seç",
        command=commands.select_output_dir,
        width=12,
    )
    btn_select_output.grid(row=0, column=0, sticky="w")

    lbl_output_dir = ttk.Label(
        frame_custom_out,
        text="(Seçilmedi)",
        foreground="gray",
        wraplength=220,
    )
    lbl_output_dir.grid(row=0, column=1, sticky="w", padx=(8, 0))

    # İşlem kontrol butonları
    group_actions = ttk.LabelFrame(parent, text="İşlem Kontrolleri", padding=6)
    group_actions.grid(row=2, column=0, sticky="new", pady=(8, 0))
    group_actions.grid_columnconfigure(0, weight=1)

    btn_cancel = ttk.Button(
        group_actions,
        text="İşlemi İptal Et",
        command=commands.cancel_processing,
        width=24,
        state="disabled",
    )
    btn_cancel.grid(row=0, column=0, sticky="ew")

    btn_save_log = ttk.Button(
        group_actions,
        text="Günlükleri Kaydet",
        command=commands.save_log,
        width=24,
    )
    btn_save_log.grid(row=1, column=0, sticky="ew", pady=(4, 0))

    btn_preview = ttk.Button(
        group_actions,
        text="Önizleme Penceresi",
        command=commands.open_preview_window,
        width=24,
    )
    btn_preview.grid(row=2, column=0, sticky="ew", pady=(4, 0))

    return btn_process_single, btn_process_folder, btn_cancel, lbl_output_dir


# -------------------------------------------------------------------
# Sağ üst panel: yöntemler, header, PNG/JPEG ayarları + AI paneli
# -------------------------------------------------------------------
def _build_methods_panel(
    parent: ttk.Frame,
    variables: Dict[str, tk.Variable],
    commands: CommandBindings,
    ffmpeg_available: bool,
    ffmpeg_cmd: Optional[str],
):
    methods_frame = ttk.LabelFrame(parent, text="Onarım Yöntemleri ve Ayarlar", padding=6)
    methods_frame.grid(row=0, column=0, sticky="nsew")
    methods_frame.grid_columnconfigure(0, weight=1)
    methods_frame.grid_columnconfigure(1, weight=1)

    # Pipeline / genel seçenekler
    pipeline_frame = ttk.LabelFrame(methods_frame, text="Pipeline / Genel", padding=6)
    pipeline_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    pipeline_frame.grid_columnconfigure(0, weight=1)

    ttk.Checkbutton(
        pipeline_frame,
        text="Başarılı ilk yöntemden sonra dur",
        variable=variables["stop_on_first_success"],
    ).grid(row=0, column=0, sticky="w")

    ttk.Checkbutton(
        pipeline_frame,
        text="Klasörde tüm dosyaları dene (içerik kontrolüyle)",
        variable=variables["try_all_files"],
    ).grid(row=1, column=0, sticky="w", pady=(0, 2))

    # JPEG yöntemleri
    jpeg_frame = ttk.LabelFrame(methods_frame, text="JPEG Yöntemleri", padding=6)
    jpeg_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
    jpeg_frame.grid_columnconfigure(0, weight=1)

    ttk.Checkbutton(
        jpeg_frame,
        text="Pillow ile yeniden yaz (basit yeniden kaydetme)",
        variable=variables["use_pillow"],
    ).grid(row=0, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="Smart Header V3 (DQT/DHT tahmini + header yeniden inşa)",
        variable=variables["use_header"],
        command=commands.on_use_header_toggle,
    ).grid(row=1, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="Marker onarımı (SOI/SOS tarama, bozuk segmentleri atlama)",
        variable=variables["use_marker"],
    ).grid(row=2, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="Gömülü JPEG taraması (EXIF thumbnail, gömülü tam JPEG)",
        variable=variables["use_embed_scan"],
    ).grid(row=3, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="Partial-top truncation onarımı (üst kısım sağlam, altı bozuk)",
        variable=variables["use_partial_top"],
    ).grid(row=4, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="EXIF thumbnail'den kurtarma (gerekiyorsa büyütme)",
        variable=variables["use_exif_thumb"],
    ).grid(row=5, column=0, sticky="w")

    ttk.Checkbutton(
        jpeg_frame,
        text="EXIF thumbnail'i onarım sonrası up-scale et",
        variable=variables["exif_thumb_upscale"],
    ).grid(row=6, column=0, sticky="w")

    # Smart Header / Header kütüphanesi bölümü
    sh_frame = ttk.LabelFrame(methods_frame, text="Smart Header V3 Ayarları", padding=6)
    sh_frame.grid(row=1, column=1, sticky="nsew")
    sh_frame.grid_columnconfigure(1, weight=1)

    btn_sel_header_file = ttk.Button(
        sh_frame,
        text="Referans JPEG Dosyası Seç",
        command=commands.select_header_file,
        width=26,
    )
    btn_sel_header_file.grid(row=0, column=0, sticky="w")

    lbl_header_file = ttk.Label(
        sh_frame,
        text="(Seçilmedi)",
        foreground="gray",
    )
    lbl_header_file.grid(row=0, column=1, sticky="w", padx=(8, 0))

    btn_sel_header_lib = ttk.Button(
        sh_frame,
        text="Header Kütüphanesi Klasörü",
        command=commands.select_header_library,
        width=26,
    )
    btn_sel_header_lib.grid(row=1, column=0, sticky="w", pady=(4, 0))

    lbl_header_lib = ttk.Label(
        sh_frame,
        text="(Kütüphane yok)",
        foreground="gray",
    )
    lbl_header_lib.grid(row=1, column=1, sticky="w", padx=(8, 0))

    size_frame = ttk.Frame(sh_frame)
    size_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    ttk.Label(size_frame, text="Header kopyalama boyutu (fallback):").grid(
        row=0,
        column=0,
        sticky="w",
    )

    cmb_header_size = ttk.Combobox(
        size_frame,
        textvariable=variables["header_size_choice"],
        values=["8 KB", "16 KB", "32 KB", "64 KB"],
        state="readonly",
        width=8,
    )
    cmb_header_size.grid(row=0, column=1, sticky="w", padx=(4, 0))

    opts_frame = ttk.Frame(sh_frame)
    opts_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    ttk.Checkbutton(
        opts_frame,
        text="APP segmentlerini koru (EXIF, IPTC vb.)",
        variable=variables["keep_apps"],
    ).grid(row=0, column=0, sticky="w")

    ttk.Checkbutton(
        opts_frame,
        text="COM segmentlerini koru",
        variable=variables["keep_com"],
    ).grid(row=1, column=0, sticky="w")

    sh_info = ttk.Label(
        sh_frame,
        text=(
            "Smart Header V3, bozuk JPEG dosyalarında DQT/DHT tablolarını "
            "referans veya kütüphane header'larından alarak header'ı yeniden inşa eder. "
            "FFDA bulunamazsa, fallback olarak belirtilen header boyutu kadar "
            "sabit kopyalama dener."
        ),
        wraplength=320,
        foreground="gray",
    )
    sh_info.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # PNG onarım
    png_frame = ttk.LabelFrame(methods_frame, text="PNG Onarım", padding=6)
    png_frame.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
    png_frame.grid_columnconfigure(0, weight=1)

    ttk.Checkbutton(
        png_frame,
        text="PNG CRC onarımı (NORMAL + AGGR mod)",
        variable=variables["use_png_crc"],
    ).grid(row=0, column=0, sticky="w", pady=(0, 2))

    ttk.Checkbutton(
        png_frame,
        text="CRC hatalı ancillary chunk'ları tamamen atla",
        variable=variables["png_crc_skip_ancillary"],
    ).grid(row=1, column=0, sticky="w", pady=(0, 2))

    png_info = ttk.Label(
        png_frame,
        text=(
            "PNG CRC onarımı, bozuk veya eksik CRC alanlarını yeniden hesaplayarak "
            "okunabilirliği artırmayı dener. Normal mod başarısız olursa, "
            "AGGR (agresif) modda daha fazla chunk tamiri denenir."
        ),
        wraplength=320,
        foreground="gray",
    )
    png_info.grid(row=2, column=0, sticky="w", pady=(4, 0))

    # FFmpeg / Diğer ayarlar
    misc_frame = ttk.LabelFrame(methods_frame, text="FFmpeg ve Diğer Ayarlar", padding=6)
    misc_frame.grid(row=2, column=1, sticky="nsew", pady=(4, 0))
    misc_frame.grid_columnconfigure(0, weight=1)

    if ffmpeg_available:
        ttk.Checkbutton(
            misc_frame,
            text=f"FFmpeg denemesi (bulundu: {ffmpeg_cmd})",
            variable=variables["use_ffmpeg"],
        ).grid(row=0, column=0, sticky="w")

        frame_qual = ttk.Frame(misc_frame)
        frame_qual.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Label(frame_qual, text="FFmpeg kalite profili:").grid(row=0, column=0, sticky="w")

        cmb_ffmpeg_quality = ttk.Combobox(
            frame_qual,
            textvariable=variables["ffmpeg_quality"],
            values=["Düşük", "Normal", "Yüksek"],
            state="readonly",
            width=10,
        )
        cmb_ffmpeg_quality.grid(row=0, column=1, sticky="w", padx=(4, 0))
    else:
        ttk.Label(
            misc_frame,
            text="FFmpeg bulunamadı. ffmpeg.exe'yi program klasörüne kopyalarsanız\n"
                 "ek bir onarım yöntemi olarak kullanılabilir.",
            wraplength=320,
            foreground="gray",
        ).grid(row=0, column=0, sticky="w")

    misc_info = ttk.Label(
        misc_frame,
        text=(
            "FFmpeg, özellikle bozuk akış yapısına sahip dosyalarda yeniden muxing "
            "yaparak bazı hataları düzeltebilir. Varsayılan profil 'Normal'dir; "
            "gerekirse daha düşük/yüksek kalite seçilebilir."
        ),
        wraplength=320,
        foreground="gray",
    )
    misc_info.grid(row=2, column=0, sticky="w", pady=(4, 0))

    # --------------------------------------------------
    # AI JPEG Patch Reconstruction paneli
    # --------------------------------------------------
    ai_frame = ttk.LabelFrame(methods_frame, text="🧬 AI JPEG Patch Reconstruction", padding=6)
    ai_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
    ai_frame.grid_columnconfigure(0, weight=1)

    ttk.Checkbutton(
        ai_frame,
        text="Hasarlı JPEG bloklarını AI ile tahmin et ve doldur",
        variable=variables["use_ai_patch"],
    ).grid(row=0, column=0, sticky="w", pady=(0, 4))

    ttk.Checkbutton(
        ai_frame,
        text="Real-ESRGAN / benzeri süper çözünürlük",
        variable=variables["ai_use_realesrgan"],
    ).grid(row=1, column=0, sticky="w")

    ttk.Checkbutton(
        ai_frame,
        text="GFPGAN ile yüz onarımı",
        variable=variables["ai_use_gfpgan"],
    ).grid(row=2, column=0, sticky="w")

    ttk.Checkbutton(
        ai_frame,
        text="Stable Diffusion / benzeri inpainting (büyük boşlukları doldur)",
        variable=variables["ai_use_inpaint"],
    ).grid(row=3, column=0, sticky="w")

    ttk.Label(
        ai_frame,
        text="Hasar eşiği (0.4 = agresif, 0.95 = çok muhafazakâr):",
    ).grid(row=4, column=0, sticky="w", pady=(6, 2))

    sld_thr = ttk.Scale(
        ai_frame,
        from_=0.4,
        to=0.95,
        orient="horizontal",
        variable=variables["ai_damage_threshold"],
    )
    sld_thr.grid(row=5, column=0, sticky="we")

    ai_info = ttk.Label(
        ai_frame,
        text=(
            "AI modu, klasik onarımın en iyi çıktısını alır, hasar ısı haritası ile "
            "bozuk bölgeleri maskelemiş şekilde ESRGAN / GFPGAN / Inpainting "
            "uygular ve ek bir '*_ai_patch' çıktısı üretir."
        ),
        wraplength=320,
        foreground="gray",
    )
    ai_info.grid(row=6, column=0, sticky="w", pady=(4, 0))

    return lbl_header_file, lbl_header_lib, cmb_header_size


# -------------------------------------------------------------------
# Sağ alt panel: log + önizleme + progress/istatistik
# -------------------------------------------------------------------
def _build_bottom_panel(
    parent: ttk.Frame,
    progress_var: tk.DoubleVar,
    stats_total: tk.IntVar,
    stats_fixed: tk.IntVar,
    stats_failed: tk.IntVar,
    stats_processed: tk.IntVar,
    commands: CommandBindings,
):
    bottom_frame = ttk.Frame(parent)
    bottom_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
    bottom_frame.grid_rowconfigure(0, weight=1)
    bottom_frame.grid_columnconfigure(0, weight=1)
    bottom_frame.grid_columnconfigure(1, weight=0)

    # Log alanı
    log_frame = ttk.LabelFrame(bottom_frame, text="Günlükler", padding=4)
    log_frame.grid(row=0, column=0, sticky="nsew")
    log_frame.grid_rowconfigure(0, weight=1)
    log_frame.grid_columnconfigure(0, weight=1)

    txt_log = scrolledtext.ScrolledText(
        log_frame,
        wrap="word",
        height=18,
    )
    txt_log.grid(row=0, column=0, sticky="nsew")

    # Önizleme alanı
    preview_frame = ttk.LabelFrame(bottom_frame, text="Hızlı Önizleme", padding=4)
    preview_frame.grid(row=0, column=1, sticky="nsw", padx=(8, 0))
    preview_frame.grid_rowconfigure(0, weight=1)
    preview_frame.grid_rowconfigure(1, weight=1)
    preview_frame.grid_rowconfigure(2, weight=0)
    preview_frame.grid_columnconfigure(0, weight=1)

    preview_original_label = ttk.Label(
        preview_frame,
        text="Orijinal",
        anchor="center",
        relief="sunken",
        width=40,
    )
    preview_original_label.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

    preview_repaired_label = ttk.Label(
        preview_frame,
        text="Onarılan",
        anchor="center",
        relief="sunken",
        width=40,
    )
    preview_repaired_label.grid(row=1, column=0, sticky="nsew", pady=(0, 4))

    preview_info_label = ttk.Label(
        preview_frame,
        text="Henüz önizleme yok.",
        anchor="center",
        wraplength=260,
    )
    preview_info_label.grid(row=2, column=0, sticky="ew")

    # Alt: progress ve istatistik
    status_frame = ttk.Frame(parent)
    status_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    status_frame.grid_columnconfigure(0, weight=1)
    status_frame.grid_columnconfigure(1, weight=1)
    status_frame.grid_columnconfigure(2, weight=1)
    status_frame.grid_columnconfigure(3, weight=1)

    progress_bar = ttk.Progressbar(
        status_frame,
        variable=progress_var,
        maximum=100.0,
    )
    progress_bar.grid(row=0, column=0, columnspan=4, sticky="ew")

    lbl_total = ttk.Label(status_frame, textvariable=stats_total)
    lbl_fixed = ttk.Label(status_frame, textvariable=stats_fixed)
    lbl_failed = ttk.Label(status_frame, textvariable=stats_failed)
    lbl_processed = ttk.Label(status_frame, textvariable=stats_processed)

    ttk.Label(status_frame, text="Toplam:").grid(row=1, column=0, sticky="e", padx=(0, 2))
    lbl_total.grid(row=1, column=1, sticky="w")

    ttk.Label(status_frame, text="Onarılan:").grid(row=1, column=2, sticky="e", padx=(0, 2))
    lbl_fixed.grid(row=1, column=3, sticky="w")

    ttk.Label(status_frame, text="Başarısız:").grid(row=2, column=0, sticky="e", padx=(0, 2))
    lbl_failed.grid(row=2, column=1, sticky="w")

    ttk.Label(status_frame, text="İşlenen:").grid(row=2, column=2, sticky="e", padx=(0, 2))
    lbl_processed.grid(row=2, column=3, sticky="w")

    return txt_log, preview_original_label, preview_repaired_label, preview_info_label
