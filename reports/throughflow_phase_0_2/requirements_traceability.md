# Gereksinim–kanıt matrisi

Etiketler ürün hedefini daraltmaz. `core` ilk gerekli sözleşme; `advanced` kullanıcının çok kademe/gerçekçi fizik hedefi; `experimental` henüz fiziksel kabulü olmayan araştırma yoludur. Bu fazda hiçbir throughflow özelliğine production `supported` etiketi verilmedi.

| ID | İstek | Hedef | Bu fazdaki kanıt | Açık iş |
|---|---|---|---|---|
| R01 | Repo içinden basit çağrı | core | HE baseline, NASA `turbine1_1_fixed_streamlines` | Registry/public throughflow API Faz 3–5 |
| R02 | Eğitim reposundan çağrı | core | `packaging_baseline.json`: HE wheel, dış cwd, isolated import, aynı skor/metrik | Gerçek throughflow consumer/worker testi Faz 9 |
| R03 | Çok kademe | advanced | `turbine2_*_fixed_streamlines`, `eee_hpt_original`; başarısız `followup_compressor10_openpyxl` | İki makine türünde fizik kabulü; B03/B06 |
| R04 | 1 streamline'dan yüksek çözünürlüğe | core/advanced | n=1/3/5/9/17 taraması; 17'de debi sapması | B03/B05, çözünürlük yakınsama çalışması |
| R05 | Sabit kayıpla sınırlanmama | advanced | TD2/KO/AM/Craig/Traupel/Aungier hataları; DiffusionLoss dönüşü | B04: basit ramp yeterli kabul edilmedi |
| R06 | Tekrarlanabilir eğitim ödülü | core | HE birebir tekrar; türbin repeat/ABA; kompresörde ikinci solve arızası | B05/B07, deterministik sonuç/zaman ayrımı |
| R07 | NASA güncellemelerine dayanma | core | SHA + paket ve asset manifest'leri, kaynak değişikliği kontrolü | Uyumluluk matrisi, sürüm geçiş politikası/CI Faz 9–11 |
| R08 | Lisans sınırları | core | NASA README, kaynak/wheel eksikleri, bağımlılık envanteri | B01, dağıtım adayı lisans incelemesi |
| R09 | Soğutma/karşı dönüş/radyal/off-design | experimental | İlgili probe kayıtları ve sınırları README'de | Fizik referansları; geometri koruma; tasarım dışı harita |
| R10 | Mevcut HE'yi bozmama | core | 222 başlangıç testi, 5 regression vaka, wheel tüketimi | İleri fazlarda aynı baseline'ı koru |

Tam senaryo kimlikleri ve kaynak/ref/model parametreleri `probes/<profile>/<case>.json` içinde. Yalnız `completed` durumuna bakarak supported sınıfına terfi yoktur. Eğitim kullanılabilirliği için fiziksel referans, model geçerliliği ve residual kabulü birlikte gereklidir.
