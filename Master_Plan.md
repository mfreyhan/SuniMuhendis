# AI Agent Yönergesi: RL-Destekli Mühendislik Tasarımı Yapabilen LLM

## 0. Orijinal Proje Bağlamı ve Korunması Gereken Bilgiler

Bu doküman, ilk proje tanımı dosyasındaki araştırma fikrini koruyarak genişletilmiş bir AI-agent uygulama yönergesidir. Agent sistemi bu bölümü yalnızca arka plan bilgisi olarak değil, proje hedeflerini ve önceliklerini belirleyen bağlayıcı kapsam bilgisi olarak yorumlamalıdır.

### 0.1. Ekip Bilgisi

Proje iki kişilik bir ekip tarafından yürütülecektir:

```text
- Bir ekip üyesi yapay zeka / makine öğrenmesi / LLM-RL sistemleri alanında uzmandır.
- Diğer ekip üyesi uçak mühendisliği, aerospace sistemleri, turbomachinery, uçak, motor ve roket sistemleri alanlarında deneyimlidir.
```

Bu ekip yapısı nedeniyle proje hem modern LLM/RL yöntemlerini hem de gerçek mühendislik tasarımı sezgisini bir araya getirmelidir. Agent, kod ve mimari kararlarında bu iki yönlü uzmanlığı destekleyecek şekilde ilerlemelidir.

### 0.2. Orijinal Proje Fikri

Orijinal fikir şudur:

```text
LLM bir mühendislik tasarım problemine ait parametreleri üretir.
Bu parametreler bir simülasyon ortamına beslenir.
Simülasyon sonuçları performans metriklerine çevrilir.
Performans metriklerinden reward hesaplanır.
Reward sinyali ile LLM pekiştirmeli öğrenme yoluyla güncellenir.
Döngü tekrarlandıkça model daha iyi tasarımlar üretmeyi öğrenir.
```

Bu dokümandaki bütün mimari kararlar bu ana paradigmayı korumalıdır.

Özellikle şu ayrım korunmalıdır:

```text
LLM = tasarımcı
Simulator = evaluator / hakem
Reward function = öğrenme sinyali
DRC = simülatör öncesi güvenlik ve geçerlilik filtresi
```

### 0.3. Referans Çalışma

Bu projenin ana ilham kaynağı aşağıdaki çalışmadır:

```text
Simonds, T. (2025). LLMs for Engineering: Teaching Models to Design High Powered Rockets.
arXiv:2504.19394.
```

Orijinal proje tanımında bu çalışma şu nedenle referans alınmıştır:

```text
- Çalışmada RocketPy simülatörü kullanılmıştır.
- GRPO ile 7B parametreli bir model eğitilmiştir.
- Model, yüksek güçlü roket tasarımında foundation modelleri ve insan uzmanları geçmiştir.
- Bu proje de aynı LLM + simulator + reward + RL paradigmasını başka mühendislik problemlerine taşımayı hedefler.
```

Agent bu çalışmayı birebir kopyalanacak bir mimari olarak değil, temel araştırma paradigmasını gösteren referans örnek olarak yorumlamalıdır.

### 0.4. Gerekçelendirme / Reasoning Hedefi

Orijinal proje tanımında yalnızca iyi tasarım üretmek değil, modelin tasarımını gerekçelendirmesi de hedeflenmiştir.

Korunması gereken fikir:

```text
Model rastgele veya bilinçli bir tasarım değişikliği önerir.
Bu değişikliğin fiziksel etkisini tahmin eder.
Örneğin: verim düşer, menzil artar, pressure drop artar, L/D iyileşir.
Simülasyon sonucu bu tahmini doğrularsa model reasoning reward alır.
```

Bu nedenle sistemde `R_reasoning` bileşeni opsiyonel fakat mimari olarak desteklenen bir reward bileşeni olmalıdır.

Başlangıçta reasoning reward kapalı tutulabilir. Ancak veri formatı baştan buna uygun tasarlanmalıdır.

Örnek:

```json
{
  "design_parameters": {
    "...": "..."
  },
  "expected_effects": {
    "heat_transfer_rate": "increase",
    "pressure_drop": "increase",
    "cost": "slightly increase"
  },
  "design_rationale": "Smaller baffle spacing increases shell-side turbulence, improving heat transfer while increasing pressure loss."
}
```

### 0.5. Simülasyon Ortamları İçin Güncel Karar

Güncel strateji, başlangıçta hızlı, kontrol edilebilir, açık kaynak/ücretsiz ve Python'a kolay bağlanabilen simülasyon ortamlarıyla ilerlemektir.

Başlangıç ortamları:

```text
- Heat exchanger design
- UAV wing / airfoil / planform design
- Basit structural / truss design
```

Orta–uzun vadeli aerospace validasyon ortamı:

```text
- NASA turbo-design ve diğer turbomachinery araçları
```

Agent bu kararı şöyle uygulamalıdır:

```text
Başlangıçta karmaşık turbomachinery entegrasyonu yazma.
Önce heat exchanger, UAV wing ve basit structural/truss gibi daha kontrollü ortamları kur.
TurboDesign yalnızca Phase 9 kapsamında ele alınmalıdır.
```

### 0.6. Orijinal Mimari Akış

Orijinal taslak akış korunmalıdır:

```text
[LLM]
  → Tasarım parametrelerini üretir (JSON / dict formatında)
      → [Doğrulama / DRC katmanı]
          → [Simülasyon çalışır]
              → [Performans metrikleri çıkar]
                  → [Reward fonksiyonu hesaplanır]
                      → [RL eğitimi]
                          → [LLM güncellenir]
```

DRC'nin yeri konusunda orijinal dosyada bir not vardı:

```text
DRC'nin simülasyondan önce mi sonra mı geleceği başlangıçta açık bir karardı.
Bazı parametreler simülatörü hata verecek şekilde tetikleyebileceğinden,
güncel mimaride DRC simülasyon öncesi ön-filtreleme olarak konumlandırılmalıdır.
```

Bu nedenle agent, geçersiz tasarımları doğrudan simülatöre göndermemelidir.

### 0.7. Açık Kalan Tasarım Kararları

Orijinal dosyada aşağıdaki kararlar açık bırakılmıştı. Güncel dokümanda bunlar kısmen yönlendirilmiştir, fakat agent bunları hâlâ konfigüre edilebilir tutmalıdır.

| Karar | Orijinal Durum | Güncel Yönlendirme |
|---|---|---|
| Optimizasyon hedefi / reward sinyali | Belirsiz | Environment-specific reward; normalize edilmiş `RewardResult` |
| Hangi LLM base modeli kullanılacak? | Qwen 3.5 27B düşünülebilir | Qwen/Llama/Mistral/Gemma gibi küçük-orta açık modeller desteklenmeli |
| RL algoritması | GRPO | Başlangıçta GRPO; PPO opsiyonel |
| Tasarım parametreleri ve formatı | Ortama göre belirlenecek | Her environment için ayrı JSON schema + Pydantic model |
| DRC yeri | Net değildi | Simülasyon öncesi zorunlu ön-filtreleme |
| Simülatör seçimi | Başlangıçta net değildi | MVP: heat exchanger; demo: UAV wing; TurboDesign: orta–uzun vade |

### 0.8. Projenin Mevcut Aşaması

Orijinal dosyada projenin mevcut aşaması şu şekilde belirtilmiştir:

```text
- 5 girdili ve 3 çıktılı rastgele bir matematiksel model oluşturuldu.
- LLM, prompttaki isterleri yani matematiksel modelin çıktılarını sağlayacak girdiler üretmek üzere eğitildi.
- Test edildiğinde modelin 3 isterden genellikle 2'sini sağladığı görüldü.
- 3'te 3 başarı düzenli olarak sağlanamadı.
```

Olası nedenler:

```text
- Matematiksel model rastgele oluşturulduğu için fiziksel olarak anlamlı olmayabilir.
- İsterler mantıklı veya iyi koşullandırılmış olmayabilir.
```

Bu deney, projenin Phase -1 / Toy Proof-of-Concept aşaması olarak görülmelidir.

Agent, bu bilgiden şu sonucu çıkarmalıdır:

```text
Rastgele matematiksel model yerine fiziksel anlamlı ama hızlı çalışan simülasyon ortamlarına geçilmelidir.
İlk gerçek MVP bu yüzden heat exchanger design olarak seçilmiştir.
```

### 0.9. Orijinal Kapsamın Güncel Kapsamla Birleşimi

Bu doküman orijinal hedefi değiştirmez; onu daha uygulanabilir fazlara ayırır.

Güncel strateji:

```text
1. Orijinal LLM + simulator + reward + RL fikri korunur.
2. Başlangıç daha hızlı ve kontrollü ortamlarla yapılır.
3. Heat exchanger ana MVP olur.
4. UAV wing görsel ve aerospace bağlantılı demo olur.
5. Küçük LLM'ler eğitilir.
6. Ticari LLM'ler benchmark için kullanılır.
7. TurboDesign / turbomachinery orta–uzun vadeli ileri validasyon olarak kalır.
```

---

## Dokümanın Amacı

Bu doküman, Cursor, Antigravity veya benzeri AI agent tabanlı geliştirme ortamlarına doğrudan verilebilecek bir **teknik uygulama yönergesi** olarak hazırlanmıştır.

Amaç, agent'ın yalnızca proje fikrini anlaması değil; hangi sırayla ne kuracağını, hangi dosyaları oluşturacağını, hangi testleri yazacağını, hangi faz tamamlanmadan sonraki faza geçmemesi gerektiğini ve farklı mühendislik simülatörlerini ortak bir mimari altında nasıl yöneteceğini açıkça tarif etmektir.

Bu proje, LLM'lerin mühendislik tasarımı yapabilme kapasitesini fizik tabanlı simülasyonlardan gelen ödül sinyalleriyle geliştirmeyi hedefler. Projede küçük boyutlu açık/yerel LLM'ler eğitilecek; ticari LLM'ler ise yalnızca karşılaştırma ve benchmark için kullanılacaktır.

---

# 0. Agent İçin En Kritik Talimatlar

AI agent aşağıdaki kurallara kesinlikle uymalıdır:

```text
1. Simülatörler kurulmadan LLM entegrasyonuna geçme.
2. Smoke testler yazılmadan reward veya training koduna geçme.
3. Environment interface stabil olmadan ticari LLM veya yerel LLM bağlama.
4. Simülatör kodlarının içine LLM kodu koyma.
5. LLM client kodlarının içine simülatör detayları koyma.
6. Her environment aynı EvaluationResult formatını dönmeli.
7. Her reward fonksiyonu farklı olabilir fakat aynı RewardResult formatını dönmeli.
8. Tüm reward toplamları normalize edilmiş benzer aralıkta olmalı.
9. Hard constraint'leri DRC'de ele; soft trade-off'ları reward içinde değerlendir.
10. Her faz sonunda test, log ve örnek çıktı üret.
```

Agent hiçbir aşamada "ileride yapılır" diyerek temel testleri atlamamalıdır.

---

# 1. Projenin Kısa Tanımı

Proje, LLM'in mühendislik tasarımı yapmasını sağlayacak bir sistem kurmayı hedefler.

Temel döngü:

```text
Task specification
      ↓
LLM / baseline model
      ↓
Structured design JSON
      ↓
Schema validation
      ↓
Design Rule Check - DRC
      ↓
Physics-based simulator
      ↓
Metrics normalization
      ↓
Reward calculation
      ↓
Logging / dataset / RL update
```

Bu projede LLM bir **tasarımcı**, simülatör ise bir **hakem/evaluator** olarak çalışır.

Simülatörün görevi tasarımı optimize etmek değildir. Simülatör yalnızca verilen tasarımı analiz eder ve objektif mühendislik metrikleri üretir.

---

# 2. Ana Araştırma Sorusu

```text
Bir LLM, yapılandırılmış tasarım parametreleri üreterek ve fizik tabanlı simülasyonlardan gelen reward sinyaliyle eğitilerek, mühendislik açısından geçerli ve performanslı tasarımlar üretmeyi öğrenebilir mi?
```

İkincil araştırma sorusu:

```text
LLM yalnızca iyi tasarım üretmekle kalmayıp, yaptığı tasarım değişikliklerinin fiziksel etkilerini doğru tahmin etmeyi öğrenebilir mi?
```

Örnek reasoning hedefi:

```json
{
  "design_change": "baffle spacing decreased",
  "predicted_effects": {
    "heat_transfer_rate": "increase",
    "pressure_drop": "increase",
    "cost": "slightly increase"
  },
  "rationale": "Smaller baffle spacing increases shell-side turbulence, improving heat transfer but increasing pressure losses."
}
```

---

# 3. Model Kullanım Stratejisi

## 3.1. Eğitilecek Modeller

Bu projede asıl eğitilecek modeller küçük/orta boyutlu açık veya yerel LLM'lerdir.

Muhtemel model aileleri:

```text
- Qwen tabanlı modeller
- Llama tabanlı modeller
- Mistral tabanlı modeller
- Gemma tabanlı modeller
```

Eğitim yaklaşımları:

```text
- SFT
- LoRA / QLoRA
- Rejection sampling + SFT
- GRPO
- PPO
- Reward-weighted supervised fine-tuning
```

Küçük LLM'ler için temel hedefler:

```text
- Valid JSON üretmek
- Schema'ya uymak
- DRC'den geçmek
- Simülasyonda çalışabilecek tasarımlar üretmek
- Ortalama reward'u artırmak
- Tasarım etkilerini doğru tahmin etmek
```

## 3.2. Ticari LLM'ler

Ticari LLM'ler eğitim için değil, benchmark için kullanılacaktır.

Kullanım amaçları:

```text
- Zero-shot tasarım performansını ölçmek
- Few-shot tasarım performansını ölçmek
- Yerel RL-trained model ile karşılaştırmak
- Cost per valid design metriği hesaplamak
- Reasoning kalitesini karşılaştırmak
```

Kural:

```text
Ticari LLM'ler hiçbir ayrıcalıklı evaluator kullanmamalıdır.
Ticari ve yerel LLM'ler aynı task set, aynı JSON schema, aynı DRC, aynı simülatör ve aynı reward fonksiyonuyla değerlendirilmelidir.
```

---

# 4. Faz Bazlı Geliştirme Planı

Bu proje fazlara bölünmelidir. Agent her fazı bitirmeden bir sonraki faza geçmemelidir.

---

## Phase 0 — Repo, Core Interface ve Simülatör Altyapısı

### Amaç

LLM kullanmadan, tüm simülasyon altyapısının temelini oluşturmak.

Bu fazda hiçbir LLM eğitimi yoktur.

### Yapılacaklar

```text
- Repo klasör yapısını oluştur.
- Python environment dosyalarını oluştur.
- BaseEnvironment arayüzünü yaz.
- BaseSimulator arayüzünü yaz.
- BaseRewardFunction arayüzünü yaz.
- Ortak dataclass / Pydantic tiplerini yaz.
- Logging ve cache altyapısını yaz.
- run_simulation.py CLI iskeletini yaz.
- İlk import/smoke test altyapısını kur.
```

### Faz 0 Teslimleri

```text
src/core/types.py
src/core/base_environment.py
src/core/base_simulator.py
src/core/base_reward.py
src/core/cache.py
src/core/logging.py
scripts/run_simulation.py
tests/test_core_interfaces.py
```

### Faz 0 Kabul Kriterleri

```text
- BaseEnvironment import edilebiliyor.
- DummyEnvironment ile evaluate() çalışıyor.
- Invalid schema durumunda controlled EvaluationResult dönüyor.
- DRC failure durumunda simülasyon çağrılmadan reward dönüyor.
- Simulation failure try/except ile yakalanıyor.
- RewardResult her durumda oluşuyor.
```

---

## Phase 1 — Heat Exchanger MVP

### Amaç

İlk gerçek mühendislik ortamını kurmak ve LLM olmadan çalıştırmak.

### Kullanılacak Paketler

```text
ht
fluids
CoolProp
numpy
scipy
pydantic
pytest
```

### Yapılacaklar

```text
- ht, fluids, CoolProp paketlerini kur.
- Import smoke test yaz.
- HeatExchangerEnv oluştur.
- HeatExchangerSimulator oluştur.
- HeatExchangerReward oluştur.
- Heat exchanger schema yaz.
- Heat exchanger DRC yaz.
- Örnek task JSON oluştur.
- Örnek valid design JSON oluştur.
- run_simulation.py ile LLM'siz simülasyon çalıştır.
- Sonucu normalized EvaluationResult JSON olarak kaydet.
```

### Faz 1 Teslimleri

```text
src/environments/heat_exchanger/env.py
src/environments/heat_exchanger/simulator.py
src/environments/heat_exchanger/schema.py
src/environments/heat_exchanger/drc.py
src/environments/heat_exchanger/reward.py
configs/tasks/heat_exchanger/task_001.json
examples/designs/heat_exchanger_valid_001.json
examples/outputs/heat_exchanger_valid_001_result.json
tests/test_heat_exchanger_imports.py
tests/test_heat_exchanger_smoke.py
tests/test_heat_exchanger_reward.py
```

### Faz 1 Kabul Kriterleri

```text
- Elle yazılmış valid design DRC'den geçiyor.
- Simülasyon success=True dönüyor.
- heat_duty_W, pressure_drop, area gibi metrikler NaN/inf değil.
- Reward hesaplanıyor.
- Aynı input iki kez çalıştırıldığında aynı sonuç dönüyor.
- Invalid design simülatörü çökertmeden kontrollü hata/reward dönüyor.
```

---

## Phase 2 — LLM'siz Baseline ve Dataset Üretimi

### Amaç

Küçük LLM eğitimine başlamadan önce baseline performans ve SFT için örnek veri üretmek.

### Yapılacaklar

```text
- Random design sampler yaz.
- Rule-based heuristic sampler yaz.
- Latin hypercube sampler yaz.
- İsteğe bağlı Bayesian optimization baseline yaz.
- En az 100 valid/invalid heat exchanger denemesi üret.
- Her denemeyi simüle et ve logla.
- Reward dağılımını raporla.
- Başarılı tasarımları SFT veri seti için ayır.
```

### Faz 2 Teslimleri

```text
src/baselines/random_sampler.py
src/baselines/heuristic_sampler.py
src/baselines/latin_hypercube_sampler.py
scripts/run_baseline.py
logs/baselines/heat_exchanger/
datasets/sft/heat_exchanger_initial.jsonl
reports/phase_2_heat_exchanger_baseline.md
```

### Faz 2 Kabul Kriterleri

```text
- En az 100 tasarım simüle edilmiş.
- JSON logları oluşmuş.
- Valid design rate hesaplanmış.
- Mean reward, best reward, median reward hesaplanmış.
- SFT için başarılı örnekler ayrılmış.
```

---

## Phase 3 — Model Client Interface ve İlk LLM Entegrasyonu

### Amaç

LLM'leri simülatörlerden bağımsız şekilde sisteme bağlamak.

### Yapılacaklar

```text
- BaseModelClient oluştur.
- DummyRandomClient oluştur.
- HeuristicClient oluştur.
- LocalTransformersClient iskeleti oluştur.
- LocalVLLMClient iskeleti oluştur.
- CommercialLLMClient soyut arayüzü oluştur.
- JSON parser ve JSON repair mekanizması yaz.
- Prompt template yaz.
- LLM olmadan DummyClient ile evaluate_model.py çalıştır.
```

### Faz 3 Teslimleri

```text
src/model_clients/base.py
src/model_clients/dummy_random.py
src/model_clients/heuristic.py
src/model_clients/local_transformers.py
src/model_clients/local_vllm.py
src/model_clients/commercial_base.py
src/prompts/templates.py
src/parsing/json_parser.py
scripts/run_llm_eval.py
tests/test_model_client_interface.py
tests/test_json_parser.py
```

### Faz 3 Kabul Kriterleri

```text
- DummyRandomClient task alıp design JSON üretiyor.
- Üretilen design env.evaluate() ile değerlendiriliyor.
- Model client simülatör detaylarını import etmiyor.
- Simülatörler model client'ları import etmiyor.
- Raw model output loglanıyor.
- Parsed design loglanıyor.
```

---

## Phase 4 — Küçük LLM SFT / LoRA Aşaması

### Amaç

Küçük yerel LLM'e geçerli JSON tasarım üretmeyi öğretmek.

### Yapılacaklar

```text
- Phase 2'deki başarılı tasarımlardan instruction dataset oluştur.
- Prompt-response formatı belirle.
- LoRA / QLoRA eğitim scripti yaz.
- Base model ile SFT modelini karşılaştır.
- JSON valid rate ölç.
- Schema valid rate ölç.
- DRC pass rate ölç.
- Simulation success rate ölç.
```

### Faz 4 Teslimleri

```text
datasets/sft/heat_exchanger_train.jsonl
datasets/sft/heat_exchanger_eval.jsonl
scripts/train_sft.py
scripts/evaluate_sft_model.py
configs/model_configs/sft_config.yaml
reports/phase_4_sft_results.md
```

### Faz 4 Kabul Kriterleri

```text
- SFT eğitimi tamamlanmış.
- Base model ve SFT model aynı task setinde karşılaştırılmış.
- SFT sonrası JSON valid rate artmış.
- SFT sonrası DRC pass rate artmış.
- Sonuçlar raporlanmış.
```

---

## Phase 5 — RL / GRPO Training

### Amaç

Küçük LLM'i simülasyon reward'u ile doğrudan iyileştirmek.

### Yapılacaklar

```text
- Rollout collector yaz.
- Her task için N candidate design üret.
- Her design için schema validation, DRC, simulation, reward çalıştır.
- Reward breakdown logla.
- GRPO veya PPO training pipeline bağla.
- Eğitim boyunca mean reward ve valid design rate takip et.
```

### Faz 5 Teslimleri

```text
src/training/rollout_collector.py
src/training/grpo_trainer.py
src/training/reward_adapter.py
scripts/train_grpo.py
configs/training/grpo_heat_exchanger.yaml
logs/rollouts/
reports/phase_5_rl_results.md
```

### Faz 5 Kabul Kriterleri

```text
- Rollout collector çalışıyor.
- En az bir kısa RL deneyi tamamlanmış.
- Eğitim boyunca reward loglanmış.
- RL-trained model SFT-only modele göre en az bir metrikte iyileşme göstermiş.
```

---

## Phase 6 — Ticari LLM Benchmark

### Amaç

Yerel base, SFT ve RL-trained modelleri ticari LLM'lerle karşılaştırmak.

### Yapılacaklar

```text
- Ticari LLM client implementasyonlarını ekle.
- Aynı task setini ticari LLM'lere ver.
- Zero-shot ve few-shot modları çalıştır.
- Aynı parser, DRC, simülatör ve reward ile değerlendir.
- Cost per valid design hesapla.
- Local RL-trained model ile karşılaştır.
```

### Faz 6 Teslimleri

```text
src/model_clients/openai_client.py
src/model_clients/anthropic_client.py
src/model_clients/gemini_client.py
configs/evaluation/commercial_benchmark.yaml
reports/phase_6_commercial_benchmark.md
```

### Faz 6 Kabul Kriterleri

```text
- Ticari LLM benchmarkı aynı evaluator hattını kullanıyor.
- Ticari modellere özel reward veya schema yok.
- Cost per valid design raporlanmış.
- Local base, local SFT, local RL ve commercial LLM'ler karşılaştırılmış.
```

---

## Phase 7 — UAV Wing / Airfoil Demo

### Amaç

İkinci mühendislik ortamını ekleyerek mimarinin genellenebilirliğini göstermek.

### Kullanılacak Paketler

```text
AeroSandbox
NeuralFoil
numpy
scipy
pydantic
matplotlib
pytest
```

### Yapılacaklar

```text
- AeroSandbox ve NeuralFoil kurulumunu test et.
- UavWingEnv oluştur.
- UavWingSimulator oluştur.
- UavWingReward oluştur.
- Wing schema ve DRC yaz.
- Görselleştirme fonksiyonu ekle.
- Heat exchanger için çalışan model pipeline'ını UAV ortamına uygula.
```

### Faz 7 Teslimleri

```text
src/environments/uav_wing/env.py
src/environments/uav_wing/simulator.py
src/environments/uav_wing/schema.py
src/environments/uav_wing/drc.py
src/environments/uav_wing/reward.py
src/environments/uav_wing/visualization.py
configs/tasks/uav_wing/task_001.json
examples/designs/uav_wing_valid_001.json
tests/test_uav_wing_smoke.py
reports/phase_7_uav_demo.md
```

### Faz 7 Kabul Kriterleri

```text
- UAV valid design simüle ediliyor.
- L/D, stall speed, wing mass gibi metrikler hesaplanıyor.
- Reward hesaplanıyor.
- Kanat geometrisi görselleştirilebiliyor.
- Aynı BaseEnvironment interface'i kullanılıyor.
```

---

## Phase 8 — Multi-Environment Benchmark

### Amaç

Sistemin tek bir mühendislik problemine overfit olmadığını göstermek.

### Eklenebilecek Ortamlar

```text
- Truss / lightweight structure design
- Battery cell / pack design
- Water distribution network design
- Vehicle powertrain design
```

### Yapılacaklar

```text
- En az bir ek environment daha ekle.
- Ortak task formatını koru.
- RewardResult formatını koru.
- Multi-environment evaluation scripti yaz.
- Environment bazlı ve genel metrikleri raporla.
```

### Faz 8 Kabul Kriterleri

```text
- En az üç environment aynı interface ile çalışıyor.
- Aynı model client farklı environment'lara design üretebiliyor.
- Environment-specific reward'lar normalized_total üretiyor.
- Multi-environment rapor oluşuyor.
```

---

## Phase 9 — TurboDesign / Turbomachinery Orta-Uzun Vadeli Validasyon

### Amaç

Sistem olgunlaştıktan sonra turbomachinery tarafına geçmek.

Bu faz başlangıçta yapılmamalıdır.

### Neden Başlangıçta Değil?

```text
- Parametre uzayı daha karmaşık.
- DRC kuralları daha zor.
- Geçersiz tasarım üretme ihtimali yüksek.
- Simülasyon/geometri ilişkisi daha karmaşık.
- LLM/RL altyapısı debug edilmeden bu aşama risklidir.
```

### Muhtemel Araçlar

```text
NASA turbo-design
NASA pyturbo-aero
TurboDesigner
TurboFlow
TURBIGEN
SU2
```

### Bu Faza Geçiş Şartları

```text
- Heat exchanger MVP stabil çalışıyor.
- UAV demo çalışıyor.
- En az bir küçük LLM valid design üretebiliyor.
- RL pipeline çalışıyor.
- Logging ve caching stabil.
- En az iki environment benchmark edilmiş.
```

---

---

# Orijinal Dosyadan Korunacak Minimum Bilgi Kontrol Listesi

Agent veya geliştirici dokümanda sadeleştirme yaparsa aşağıdaki bilgileri silmemelidir:

```text
- İki kişilik ekip bilgisi
- LLM + RL + simulator + reward ana paradigması
- Simonds 2025 / RocketPy / GRPO referans motivasyonu
- Modelin tasarımını gerekçelendirmesi hedefi
- TurboDesign'ın orta–uzun vadeye bırakılması
- DRC'nin simülasyon öncesi ön-filtre olması gerektiği
- Açık tasarım kararları tablosu
- 5 girdili / 3 çıktılı toy model deneyi ve buradan çıkarılan ders
- Küçük yerel LLM'lerin eğitileceği, ticari LLM'lerin benchmark için kullanılacağı
```

Bu bilgiler proje motivasyonu ve kapsamını belirlediği için korunmalıdır.

---

# 5. Önerilen Klasör Yapısı

Agent repo yapısını aşağıdaki gibi kurmalıdır:

```text
project/
  pyproject.toml
  README.md

  requirements/
    base.txt
    dev.txt
    simulators_heat_exchanger.txt
    simulators_uav.txt
    simulators_structures.txt
    simulators_battery.txt
    simulators_water.txt
    llm_local.txt
    llm_api.txt

  src/
    core/
      types.py
      base_environment.py
      base_simulator.py
      base_reward.py
      cache.py
      logging.py
      config.py

    environments/
      heat_exchanger/
        env.py
        simulator.py
        schema.py
        drc.py
        reward.py

      uav_wing/
        env.py
        simulator.py
        schema.py
        drc.py
        reward.py
        visualization.py

      truss/
        env.py
        simulator.py
        schema.py
        drc.py
        reward.py

      battery/
        env.py
        simulator.py
        schema.py
        drc.py
        reward.py

      water_network/
        env.py
        simulator.py
        schema.py
        drc.py
        reward.py

    model_clients/
      base.py
      dummy_random.py
      heuristic.py
      local_transformers.py
      local_vllm.py
      llama_cpp.py
      commercial_base.py
      openai_client.py
      anthropic_client.py
      gemini_client.py

    prompts/
      templates.py
      examples.py

    parsing/
      json_parser.py
      json_repair.py

    baselines/
      random_sampler.py
      heuristic_sampler.py
      latin_hypercube_sampler.py
      bayesian_optimization.py

    training/
      rollout_collector.py
      sft_dataset.py
      grpo_trainer.py
      ppo_trainer.py
      reward_adapter.py

    evaluation/
      evaluate_model.py
      compare_models.py
      metrics.py
      plots.py

  scripts/
    run_simulation.py
    run_baseline.py
    run_llm_eval.py
    train_sft.py
    train_grpo.py
    run_commercial_benchmark.py

  configs/
    tasks/
      heat_exchanger/
      uav_wing/
      truss/
      battery/
      water_network/

    reward_weights/
      heat_exchanger.yaml
      uav_wing.yaml
      truss.yaml
      battery.yaml
      water_network.yaml

    model_configs/
    training/
    evaluation/

  examples/
    designs/
    outputs/

  datasets/
    sft/
    rl/

  logs/
    simulations/
    rollouts/
    llm_outputs/
    baselines/

  reports/

  tests/
    test_core_interfaces.py
    test_heat_exchanger_smoke.py
    test_uav_wing_smoke.py
    test_reward_functions.py
    test_json_parser.py
```

---

# 6. Core Architecture

## 6.1. BaseEnvironment

Tüm mühendislik ortamları `BaseEnvironment` sınıfından türemelidir.

Public entry point:

```python
result = env.evaluate(task, design)
```

`evaluate()` methodu aşağıdaki sırayı takip etmelidir:

```text
1. Schema validation
2. DRC
3. Simulation
4. Metrics normalization
5. Reward calculation
6. Logging-compatible EvaluationResult return
```

Örnek iskelet:

```python
class BaseEnvironment:
    environment_name: str = "base"

    def evaluate(self, task: dict, design: dict) -> EvaluationResult:
        schema_result = self.validate_schema(task, design)

        if not schema_result.passed:
            reward = self.reward_for_invalid_schema(schema_result)
            return EvaluationResult(
                environment_name=self.environment_name,
                task=task,
                design=design,
                schema_validation=schema_result,
                drc_result=DRCResult(passed=False),
                simulation_result=None,
                reward_result=reward,
                status="schema_failed",
            )

        drc_result = self.run_drc(task, design)

        if not drc_result.passed:
            reward = self.reward_for_drc_failure(drc_result)
            return EvaluationResult(
                environment_name=self.environment_name,
                task=task,
                design=design,
                schema_validation=schema_result,
                drc_result=drc_result,
                simulation_result=None,
                reward_result=reward,
                status="drc_failed",
            )

        try:
            simulation_result = self.run_simulation(task, design)
        except Exception as exc:
            simulation_result = SimulationResult(
                simulation_success=False,
                simulator_name=self.environment_name,
                metrics={},
                warnings=[str(exc)]
            )

        reward = self.compute_reward(task, design, simulation_result)

        return EvaluationResult(
            environment_name=self.environment_name,
            task=task,
            design=design,
            schema_validation=schema_result,
            drc_result=drc_result,
            simulation_result=simulation_result,
            reward_result=reward,
            status="success" if simulation_result.simulation_success else "simulation_failed",
        )
```

## 6.2. BaseSimulator

Simülasyon hesapları `BaseSimulator` sınıfı üzerinden yapılmalıdır.

```python
class BaseSimulator:
    simulator_name: str = "base_simulator"

    def run(self, task: dict, design: dict) -> SimulationResult:
        raise NotImplementedError
```

Önemli kural:

```text
Simulator sınıfları LLM client import etmemelidir.
Simulator sınıfları sadece fiziksel/mühendislik hesapları yapmalıdır.
```

## 6.3. BaseRewardFunction

Her ortam kendi reward sınıfına sahip olmalıdır.

```python
class BaseRewardFunction:
    reward_name: str = "base_reward"

    def compute(
        self,
        task: dict,
        design: dict,
        simulation_result: SimulationResult
    ) -> RewardResult:
        raise NotImplementedError
```

Örnekler:

```text
HeatExchangerReward
UavWingReward
TrussReward
BatteryReward
WaterNetworkReward
TurboDesignReward
```

---

# 7. Ortak Veri Tipleri

Agent `src/core/types.py` içinde aşağıdaki tipleri tanımlamalıdır.

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DRCResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    simulation_success: bool
    simulator_name: str
    metrics: dict[str, float]
    constraint_violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    runtime_seconds: float = 0.0
    raw_output: dict[str, Any] | None = None


@dataclass
class RewardResult:
    total: float
    normalized_total: float
    breakdown: dict[str, float]
    penalties: dict[str, float] = field(default_factory=dict)
    objective_scores: dict[str, float] = field(default_factory=dict)
    constraint_satisfaction: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    environment_name: str
    task: dict[str, Any]
    design: dict[str, Any]
    schema_validation: ValidationResult
    drc_result: DRCResult
    simulation_result: SimulationResult | None
    reward_result: RewardResult
    status: str
```

Bu tipler tüm environment'larda ortak kullanılmalıdır.

---

# 8. Reward Mimarisi

## 8.1. Temel Prensip

Farklı fiziksel sistemler farklı reward fonksiyonlarına sahip olabilir. Bu beklenen ve doğru bir durumdur.

Ancak tüm reward fonksiyonları aynı `RewardResult` formatını döndürmelidir.

```text
Heat exchanger reward farklıdır.
UAV wing reward farklıdır.
Truss reward farklıdır.
Battery reward farklıdır.
Water network reward farklıdır.

Ama hepsi RewardResult döndürür.
```

RL tarafı yalnızca şu değeri kullanmalıdır:

```python
reward = result.reward_result.normalized_total
```

Analiz ve raporlama tarafı ise breakdown kullanabilir:

```python
result.reward_result.breakdown
result.reward_result.penalties
result.reward_result.objective_scores
```

## 8.2. Reward Ölçek Normalizasyonu

En önemli risk, farklı environment'larda reward ölçeklerinin kopmasıdır.

Yanlış örnek:

```text
Heat exchanger reward: 0 ile 1 arası
UAV wing reward: -50 ile +300 arası
Truss reward: -10000 ile 0 arası
```

Bu kabul edilemez.

Tüm environment'lar için önerilen normalize reward aralığı:

```text
Geçersiz JSON:                 -1.0
Schema failure:                -1.0
DRC failure:                   -0.8
Simulation failure:            -1.0
Kötü ama geçerli tasarım:       -0.2 ile 0.2
Orta tasarım:                   0.0 ile 0.5
İyi tasarım:                    0.5 ile 0.9
Çok iyi tasarım:                0.9 ile 1.0
İstisnai tasarım:               maksimum 1.2
```

Agent, her reward fonksiyonunda `normalized_total` değerini bu ölçeğe yakın tutmalıdır.

## 8.3. Ortak Reward Bileşenleri

Genel reward şablonu:

```text
R_total = R_performance + R_constraints + R_reasoning
```

Bileşenlerin içerikleri environment'a özeldir.

### Heat Exchanger

```text
R_performance:
- heat duty hedefe yakın mı?
- outlet temperature hedefleri sağlanıyor mu?

R_constraints:
- pressure drop limitleri aşılıyor mu?
- alan/maliyet aşırı mı?
- geometri geçerli mi?

R_reasoning:
- modelin tasarım etkisi tahminleri doğru mu?
```

### UAV Wing

```text
R_performance:
- L/D oranı iyi mi?
- stall speed limiti sağlanıyor mu?
- payload taşıma yeterli mi?

R_constraints:
- span limiti aşılıyor mu?
- aspect ratio mantıklı mı?
- stress limiti sağlanıyor mu?

R_reasoning:
- span, aspect ratio, twist ve airfoil değişimlerinin etkisi doğru tahmin ediliyor mu?
```

### Truss

```text
R_performance:
- ağırlık düşük mü?

R_constraints:
- stress limiti sağlanıyor mu?
- displacement limiti sağlanıyor mu?
- yapı bağlı mı?
- buckling güvenliği var mı?

R_reasoning:
- eleman kesiti artınca displacement ve stress azalırken mass artar tahmini doğru mu?
```

## 8.4. Hard Constraint vs Soft Penalty

Agent şu ayrımı korumalıdır:

```text
DRC = fiziksel/geometrik geçerlilik
Reward = geçerli tasarımlar arasındaki kalite
```

DRC'de elenmesi gereken örnekler:

```text
tube_inner_diameter_mm >= tube_outer_diameter_mm
negative wing span
tip_chord <= 0
disconnected truss topology
negative battery porosity
pipe diameter <= 0
```

Reward içinde soft penalty olması gereken örnekler:

```text
pressure drop biraz yüksek
L/D biraz düşük
wing mass biraz fazla
heat transfer area fazla
stress limiti küçük miktarda aşılmış
energy consumption yüksek
```

## 8.5. Reward Config Dosyaları

Reward ağırlıkları koda gömülmemelidir. YAML config üzerinden okunmalıdır.

Örnek heat exchanger reward config:

```yaml
environment: heat_exchanger

reward_weights:
  heat_duty_score: 1.0
  outlet_temperature_score: 0.4
  pressure_drop_penalty: 0.6
  area_penalty: 0.2
  cost_penalty: 0.2
  reasoning_score: 0.1

normalization:
  min_reward: -1.0
  max_reward: 1.0

invalid_penalties:
  invalid_json: -1.0
  schema_failure: -1.0
  drc_failure: -0.8
  simulation_failure: -1.0
```

Örnek UAV reward config:

```yaml
environment: uav_wing

reward_weights:
  lift_to_drag_score: 1.0
  stall_margin_score: 0.5
  payload_score: 0.4
  wing_mass_penalty: 0.3
  span_penalty: 0.2
  stress_penalty: 0.5
  reasoning_score: 0.1

normalization:
  min_reward: -1.0
  max_reward: 1.0

invalid_penalties:
  invalid_json: -1.0
  schema_failure: -1.0
  drc_failure: -0.8
  simulation_failure: -1.0
```

---

# 9. Environment Fidelity Seviyeleri

Her environment mümkünse fidelity seviyesi desteklemelidir.

```python
env = HeatExchangerEnv(fidelity="low")
env = HeatExchangerEnv(fidelity="medium")
env = HeatExchangerEnv(fidelity="high")
```

Önerilen yapı:

```text
heat_exchanger:
  low     → simplified analytical model
  medium  → ht + fluids + CoolProp
  high    → TESPy veya daha detaylı thermal network

uav_wing:
  low     → analytical lift/drag estimates
  medium  → AeroSandbox + NeuralFoil
  high    → OpenAeroStruct / SU2

turbomachinery:
  low     → custom meanline model
  medium  → TurboDesign / TurboFlow
  high    → SU2 veya CFD validation
```

Başlangıçta sadece low/medium fidelity yeterlidir.

RL training düşük veya orta fidelity'de yapılabilir. Final evaluation daha yüksek fidelity'de yapılabilir.

---

# 10. Simülatör Kurulum ve Smoke Test Standardı

Her simülatör için aşağıdaki testler yazılmalıdır:

```text
1. Paket import ediliyor mu?
2. Basit valid input çalışıyor mu?
3. Output dict/JSON formatına çevriliyor mu?
4. Ana metrikler NaN veya inf değil mi?
5. Ana metrikler fiziksel olarak mantıklı mı?
6. Aynı input iki kez çalıştırıldığında aynı sonuç dönüyor mu?
7. Invalid input simülatörü çökertmeden kontrollü hata veriyor mu?
8. Runtime RL döngüsü için makul mü?
```

Örnek smoke test:

```python
def test_heat_exchanger_smoke():
    task = load_json("configs/tasks/heat_exchanger/task_001.json")
    design = load_json("examples/designs/heat_exchanger_valid_001.json")

    env = HeatExchangerEnv(fidelity="medium")
    result = env.evaluate(task, design)

    assert result.status == "success"
    assert result.simulation_result is not None
    assert result.simulation_result.simulation_success is True
    assert result.simulation_result.metrics["heat_duty_W"] > 0
    assert result.reward_result.normalized_total > -1.0
```

---

# 11. Heat Exchanger Environment Detayı

## 11.1. Task Formatı

```json
{
  "environment": "heat_exchanger",
  "task_type": "shell_and_tube_design",
  "requirements": {
    "target_heat_duty_W": 180000,
    "max_hot_side_pressure_drop_Pa": 25000,
    "max_cold_side_pressure_drop_Pa": 30000,
    "hot_fluid": "Water",
    "cold_fluid": "Water",
    "hot_inlet_temperature_C": 85,
    "cold_inlet_temperature_C": 25,
    "hot_mass_flow_kg_s": 2.1,
    "cold_mass_flow_kg_s": 2.7
  }
}
```

## 11.2. Design Formatı

```json
{
  "design_parameters": {
    "heat_exchanger_type": "shell_and_tube",
    "tube_outer_diameter_mm": 19.0,
    "tube_inner_diameter_mm": 16.0,
    "tube_length_m": 3.5,
    "number_of_tubes": 120,
    "tube_passes": 2,
    "shell_passes": 1,
    "shell_diameter_m": 0.45,
    "baffle_spacing_m": 0.18,
    "baffle_cut_percent": 25
  },
  "expected_effects": {
    "heat_duty": "increase",
    "pressure_drop": "moderate increase",
    "cost": "increase"
  },
  "design_rationale": "The design increases heat transfer area while keeping baffle spacing moderate."
}
```

## 11.3. DRC Kuralları

```text
tube_outer_diameter_mm > tube_inner_diameter_mm
tube_inner_diameter_mm > 0
tube_length_m > 0
number_of_tubes > 0
tube_passes in [1, 2, 4, 6, 8]
shell_passes >= 1
shell_diameter_m > tube_outer_diameter_m
baffle_spacing_m > 0
baffle_spacing_m < shell_diameter_m
0 < baffle_cut_percent < 50
hot_inlet_temperature_C > cold_inlet_temperature_C
mass_flow rates > 0
```

## 11.4. Metrics

```json
{
  "heat_duty_W": 0.0,
  "hot_outlet_temperature_C": 0.0,
  "cold_outlet_temperature_C": 0.0,
  "overall_U_W_m2K": 0.0,
  "heat_transfer_area_m2": 0.0,
  "hot_side_pressure_drop_Pa": 0.0,
  "cold_side_pressure_drop_Pa": 0.0,
  "estimated_cost_index": 0.0
}
```

---

# 12. UAV Wing Environment Detayı

## 12.1. Task Formatı

```json
{
  "environment": "uav_wing",
  "task_type": "uav_planform_design",
  "requirements": {
    "target_payload_kg": 3.0,
    "cruise_speed_m_s": 22.0,
    "max_stall_speed_m_s": 11.0,
    "air_density_kg_m3": 1.225,
    "max_wing_span_m": 4.0,
    "max_wing_mass_kg": 2.5,
    "min_lift_to_drag_ratio": 12.0
  }
}
```

## 12.2. Design Formatı

```json
{
  "design_parameters": {
    "span_m": 3.2,
    "root_chord_m": 0.42,
    "tip_chord_m": 0.19,
    "sweep_deg": 3.0,
    "dihedral_deg": 4.0,
    "twist_root_deg": 2.0,
    "twist_tip_deg": -2.0,
    "airfoil_root": "naca4412",
    "airfoil_tip": "naca2412"
  },
  "expected_effects": {
    "lift_to_drag_ratio": "increase",
    "stall_speed": "decrease",
    "bending_moment": "increase"
  },
  "design_rationale": "A high aspect ratio wing improves induced drag but increases bending load."
}
```

## 12.3. DRC Kuralları

```text
span_m > 0
span_m <= max_wing_span_m
root_chord_m > 0
tip_chord_m > 0
root_chord_m >= tip_chord_m
aspect_ratio within configured limits
sweep_deg within configured limits
dihedral_deg within configured limits
twist angles within configured limits
airfoil names supported by evaluator
wing_area_m2 > 0
```

## 12.4. Metrics

```json
{
  "wing_area_m2": 0.0,
  "aspect_ratio": 0.0,
  "lift_coefficient_cruise": 0.0,
  "drag_coefficient_cruise": 0.0,
  "lift_to_drag_ratio": 0.0,
  "estimated_stall_speed_m_s": 0.0,
  "estimated_wing_mass_kg": 0.0,
  "max_bending_stress_MPa": 0.0
}
```

---

# 13. Model Client Interface

Tüm modeller aynı interface'i kullanmalıdır.

```python
class BaseModelClient:
    model_name: str
    model_type: str

    def generate_design(
        self,
        task: dict,
        schema: dict,
        context: dict | None = None
    ) -> dict:
        raise NotImplementedError
```

Implementasyonlar:

```text
DummyRandomClient
HeuristicClient
LocalTransformersClient
LocalVLLMClient
LlamaCppClient
OpenAIClient
AnthropicClient
GeminiClient
```

Kural:

```text
ModelClient sadece design üretir.
ModelClient reward hesaplamaz.
ModelClient simülatörü çağırmaz.
ModelClient DRC yapmaz.
```

---

# 14. Prompt Standardı

Küçük LLM'ler için prompt kısa ve net olmalıdır.

Örnek:

```text
You are an engineering design model.

Return only valid JSON.
Do not include markdown.
Do not include explanations outside JSON.

Task:
{task_json}

Allowed design schema:
{schema_json}

Your output must contain:
- design_parameters
- expected_effects
- design_rationale
```

Ticari LLM benchmarkında da mümkün olduğunca aynı prompt kullanılmalıdır. Ticari LLM'lere özel gereğinden fazla bilgi verilirse karşılaştırma adil olmaz.

---

# 15. Deney Modları

## 15.1. Zero-Shot Evaluation

```text
LLM task alır ve tek seferde design üretir.
Simülasyon sonucu LLM'e geri verilmez.
```

## 15.2. Few-Shot Evaluation

```text
LLM'e birkaç başarılı/başarısız örnek verilir.
Sonra yeni task için design üretmesi istenir.
```

## 15.3. Iterative Design Without Training

```text
LLM'e önceki simülasyon sonucu verilir.
Yeni tasarım üretmesi istenir.
Bu eğitim değildir, inference-time iterative design'dır.
```

## 15.4. SFT

```text
Başarılı tasarımlardan instruction dataset oluşturulur.
Küçük LLM'e valid JSON ve makul tasarım aralıkları öğretilir.
```

## 15.5. RL / GRPO

```text
Model bir task için N candidate design üretir.
Her design simüle edilir.
Reward hesaplanır.
Model reward sinyali ile güncellenir.
```

## 15.6. Commercial Benchmark

```text
Ticari LLM'ler aynı task setinde değerlendirilir.
Eğitim yapılmaz.
```

---

# 16. Logging Standardı

Her tasarım denemesi aşağıdaki formatta loglanmalıdır.

```json
{
  "run_id": "uuid",
  "timestamp": "iso_datetime",
  "phase": "phase_1",
  "experiment_mode": "zero_shot | few_shot | iterative | sft | rl | commercial_benchmark | baseline",
  "environment": "heat_exchanger",
  "model": {
    "model_name": "string",
    "model_type": "local | commercial | random | heuristic"
  },
  "task": {},
  "raw_model_output": "string",
  "parsed_design": {},
  "schema_validation": {
    "passed": true,
    "errors": []
  },
  "drc_result": {
    "passed": true,
    "violations": []
  },
  "simulation_result": {},
  "reward": {
    "total": 0.0,
    "normalized_total": 0.0,
    "breakdown": {}
  },
  "runtime": {
    "model_seconds": 0.0,
    "simulation_seconds": 0.0,
    "total_seconds": 0.0
  }
}
```

---

# 17. Caching Standardı

Aynı task/design/simulator kombinasyonu tekrar simüle edilmemelidir.

Hash:

```text
hash = sha256(task_json + design_json + simulator_name + simulator_version + fidelity)
```

Cache path:

```text
logs/simulations/cache/{hash}.json
```

Caching özellikle şu durumlarda zorunludur:

```text
- RL training sırasında tekrar eden tasarımlar
- Ticari LLM benchmark maliyet kontrolü
- Debugging
- Reproducibility
```

---

# 18. Evaluation Metrics

Tüm modeller için aşağıdaki metrikler hesaplanmalıdır:

```text
JSON valid rate
Schema valid rate
DRC pass rate
Simulation success rate
Constraint satisfaction rate
Mean normalized reward
Median normalized reward
Best normalized reward
Design diversity
Reasoning direction accuracy
Runtime per valid design
Cost per valid design
```

Raporlar environment bazında ve genel ortalama olarak ayrılmalıdır.

---

# 19. Başlangıçta Kullanılacak Simülatörler

## Seviye 1 — İlk Kurulacaklar

```text
Heat exchanger:
  ht
  fluids
  CoolProp

UAV wing:
  AeroSandbox
  NeuralFoil

Truss:
  Başlangıçta custom numpy/scipy solver
  Sonra OpenSeesPy veya scikit-fem
```

## Seviye 2 — İkinci Aşama

```text
Battery:
  PyBaMM

Water network:
  WNTR

Vehicle powertrain:
  FASTSim veya benzeri açık araçlar
```

## Seviye 3 — Orta-Uzun Vade

```text
Turbomachinery:
  NASA turbo-design
  NASA pyturbo-aero
  TurboDesigner
  TurboFlow
  TURBIGEN
  SU2

Building/HVAC:
  EnergyPlus
  BOPTEST
  OpenModelica/OMPython

Wind farm:
  FLORIS
  WISDEM
  OpenFAST
```

---

# 20. Agent İçin Yapılmaması Gerekenler

```text
- İlk committe LLM API entegrasyonu yapma.
- Simülatör smoke testleri geçmeden training scripti yazma.
- Reward hesaplarını environment içine dağınık şekilde gömme.
- Her environment için farklı result formatı üretme.
- Ticari LLM'ler için ayrı evaluator yazma.
- Geçersiz tasarımları simülatöre doğrudan gönderme.
- NaN/inf metrikleri reward'a sokma.
- Hard constraint'leri soft penalty olarak bırakma.
- Reward scale normalizasyonunu unutma.
- TurboDesign ile başlama.
```

---

# 21. Nihai Hedef Mimari

Projenin çekirdeği şu tek satır etrafında çalışmalıdır:

```python
result = env.evaluate(task, design)
reward = result.reward_result.normalized_total
```

Bu satır çalıştığında şu kaynaklardan gelen tüm tasarımlar aynı pipeline'dan geçebilmelidir:

```text
- Random sampler
- Heuristic sampler
- Bayesian optimizer
- Ticari LLM
- Yerel base LLM
- Yerel SFT LLM
- Yerel RL-trained LLM
```

Bu mimari sağlanırsa, heat exchanger'dan UAV wing'e, oradan truss veya TurboDesign'a geçmek için eğitim/evaluation kodunu yeniden yazmak gerekmez.

---

# 22. Kısa Sonuç

Bu proje, önce sağlam bir **simülatör ve environment altyapısı** kurmalı, sonra LLM entegrasyonuna geçmelidir.

Öncelik sırası:

```text
1. BaseEnvironment / BaseSimulator / BaseRewardFunction
2. Heat exchanger MVP
3. LLM'siz baseline ve dataset
4. Küçük LLM SFT
5. RL / GRPO
6. Ticari LLM benchmark
7. UAV wing demo
8. Multi-environment benchmark
9. TurboDesign / turbomachinery ileri validasyon
```

Agent bu dokümanı bir proje yürütme planı olarak kullanmalı ve her faz sonunda test edilebilir, loglanabilir, çalışır çıktılar üretmelidir.