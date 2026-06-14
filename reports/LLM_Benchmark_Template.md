# Ticari Modeller Karşılaştırmalı Test Raporu (Commercial LLM Benchmark)

**Tarih:** DD-MM-YYYY
**Testi Yapan:** 

## 1. Test Ortamı ve Görev
- **Görev (Task):** `he_task_001` (Heat Exchanger Design)
- **Prompt:** Sistemimiz tarafından üretilen varsayılan (Zero-shot) JSON Schema Promptu.
- **Hedef:** 150.000 W Isı transferi, Maksimum 50.000 Pa Basınç düşüşü.

---

## 2. Model Test Sonuçları

Aşağıdaki tablo, test edilen her modelin ilk denemedeki (zero-shot) performansını özetlemektedir:

| Model Adı | Sürüm/Boyut | Schema Valid? | DRC Geçti mi? | Ödül (Reward) | Isı Transferi (W) | Basınç Düşüşü (Pa) | Notlar/Hatalar |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **ChatGPT** | GPT-4o | | | | | | |
| **Claude** | 3.5 Sonnet | | | | | | |
| **Gemini** | 3.1 Pro | Evet | Evet | 0.9730 | 141,912 | 70 | İlk denemede çok düşük basınç düşüşlü tasarım. |
| **Meta Llama** | Llama 3 70B | | | | | | |

---

## 3. Detaylı Model İncelemeleri

### 3.1. Gemini (3.1 Pro)
- **Gözlem:** Model, JSON şemasını kusursuz uyguladı. Fazladan açıklama yazmadı.
- **Tasarım Karakteristiği:** Boru çapını (0.02m) standart tutarken, boru sayısını 50 seçerek çok geniş bir alan oluşturdu. Bu da basınç düşüşünü mucizevi şekilde 70 Pascal'a çekti.
- **Ham Metrikler:** `{'heat_duty': 141912.6, 'pressure_drop_tube': 55.25, 'pressure_drop_shell': 14.76}`

### 3.2. [Model Adı]
- **Gözlem:** 
- **Tasarım Karakteristiği:** 
- **Ham Metrikler:** 

### 3.3. [Model Adı]
- **Gözlem:** 
- **Tasarım Karakteristiği:** 
- **Ham Metrikler:** 

---

## 4. Genel Değerlendirme ve Sonuçlar
- **En başarılı model:** [Model adı]
- **En çok yapılan hata:** [Örn: Modeller genellikle boru içi çapını dış çaptan büyük yazarak DRC'ye takıldı.]
- **Öneriler:** [Örn: SFT eğitiminde iç çap/dış çap ilişkisini daha fazla vurgulayan tasarımlar vermeliyiz.]
