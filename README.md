📸 Gelişmiş Resim Onarım Motoru (Image Repair Engine)
Bu araç, bozuk veya kısmen hasar görmüş JPEG ve PNG dosyalarını onarmak için geliştirilmiş, profesyonel seviyede algoritmalar kullanan bir masaüstü uygulamasıdır. Tek bir akıcı arayüzde birden fazla onarım tekniğini ve gelişmiş bir çıktı skorlama sistemini birleştirir.

✨ Temel Özellikler
JPEG Onarımı
Marker Onarımı: Yanlış yerleştirilmiş SOI (Start of Image) ve EOI (End of Image) işaretleyicilerini düzeltir.

Smart Header V3: Bozuk JPEG dosyalarında DQT / DHT tablolarını (görüntü kalitesini ve renk haritasını belirleyen kritik yapılar) referans bir header veya dinamik bir Header Kütüphanesi kullanarak yeniden inşa eder.

Partial Top Recovery: Dosyanın üst kısmındaki veri kayıplarını farklı oranlarda deneyerek kurtarmaya çalışır.

EXIF Thumbnail'den Kurtarma: Dosya içinde mevcut olan küçük EXIF önizleme resmini çıkarır ve isteğe bağlı olarak büyütür (Upscale).

Gömülü JPEG Taraması: Dosya içindeki gizli veya gömülü JPEG verilerini tarayarak çıkarır.

PNG Onarımı
PNG CRC Düzeltme: CRC (Cyclic Redundancy Check) hatalarını hem normal hem de agresif (AGGR) modda düzelterek veri bütünlüğünü sağlar.

Ancillary Chunk Atlama: Hatalı ek (ancillary) veri bloklarının isteğe bağlı olarak atlanmasıyla onarımı mümkün kılar.

Genel Yöntemler ve Dönüştürme
Pillow ile Yeniden Kaydetme: Basit format hatalarını düzeltmek için popüler Python kütüphanesi Pillow kullanılarak dosyayı yeniden yazar.

PNG Roundtrip: Dosyayı geçici olarak PNG formatına çevirip tekrar orijinal formata döndürerek bozulmaları temizler.

FFmpeg ile Yeniden Encode: Kurulumluysa, güçlü FFmpeg aracını kullanarak dosyayı yeniden kodlar (JPEG/PNG için farklı kalite ön ayarları mevcuttur).

💡 Akıllı Skorlama Sistemi
Programın en güçlü özelliği, onarılan her bir çıktıyı analiz eden ve puanlayan Akıllı Skorlama mekanizmasıdır. Bu skorlar sayesinde en iyi onarım sonucu kullanıcıya sunulur.

Detay / Entropi Analizi

Keskinlik Tahmini

Gri Oranı (Tek tonlu veya bozulmuş görüntü tespiti)

Kırpılmış Veri İhtimali (Truncation)

Çözünürlük ve Dosya Boyutu Dengesi

⚙️ Arayüz ve Kullanılabilirlik
Uygulama, tüm ayarları tek bir akıcı pencerede sunar:

Toplu İşlem: Tek bir dosyayı veya komple bir klasörü ve içindeki tüm resimleri onarma.

Hızlı Önizleme: Orijinal dosya ile Akıllı Skorlama ile seçilen En İyi Onarım çıktısını yan yana gösterir.

Log Yönetimi: Tüm işlem kayıtları ve hatalar anlık olarak log penceresinde gösterilir ve TXT / CSV formatında dışa aktarılabilir.

Çıktı Klasörü: Onarılan dosyaların otomatik olarak girdi klasöründe oluşturulan repaired_images alt klasörüne veya özel bir klasöre kaydedilme seçeneği.

⬇️ Kurulum ve Çalıştırma
Normal Kullanıcı (Python Bilgisi Gerekmez)
Bu yöntem, uygulamayı indirdiğinizde hazır bir paket (örneğin bir ZIP dosyası) aldığınızı varsayar.

Program Klasörünü Hazırlama: Programın ZIP dosyasını indirin ve örneğin C:\ImageRepairEngine gibi bir klasöre çıkarın. Klasörde Başlat.cmd, gui.py, utils.py, repair_engine.py gibi dosyalar bulunmalıdır.

FFmpeg Kurulumu (Önerilen): FFmpeg olmadan da program çalışır, ancak FFmpeg ile yeniden encode özelliği pasif kalır.

ffmpeg.org adresinden ffmpeg.exe dosyasını indirin.

İndirdiğiniz ffmpeg.exe dosyasını direkt olarak program klasörüne (C:\ImageRepairEngine\) kopyalayın. Program bu dosyayı otomatik olarak tanıyacaktır.

Çalıştırma: Program klasöründeki Başlat.cmd dosyasına çift tıklayın. Uygulama penceresi açılacaktır.

Geliştiriciler İçin (Kaynaktan Çalıştırma)
Projeyi klonlayıp Python ortamında çalıştırmak isteyen ileri düzey kullanıcılar için:

Gereksinimler: Sisteminizde Python 3.10 veya üzeri kurulu olmalıdır.

Klonlama ve Ortam Hazırlığı:

Bash

git clone [REPO_ADRESİNİZ]
cd image-repair-engine

# Sanal ortam oluşturma ve etkinleştirme (önerilir)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate # macOS/Linux

# Bağımlılıkları yükleme
pip install -r requirements.txt
Çalıştırma:

Bash

python gui.py
📖 Kullanım Senaryosu (Özet)
Uygulamayı Başlat.cmd (Normal Kullanıcı) veya python gui.py (Geliştirici) ile çalıştırın.

Sol üst panelden Çıktı Klasörü modunu seçin.

Sağ paneldeki Onarım Yöntemleri bölümünden kullanmak istediğiniz algoritmaları (Smart Header, FFmpeg, Marker vb.) işaretleyin.

Header Library kullanmak istiyorsanız, referans bir klasör seçerek kütüphaneyi oluşturun.

"Tek Resim Seç ve Onar" veya "Klasör Seç ve Tümünü Onar" butonlarından birini kullanarak işlemi başlatın.

İşlem bittiğinde, sonuçları alt paneldeki Hızlı Önizleme ve log penceresinden kontrol edin. Onarılan dosyalar, belirlediğiniz çıktı klasöründe olacaktır.

🤝 Katkıda Bulunma
Geri bildirimleriniz, hata raporlarınız ve yeni özellik önerileriniz değerlidir! Lütfen bir Issue açarak veya bir Pull Request göndererek katkıda bulunun.
