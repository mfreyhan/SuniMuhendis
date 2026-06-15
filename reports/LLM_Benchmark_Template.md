# Ticari Modeller Karşılaştırmalı Test Raporu (Commercial LLM Benchmark)

**Tarih:** 15-06-2026
**Testi Yapan:** 

## 1. Test Ortamı ve Görev
- **Görev (Task):** `he_task_001` (Heat Exchanger Design)
- **Simülatör Sürümü:** V2 (Etkinlik, Maliyet, Boru Titreşimi ve Duvar Hızı kontrolleri eklendi)
- **Görev Koşulları:** 2.5 kg/s Yüksek Debi, %30 Cost Ağırlığı
- **Prompt:** Sistemimiz tarafından üretilen varsayılan (Zero-shot) JSON Schema Promptu.
- **Hedef:** 150.000 W Isı transferi, Boru ve Gövde için ayrı ayrı 50.000 Pa Maksimum Basınç düşüşü, Maksimum Etkinlik, Minimum Maliyet, ve Sıfır Mekanik Uyarı.

---

## 2. Model Test Sonuçları

Aşağıdaki tablo, test edilen her modelin ilk denemedeki (zero-shot) performansını özetlemektedir:

| Model Adı | Sürüm | Isı (W) | Heat R. | DP Tube (Pa) | Tube R. | DP Shell (Pa) | Shell R. | Eff. (%) | Eff. R. | Cost ($/y) | Cost R. | Uyarı | Penalty | **Total R.** | Notlar |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **GPT** | 5.5 Pro | 189,690 | 1.0000 | 11,468 | 1.0000 | 4,436 | 1.0000 | 30.2 | 0.3023 | 788 | 1.0000 | 4 | 0.6000 | **0.5163** | Son derece ucuza kaçtı (Sadece 16 boru) ancak 4 uyarı yedi! |

*(Not: Tablodaki skorlar, ilgili alanın normalize edilmiş (0-1 arası) alt ödüllerini ifade etmektedir.)*

---

## 3. Detaylı Model İncelemeleri

### 3.1. GPT (5.5 Pro)
- **Gözlem:** Debilerin 2.5 kg/s'ye çıkartıldığı ve Cost ağırlığının %30'a fırlatıldığı yeni görev simülasyonunda test edilen ilk model.
- **Tasarım Karakteristiği:** Model, maliyetin %30 ağırlığa çıktığını prompt'ta görür görmez gözünü karartıp **maliyeti minimuma indirmek için sadece 16 borulu ve 0.18m çapında** ufacık bir ısı değiştirici tasarladı. Maliyeti 788 $/yıl gibi şaka gibi bir rakama düşürüp Cost'tan **tam puan** (1.000) aldı. Ayrıca yüksek debinin de etkisiyle çok yüksek hıza ulaşan su sayesinde hedefin (150kW) bile üstüne çıkarak (189.690 W) Isı'dan da **tam puan** aldı. ANCAK; o devasa debiyi (2.5 kg/s) sadece 16 tane incecik boruya sıkıştırmanın faturası çok ağır oldu: Sistem boru hızı ve mekanik riskler sebebiyle tam **4 adet kritik uyarı** verdi. Sırf maliyeti kırmak için güvenliği tamamen çöpe attığından penalty_factor (0.60) üzerinden skoru **0.5163**'e çakıldı.
- **Ham Metrikler:** `{'heat_duty_W': 189690.2, 'dp_tube_Pa': 11468.8, 'dp_shell_Pa': 4436.3, 'effectiveness': 0.302, 'cost_annualised_USD_per_yr': 788.5, 'num_warnings': 4.0}`

## 4. Genel Değerlendirme ve Sonuçlar
- **En başarılı model:** (Henüz yeterli model test edilmedi)
- **En çok yapılan hata:** Mekanik sınır ihlalleri (Titreşim, hız limitleri vb.)
- **Öneriler:** LLM'lerin sadece akışkanlar dinamiğini değil, mekanik titreşim/hız limitlerini de dikkate almasını sağlayacak daha spesifik SFT verisi üretilmeli.
