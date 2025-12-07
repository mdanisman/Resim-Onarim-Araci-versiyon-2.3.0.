## 📸 Gelişmiş Resim Onarım Aracı
Bu araç, bozuk veya kısmen hasar görmüş JPEG ve PNG dosyalarını onarmak için geliştirilmiş, profesyonel seviyede algoritmalar kullanan bir masaüstü uygulamasıdır. Tek bir akıcı arayüzde birden fazla onarım tekniğini ve gelişmiş bir çıktı skorlama sistemini birleştirir.

## ✨ Temel Özellikler
### JPEG Onarımı
- Marker Onarımı: Yanlış yerleştirilmiş SOI (Start of Image) ve EOI (End of Image) işaretleyicilerini düzeltir.
- Smart Header V3: Bozuk JPEG dosyalarında DQT / DHT tablolarını referans bir header veya dinamik bir Header Kütüphanesi kullanarak yeniden inşa eder.
- Partial Top Recovery: Dosyanın üst kısmındaki veri kayıplarını farklı oranlarda deneyerek kurtarmaya çalışır.
- EXIF Thumbnail'den Kurtarma: Dosya içinde mevcut olan küçük EXIF önizleme resmini çıkarır ve isteğe bağlı olarak büyütür (Upscale).
- Gömülü JPEG Taraması: Dosya içindeki gizli veya gömülü JPEG verilerini tarayarak çıkarır.

### PNG Onarımı
- PNG CRC Düzeltme: CRC (Cyclic Redundancy Check) hatalarını normal veya agresif (AGGR) modda düzelterek veri bütünlüğünü sağlar.
- Ancillary Chunk Atlama: Hatalı ek (ancillary) veri bloklarının isteğe bağlı olarak atlanmasıyla onarım sağlar.

### Genel Yöntemler ve Dönüştürme
- Pillow ile Yeniden Kaydetme: Basit format hatalarını düzeltmek için dosyayı yeniden yazar.
- PNG Roundtrip: Dosyayı geçici olarak PNG formatına çevirip tekrar orijinal formata döndürerek bozulmaları temizler.
- FFmpeg ile Yeniden Encode: FFmpeg kuruluysa dosyayı yeniden kodlar (JPEG/PNG için farklı kalite ön ayarları mevcuttur).

## 💡 Akıllı Skorlama Sistemi
Onarılan her bir çıktı, Akıllı Skorlama mekanizmasıyla analiz edilir ve puanlanır. Böylece kullanıcıya en iyi onarım sonucu sunulur:
- Detay / Entropi Analizi
- Keskinlik Tahmini
- Gri Oranı (tek tonlu veya bozulmuş görüntü tespiti)
- Kırpılmış Veri İhtimali (truncation)
- Çözünürlük ve dosya boyutu dengesi

## ⚙️ Arayüz ve Kullanılabilirlik
Uygulama, tüm ayarları tek bir akıcı pencerede sunar:
- Toplu işlem: Tek bir dosyayı veya komple bir klasörü onarma
- Hızlı önizleme: Orijinal ve en iyi onarım çıktısını yan yana gösterme
- Log yönetimi: İşlem kayıtlarını anlık olarak görüntüleme ve TXT/CSV'ye aktarma
- Çıktı klasörü: Onarılan dosyaları otomatik `repaired_images` alt klasörüne veya özel bir klasöre kaydetme

## ⬇️ Kurulum ve Çalıştırma
Bu uygulamayı çalıştırmak için daha önce Python kurmuş olmanız gerekmez. Aşağıdaki adımları izleyerek programı hemen kullanmaya başlayabilirsiniz.
### 1. 📦 Program Klasörünü Hazırlama
- İndirdiğiniz ZIP dosyasını açın.
- Klasörü sabit bir yere (ör. Masaüstü veya `C:\Resim Onarım Aracı`) çıkarın.
- Klasörde `Gereksinimler.txt` ve `Kurulumu_Baslat.bat` dosyalarının bulunduğundan emin olun.

### 2. 🛠 Tek Tıkla Kurulumu Başlatma
- Klasör içindeki `Kurulumu_Baslat.bat` dosyasına sağ tıklayın ve **Yönetici olarak çalıştırın**.
- Komut dosyası Python'u indirir, sistem PATH'ine ekler ve `Gereksinimler.txt` içindeki Python kütüphanelerini otomatik yükler.
- Kurulum bittiğinde komut penceresi kapanır.

### 3. ▶️ Programı Çalıştırma
- Program klasörüne dönün ve `Baslat.cmd` dosyasına çift tıklayın.
- Resim Onarım Aracı penceresi açılacaktır.

## 🛠 FFmpeg Kurulumu (İsteğe Bağlı ama Önerilir)
- Program açıldığında ffmpeg bulunamadı uyarısı görebilirsiniz; yeniden encode yöntemleri için FFmpeg gereklidir.
- ffmpeg.org gibi güvenilir bir kaynaktan FFmpeg'in Windows sürümünü indirin ve `ffmpeg.exe` dosyasını çıkarın.
- `ffmpeg.exe` dosyasını programın ana klasörüne (ör. `Baslat.cmd` ile aynı konum) kopyalayın.
- Programı tekrar çalıştırdığınızda arayüzde "FFmpeg bulundu" bilgisini görebilirsiniz.

## 🧑‍💻 Geliştirici Rehberi
Uygulamayı geliştirmek veya katkıda bulunmak için aşağıdaki adımları izleyin. Depoda güncel dokümantasyon dosyaları (`README.md`, `CONTRIBUTING.md`, pip uyumlu `gereksinimler.txt`) bulunduğundan geliştirme sırasında güncel kalmalarına dikkat edin.

### 1) Sanal ortam oluşturma
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **Windows (PowerShell):**
  ```powershell
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- Ortam aktifken `python` ve `pip` komutlarını doğrudan kullanabilirsiniz.

### 2) Bağımlılıkları yükleme (pip)
- Pip'i güncelleyin ve gereksinimleri kurun:
  ```bash
  python -m pip install --upgrade pip
  python -m pip install -r gereksinimler.txt
  ```
- Dosya adı Türkçe olsa da `-r gereksinimler.txt` parametresiyle doğrudan kullanılabilir; Windows kullanıcıları `py -m pip ...` komutunu tercih edebilir.
- **Windows:** PowerShell/CMD'de proje klasöründe `py -m pip install -r gereksinimler.txt`
- **macOS / Linux:** Terminalde proje klasöründe `python3 -m pip install -r gereksinimler.txt`

### 3) Conda ile çalışma
- Pip içeren bir ortam açın ve aynı `gereksinimler.txt` dosyasını kullanın:
  ```bash
  conda create -n resim-onarim python=3.10 pip
  conda activate resim-onarim
  pip install -r gereksinimler.txt
  ```

### 4) Uygulamayı çalıştırma ve test etme
- Arayüzü başlatmak için: `python main.py`
- GUI'yi modül olarak çalıştırmak için: `python -m gui`
- Varsa otomatik testleri çalıştırmak için: `python -m unittest discover`
- Test komutu, `tests/` dizinindeki birim testlerini otomatik yakalayacak şekilde ayarlanmıştır; kapsamlı test yoksa komut hızlı tamamlanır.

## 🤝 Katkıda Bulunma
- Geri bildirim, hata raporu veya yeni özellik önerilerinizi Issue açarak veya Pull Request göndererek paylaşabilirsiniz.
- Sürece dair detaylar için [CONTRIBUTING.md](CONTRIBUTING.md) dosyasına bakın.
