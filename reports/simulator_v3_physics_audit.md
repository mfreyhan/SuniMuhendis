# Simülatör V3 — Fiziksel Doğruluk ve Görev Kalibrasyonu Denetimi

**Tarih:** 2026-09-18
**Kapsam:** `simulator.py` V3, `drc.py`, `score.py` (V3), `results/zero_shot/heat_exchanger_hard_v2/task.json`
**Yöntem:** Analitik türetme + ~410.000 tasarımın toplu simülasyonu (rastgele ve yönlendirilmiş örnekleme)
**Sonuç:** Fizik motorunda katastrofik hata **yok**. Katastrofik sorun **görev kalibrasyonunda**: `hard_v2`'nin parametre seçimi, hiçbir tasarımın kaçamayacağı sabit bir ceza ve aşılamaz bir duty tavanı yaratıyor.

---

## 1. Doğrulanan Bulgular (fizik motoru sağlam)

| Kontrol | Yöntem | Sonuç |
|---|---|---|
| Enerji dengesi | ε-NTU'dan çıkan Q ile U·A·F·LMTD karşılaştırması | Sapma **%0.00** |
| 2. yasa | 4.000 rastgele tasarımda ε ve Q/Q_max | İhlal **yok**; ε hiç konfigürasyon limitini aşmadı |
| ε-NTU ↔ LMTD-F tutarlılığı | İki bağımsız hesap yolu | Birbirini doğruluyor |
| `ht` kütüphane çağrısı | `effectiveness_from_NTU(subtype="S&T", n_shell_tube=1)` | Çalışıyor; sessiz fallback'e **düşmüyor** |
| Duvar iletimi | `ln(do/di) / (2πkLN)` | Silindirik iletim doğru |
| Kütüphane sınırı | `ht`/`fluids` yalnızca boru içi akışta, kabuk tarafı elle Kern | Doğru ayrım |

Bu nedenle aşağıdaki bulguların hiçbiri "denklem yanlış" değildir; hepsi **kalibrasyon ve tasarım uzayı** sorunudur.

---

## 2. KATASTROFİK — `hard_v2` ulaşılamaz bir noktada kalibre edilmiş

### 2.1. Duty hedefi, konfigürasyonun termodinamik tavanının %95'inde

Şema `tube_passes` alanını dışarı açmıyor; varsayılan `DEFAULT_TUBE_PASSES = 2`. Dolayısıyla her tasarım zorunlu olarak **1 kabuk – 2 boru geçişli** TEMA E. Debiler eşit olduğu için `Cr = 0.99809` ve bu konfigürasyonun asimptotik tavanı sabittir:

```
ε_max = 2 / (1 + Cr + sqrt(1 + Cr²)) = 0.586346          (NTU → ∞)
Q_max,konfig = ε_max · C_min · ΔT = 367.815 W
```

Görev hedefi **350.000 W** — yani mutlak tavanın **%95.2**'si.

| NTU | ε | Q (W) |
|---:|---:|---:|
| 1.0 | 0.4629 | 290.402 |
| 2.0 | 0.5573 | 349.571 |
| 2.5 | 0.5721 | 358.860 |
| 3.0 | 0.5793 | 363.408 |
| 5.0 | 0.5859 | 367.554 |
| ∞ | 0.5863 | 367.815 |

Hedef, NTU 2 ile 3 arasında geçiliyor; **NTU 3'ün ötesinde eklenen hiçbir alan duty'yi artırmıyor.** Karşılaştırma: saf karşıt akışta NTU=5 için ε=0.834 olurdu. Yani ısı transferi hedefi optimize edilebilir bir amaç değil; bir eşik ve hemen ardından bir duvar.

### 2.2. İki uyarı matematiksel olarak kaçınılmaz — her feasible tasarım sabit ×0.8 yiyor

**(a) `F < 0.75` uyarısı.** Debiler ve giriş sıcaklıkları sabit olduğundan çıkış sıcaklıkları — dolayısıyla LMTD düzeltme faktörü F — **yalnızca Q'nun fonksiyonudur**. Hiçbir geometrik serbestlik F'yi etkileyemez:

```
F = 0.75  <=>  Q = 328.436 W
görev hedefi 350.000 W  =>  F <= 0.625, daima
```

Duty gereksinimini karşılamak bu uyarıyı **garanti eder**.

**(b) `Tube velocity < 0.5 m/s` uyarısı.** Nozzle çapı `D_nozzle_hot = 0.05 m` varsayılanında sabit ve şemada yok. Tek başına nozzle kaybı **1.668 Pa**, yani 2.500 Pa bütçesinin **%66.7'si**. Geriye 832 Pa kalır. Boru tarafı header kaybı tek başına `4·N_pass·ρv²/2 = 3.887·v²`:

```
sürtünme SIFIR olsa dahi   v_tube < 0.4626 m/s
MIN_TUBE_VELOCITY = 0.50 m/s
```

Yani `ΔP <= 2500 Pa` kısıtı ile `v >= 0.5 m/s` **birbirini dışlar**.

**Ampirik doğrulama.** Üç bağımsız tarama — 60.000 rastgele, 200.000 yönlendirilmiş (boru hızı 0.4–3.2 m/s aralığına zorlanarak), 150.000 `concentric_tube` — üç gereksinimi de sağlayan tasarımlarda uyarı sayısı **her zaman tam olarak 2**; hiçbir örnekte 0 veya 1 görülmedi. Yönlendirilmiş taramada boru hızı sağlıklı aralığa zorlandığında **190.809 geçerli simülasyonun hiçbiri** üç gereksinimi sağlayamadı.

Sonuç:

```
penalty_factor = 0.8  (her feasible tasarım için sabit)
skor tavanı    = 0.9786 × 0.8 = 0.7829
```

Bu, gözlenen değerlerle birebir örtüşüyor:

| Kaynak | En iyi skor |
|---|---:|
| 3.000 tasarımlık kalibrasyon taraması | 0.7834 |
| `gpt-oss-120b__reasoning-low` (n=20) | 0.7829 |
| `nex-n2.5-pro__reasoning-none` (n=20) | 0.7834 |

### 2.3. Beyan edilen kısıt ile gerçek kısıt uyuşmuyor

Prompt "ΔP <= 2.500 Pa" diyor. Modelin fiilen karşılaması gereken şey **geometrik ΔP <= 832 Pa (boru) / 876 Pa (kabuk)** — kalanı modelin ne gördüğü ne de değiştirebildiği sabit bir nozzle kaybı. Görev bu haliyle hem çözülemez hem de öğrenilemez.

---

## 3. ×0.8 çarpanı evrensel mi? — Hayır, `hard_v1`/`hard_v2`'ye özgü ve bıçak sırtı

Her iki tetikleyici de task parametrelerinin fonksiyonudur ve `hard_v2` her ikisinin de yanlış tarafında, üstelik **kıl payı**:

| Task | Hedef duty | ΔP limiti | Zorunlu uyarı | penalty tavanı |
|---|---:|---:|---|---:|
| `hard_v1`, `hard_v2` | 350.000 W | 2.500 Pa | `F<0.75`, `v_tube<0.5` | **0.80** |
| `v1`, `v3` | 150.000 W | 50.000 Pa | — | **1.00** |

**Uçurumun kenarı — ΔP limiti (hedef 350 kW sabit):**

| ΔP limiti | Nozzle payı | Ulaşılabilir v_tube | Durum |
|---:|---:|---:|---|
| 2.500 Pa | %66.7 | 0.463 m/s | **zorunlu uyarı** |
| 3.000 Pa | %55.6 | 0.585 m/s | serbest |
| 5.000 Pa | %33.4 | 0.926 m/s | serbest |
| 10.000 Pa | %16.7 | 1.464 m/s | serbest |

**Uçurumun kenarı — hedef duty (F=0.75 eşiği 328.436 W):**

| Hedef duty | Durum |
|---:|---|
| 320.000 W | serbest |
| 328.436 W | eşik |
| 340.000 W | **zorunlu F uyarısı** |
| 350.000 W | **zorunlu F uyarısı** |

ΔP limitini 2.500 → 3.000 Pa yapmak veya hedefi 350 → 325 kW'a çekmek, her iki zorunlu cezayı da tek başına kaldırır. Yani sorun yapısal değil, **parametre seçimi**.

---

## 4. Model ayrıştırma gücü — mevcut skor neyi ölçüyor?

`hard_v2` üzerindeki tüm koşular (n >= 20):

| Model | n | Geçerli | Ort. (tüm) | Ort. (geçerli) | Max | sd (geçerli) |
|---|---:|---:|---:|---:|---:|---:|
| gpt-oss-120b (low) | 20 | %85 | 0.637 | 0.750 | 0.783 | 0.082 |
| qwen3.8-27b (none) | 20 | %90 | 0.443 | 0.492 | 0.720 | 0.152 |
| deepseek-v4-flash (none) | 20 | %100 | 0.409 | 0.409 | 0.724 | 0.189 |
| nex-n2.5-pro (none) | 20 | %75 | 0.252 | 0.336 | 0.783 | 0.190 |
| gpt-oss-20b (low) | 20 | %45 | 0.205 | 0.455 | 0.625 | 0.181 |
| llama-3.3-70b | 20 | %10 | 0.040 | 0.403 | 0.492 | 0.090 |

Manşet metrik (ortalama toplam ödül) iki ayrı yeteneği tek sayıya karıştırıyor:

- **Uyum:** geçerli, DRC'den geçen bir JSON üretebiliyor mu? (aralık: %10 – %100)
- **Mühendislik:** ürettiği tasarım ne kadar iyi? (aralık: 0.336 – 0.750)

Korelasyonlar: `corr(geçerlilik, manşet) = 0.83`, `corr(tasarım kalitesi, manşet) = 0.76`. Yani manşet kabaca ikisinin ortalaması ve bir model yalnızca **güvenilir olarak** üst sıraya çıkabiliyor (bkz. deepseek-v4-flash: %100 geçerli, ama en düşük tasarım kalitelerinden biri).

**Ödül bütçesinin dağılımı — asıl adalet sorunu.** 80.000 tasarımlık taramada:

```
geçersiz cevap (0.0)  ->  en kötü feasible tasarım :  +0.439 puan
en kötü feasible      ->  teorik optimum           :  +0.256 puan
```

Feasible tasarımların skor dağılımı: p5 = 0.528, medyan = 0.616, p95 = 0.746, tavan = 0.783 (sd = 0.068).

**Skor, mühendislik yapmayı değil, ortaya çıkmayı ödüllendiriyor.** Bu doğrudan araştırma sorusunu bloke eder: geri bildirimli iterasyon yalnızca ikinci (0.256'lık) aralığı iyileştirebilir ve bu aralık birincisinden dardır. `zero-shot < feedback-driven < eğitilmiş model` merdiveni bu görevde ölçülemez.

---

## 5. İkincil bulgular (katastrofik değil, ancak v3 tasarımını etkiler)

| # | Bulgu | Etki |
|---|---|---|
| 5.1 | Kern Nu korelasyonu geçerlilik aralığının altında kullanılıyor (gerçekçi tasarımlarda `Re_shell ≈ 1.000`, Kern >= 2.000 için geçerli); `Re < 10`'da `abs(Re)` ile ekstrapole ediliyor | `h_o` iyimser |
| 5.2 | `P_design` varsayılanı 101.325 Pa (atmosferik) → **her iki ASME et kalınlığı kontrolü de ölü kod**. 22.457 tasarımda bir kez bile tetiklenmedi. Aynı şekilde nozzle hızı, pitch ratio ve min approach kontrolleri de hiç tetiklenmiyor | Tasarım kontrollerinin yarısı işlevsiz |
| 5.3 | İşletme maliyeti, yıllıklaştırılmış maliyetin **%0.32**'si (toplam pompa gücü 13.6 W) → maliyet fiilen çelik kütlesi | "Kompaktlık için pompalama gücü öde" ödünleşimi hiç yok |
| 5.4 | Sıcak akışkan özellikleri 80 °C suyunda donmuş; `T_hot_in` değiştirilse bile güncellenmiyor | Nominal dışı sıcaklıklarda hatalı (mevcut tasklar varsayılanı kullandığı için şu an etkisiz) |
| 5.5 | `drc.py`, `tube_passes=2` / `pitch_ratio=1.25` / `pitch_type=square` değerlerini **sabit kodluyor** ve tasarımın kendi değerlerini yok sayıyor; simülatör gerçek değerleri kullanıyor | `tube_passes=4` içeren tasarım DRC'yi geçip simülatörde `simulation_error` veriyor. **v3'te şema genişletilirse bu hemen ısırır.** |
| 5.6 | Kabuk tarafı `A_cross`, `N_tubes`'a hiç bağlı değil (klasik Kern varsayımı) | Geniş kabukte seyrek demet → `h_o` aşırı tahmin |
| 5.7 | `schema.py` `extra="forbid"` kullanıyor → simülatörün `dict.get(...)` ile okuduğu ~20 opsiyonel parametre (`tube_passes`, `pitch_ratio`, `baffle_cut`, `D_nozzle_hot`, `m_dot_hot`, ...) **hiçbir LLM tasarımından erişilebilir değil**; şema aşamasında reddediliyorlar | Tasarım uzayı gerçekten yalnızca 7 alan; bu parametreler benchmark açısından ölü. *(Not: `CLAUDE.md`'deki "extra fields beyond the schema are preserved and used downstream" ifadesi bu nedenle hatalı — düzeltilmeli.)* |
| 5.8 | `concentric_tube` karşıt akış olduğu için ε tavanını kırıyor (538 kW'a ulaşıyor), ancak en iyi skoru 0.761 ve 80 m'lik boru (`L/D = 421`) gerektiriyor | Gerçek bir kaçış yolu değil; 0.783 tavanını değiştirmiyor |

---

## 6. `hard_v3` için çıkarımlar

Denetimin operasyonel sonucu: **v3'te ilk iş zorluk eklemek değil, başlığı açmaktır.** Öncelik sırasıyla:

1. **Nozzle boyutunu ya şemaya aç ya da ΔP skorundan çıkar.** ΔP kısıtının %66'sının modelin dokunamadığı bir sabit olması hem görevi çözülemez kılıyor hem de ölçümü anlamsızlaştırıyor.
2. **`tube_passes`'i şemaya aç** (veya debileri dengesizleştirerek `Cr`'yi 1'den uzaklaştır). İkisi de ε tavanını kaldırır ve duty'yi tekrar optimize edilebilir bir amaç yapar. Şemayı genişletmeden önce **madde 5.5 düzeltilmelidir**, aksi halde DRC ile simülatör çelişir.
3. **Hedef duty ile uyarı eşiklerini tutarlı hale getir.** Bir gereksinimi karşılamak bir uyarıyı zorunlu kılmamalı; uyarılar kazanılabilir olmalı, sabit vergi olmamalı.
4. **Ödül bütçesini yeniden dağıt.** "Geçerli tasarım üretme" ile "iyi tasarım üretme" arasındaki oran şu an 0.44 / 0.26. Bunun tersine dönmesi gerekir ki iterasyon ve eğitim ölçülebilir kazanç üretebilsin.
5. **Raporlamada iki ekseni ayır.** Geçerlilik oranı ve geçerli-tasarım kalitesi ayrı raporlanmalı; tek bir manşet ortalama modelleri adil ayrıştırmıyor.

---

## 7. Denetim sonrası yapılan düzeltmeler (Simülatör V4, paket 0.3.0)

Bu denetimin bulguları üzerine aşağıdakiler düzeltildi. **Simülatör sürümü `v3` → `v4`'e yükseltildi:
çıktılar değişti, V3 ve V4 sonuçları asla birlikte havuzlanmamalı.**

### Düzeltilenler

| Bulgu | Yapılan | Etki |
|---|---|---|
| 5.5 — DRC `tube_passes`/`pitch_ratio`/`pitch_type`'ı sabit kodluyordu | `drc.py` artık bu değerleri tasarımın kendisinden okuyor; geçiş sayısının çift olması, boru sayısını bölmesi ve TEMA asgari hatve oranı DRC'de doğrulanıyor | Davranış değişmedi (şema ek alan kabul etmiyor), ancak **v3'te şema genişletilmeden önce zorunluydu** |
| Sabit `MAX_UNSUPPORTED_SPAN = 1.5 m` | TEMA RCB-4.52 tablosu, boru dış çapına göre (`max_unsupported_span()`); tablo arası çaplar daha küçük girdinin limitini alır | **Tasarımların %15.5'inde uyarı sayısı değişti**, skor sapması −0.098…+0.096, ortalama ≈ 0 |
| ASME et kalınlığı formülü işaret hatası | UG-27(c)(1) formuna geçildi: `t = P·R/(S·E − 0.6·P)`; kaynak verimi `E` parametresi eklendi (varsayılan 1.0) | Varsayılan atmosferik basınçta uyarı değişmiyor; yüksek basınçta artık emniyetsiz değil |
| 5.1 — Kern korelasyonu geçerlilik aralığı dışında | `shell_correlation_in_range` metriği + `raw_data["fidelity_notes"]` | Skoru **etkilemiyor** (bkz. aşağıdaki not) |
| 5.6 — Kern `A_cross` demet doluluğunu görmüyor | `bundle_fill_fraction` metriği + doluluk %70'in altındaysa not | Skoru **etkilemiyor** |

**Neden güvenilirlik notları `warnings`'e girmiyor:** skor her uyarı için %10 kesiyor. Korelasyonumuzun
geçerlilik aralığı dışına çıkması tasarımın kusuru değil, *bizim* modelimizin sınırı. Bunu uyarı sayarsak
hakemin cehaletini tasarıma fatura etmiş oluruz. Bu yüzden ayrı bir kanaldan raporlanıyorlar.

### Bilinçli olarak düzeltilmeyenler

| Bulgu | Neden |
|---|---|
| 5.4 — Akışkan özellikleri 80 °C'de sabit | Özellikleri ortalama yığın sıcaklığında hesaplamak tüm termal sonuçları yeniden yazar. Kazanç marjinal, risk yüksek; ayrıca şema sıcaklık girdisine izin vermediği için benchmark yolunda hiçbir etkisi yok. Bilinen sınırlama olarak kayıt altında. |
| 5.2 — ASME kontrolleri ölü | Formül düzeltildi ama kontroller yine tetiklenmiyor: **et kalınlığı tasarlanmıyor, türetiliyor** (`max(6 mm, D/200)`). Canlandırmanın tek yolu kalınlığı şemaya bir tasarım değişkeni olarak eklemek — bu bir v3 görev kararı. |
| 5.3 — İşletme maliyeti ihmal edilebilir | Bu bir fizik hatası değil, ağırlık/görev tasarımı sorunu. ΔP–maliyet ödünleşimini anlamlı kılmak v3'ün ödül bütçesi kararına ait. |

### Denetim aracı

Bulguların tekrarlanabilir olması için `BaseEnvironment.audit_task()` eklendi — ortamdan bağımsız bir
şablon metot, her ortam kendi fiziğini `analyse_physics()` ile dolduruyor. Bu raporun 2., 3. ve 4.
bölümlerindeki tüm sayılar tek çağrıyla yeniden üretilebilir:

```python
from sunimuhendis import make_env
env = make_env("heat_exchanger", score_version="heat_exchanger_score_v3")
print(env.audit_task(task_params).summary())
```

`tests/test_task_audit.py` hem duvara dayalı görevin işaretlendiğini hem de gerçekten boşluğu olan bir
görevin **işaretlenmediğini** sabitliyor. `tests/test_simulator_v4_fixes.py` yukarıdaki her düzeltmeyi
ayrı ayrı sabitliyor.
