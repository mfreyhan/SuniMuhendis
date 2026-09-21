# Turbomachinery Throughflow Ortamı — Fazlı Uygulama Planı

Tarih: 20 Eylül 2026  
Durum: Faz 0 tamamlandı; Faz 1–2 araştırması yapıldı, kabul engelleri açık. Sonraki API ve komutlar hedef tasarımdır.  
Hedef ortam adı: `turbomachinery_throughflow`  
Hedef kurulum extra'sı: `throughflow`

İlk plan 20 Eylül 2026 kaynak incelemesine dayanıyordu. 21 Eylül güncellemesi: NASA sabit SHA ile kuruldu; 65 senaryo ve 7 dependency uyumsuzluğu deneyi çalıştırıldı. [Faz 0–2 raporu](throughflow_phase_0_2/README.md), [kanıt matrisi](throughflow_phase_0_2/capability_matrix.md) ve [gereksinim eşlemesi](throughflow_phase_0_2/requirements_traceability.md) tamamlanan işleri ve engelleri kaydeder. Faz 2.5'te public runtime Python 3.12'ye geçirildi; yerel Windows ile uzak Windows/Ubuntu CI kabulü tamamlandı, özel eğitim reposu geçişi açık kaldı. Basit/çok kademeli sonuç dönüşleri fiziksel doğruluk sertifikası değildir. Çalışma PR #2 ile `main` dalına birleştirildi; ana repodaki bağımsız HE v5 değişiklikleri çalışma dalına alınmadı.

## 1. Nihai hedef ve tamamlanma tanımı

SuniMuhendis içinde geliştirilen ve aynı dağıtılabilir Python paketi üzerinden dış eğitim repolarından çağrılabilen, NASA turbo-design destekli bir throughflow ortamı oluşturulacak. Kullanıcı doğrudan NASA sınıfları kurmak, bu reponun çalışma dizininde bulunmak veya benchmark scriptlerini import etmek zorunda kalmayacak.

Ortamın iki ana işi olacak:

1. Tasarımı doğrulayıp fiziksel performansı çözmek: `env.simulate(...)`.
2. Aynı doğrulama ve fizik yolunun üzerine görev gereksinimlerini ve ödülü eklemek: mevcut biçimini koruyan `env.evaluate(...)`.

Başarılı nihai teslim aşağıdaki koşulların birlikte sağlanmasıdır:

- [ ] Mevcut heat exchanger kurulumu, API'si ve tarihsel fizik/skor davranışı korunur.
- [ ] Tek ve çok kademeli tasarımlar aynı tasarım sözleşmesiyle ifade edilir.
- [ ] Sayısal streamline çözünürlüğü, tasarımın radyal kontrol noktalarından bağımsız değiştirilebilir.
- [ ] Sabit kayıpla örnek çalıştırmanın yanında gerçek akış/geometri bağımlı kayıp modelleri doğrulanır.
- [ ] Türbin ve kompresörün desteklenen temel yolları ayrı referanslarla çalışır; birinin başarısı diğerinin doğrulandığı anlamına gelmez.
- [ ] İleri özelliklerin her biri için test edilmiş destek kapsamı, sınırlamalar ve örnek bulunur.
- [ ] Yakınsamayan, geçerliliği bilinmeyen veya altyapı hatası yaşayan çözüm güvenilir eğitim ödülü olarak sunulmaz.
- [ ] Dış repoyu temsil eden temiz bir ortam, üretilen wheel'i kurarak simülasyon ve değerlendirme yapar.
- [ ] Eğitim sırasında ağdan kod/veri indirme, GUI açma veya çalışma dizinine zorunlu dosya yazma yoktur.
- [ ] Aynı tasarımın sonucunu belirleyen kod, fizik verisi, görev ve çözüm ayarları kaydedilir.
- [ ] NASA güncellemesi mevcut deneylerin fiziğini kendiliğinden değiştirmez.
- [ ] Lisans sınırları ve dağıtılan her üçüncü taraf varlığın kaynağı belgelenir.

İlk çalışan demo bir ara kilometre taşıdır. Çok kademeli çözüm, ampirik kayıp ve dış tüketici kurulumu tamamlanmadan kullanıcının temel isteği tamamlandı sayılmaz.

## 2. Kapsam ve mimari kararlar

### 2.1 Tek paket, ayrı çözücü bağımlılığı

SuniMuhendis'in şema, DRC, skor, kullanıcı API'si ve özgün adaptör kodu bu repoda geliştirilir. NASA çözücüsü ayrı kurulan ve sürümü sabitlenen bağımlılık olur. NASA kaynağı uygulama kolaylığı için bu paketin içine kopyalanmaz. Gerekli çözücü düzeltmeleri ayrı bir fork'ta izlenir; upstream'e aktarım ayrı bir yayın işlemi olur.

Lisans yaklaşımının dayanağı, NOSA'nın ayrı yazılımlarla daha büyük bir ürün oluşturulmasına ilişkin 1.F ve 3.I maddeleridir. Bu teknik plan hukuki kesinlik iddiası taşımaz. NASA'dan türetilmeyen kendi kodumuz Apache-2.0 altında kalacak şekilde tasarlanır; NASA bileşeni ve ona yapılan değişikliklerin lisansı ayrı korunur. [NOSA 1.3](https://opensource.org/license/NASA-1.3)

### 2.2 Üç bağımsız karmaşıklık ekseni

| Eksen | Örnek değişkenler | Kimin kontrolünde? |
|---|---|---|
| Tasarım uzayı | Kademe/sıra sayısı, geometri, kanat sayısı, radyal açı dağılımları | Görevin izin verdiği sınırlar içinde tasarımcı |
| Fizik varsayımları | Kayıp ve sapma modelleri, akışkan, soğutma modeli | Görev/deney sahibi |
| Sayısal çözüm | Streamline sayısı, toleranslar, çözüm modu, hesap bütçesi | Görev/deney sahibi |

Basit ve ileri hazır ayarlar aynı sözleşmenin farklı konfigürasyonlarıdır. Bir hazır ayarın adı tek başına deney kimliği değildir; bütün varsayılanların açıldığı etkin konfigürasyon kaydedilir.

### 2.3 Sorumluluk sınırları

| Katman | Sorumluluk | Dışarı sızdırılmayacak ayrıntı |
|---|---|---|
| Tasarım/görev şeması | Birimler, izinli alanlar, bağlamsal sınırlar | NASA enum ve sınıf isimleri |
| DRC | Geometrik ve topolojik tutarlılık | Çözücünün tesadüfi varsayılanları |
| Adaptör | NASA nesnelerini oluşturma ve çözüm çağrısı | Mutasyona uğrayan canlı NASA nesneleri |
| Sonuç normalleştirme | Birimli metrikler, dağılımlar, tanılar | NumPy/Cantera nesneleri |
| Fiziksel kabul | Yakınsama, dengeler, geçerlilik | Sadece exception oluşmadığı için başarı |
| Skor | Gereksinimler ve optimizasyon ödülü | Görev dışında seçilmiş hedefler |
| Çalıştırma katmanı | İşçi süreçleri, timeout, cache, log | Skora karışan makine yükü veya süre |

NASA projesi streamline/radial-equilibrium yaklaşımını kullanır. Bu ortam 3B CFD, kanat yapısal analizi veya doğrulanmış tam motor çevrimi olarak sunulmayacak. Desteklenmeyen stall/surge öngörüsü gibi çıktılar türetilmeyecek. [NASA proje açıklaması](https://github.com/nasa/turbo-design)

### 2.4 Geriye uyumluluk ilkeleri

- `make_env("heat_exchanger")` ve mevcut `evaluate(task_id, task_params, design_id, design_params)` çağrısı korunur.
- Yeni çekirdek hook'ları varsayılan olarak eski davranışı üretir; mevcut dummy ortamların yeni abstract metot uygulaması gerekmez.
- Heat exchanger sonuçlarına yeni boş/default alanlar eklenmesi bile serileştirme karşılaştırmalarında kontrol edilir; gerekiyorsa yeni alanlar yalnızca throughflow sonuçlarında doldurulur.
- Runtime hedefi kullanıcı kararıyla Python 3.12'ye yükseltildi ve Faz 2.5'te paket metadata'sı, constraint, CI ve temiz-wheel kontrolüyle kaydedildi. Yeni minor sürüm aralığı test olmadan genişletilmez.
- Tarihsel sonuç dosyaları topluca yeniden yazılmaz; eski ve yeni sürüm kayıtları birlikte okunabilir kalır.

## 3. Mevcut repoda değişiklik gerektiren somut noktalar

| Mevcut dosya | İncelemede görülen durum | Planlanan çalışma |
|---|---|---|
| [registry.py](../src/sunimuhendis/environments/registry.py) | Yalnız heat exchanger kayıtlı | Lazy throughflow factory ve ortam metadata'sı |
| [base_environment.py](../src/sunimuhendis/core/base_environment.py) | Skorlu değerlendirme var; başarısız simülasyon tanıları sonuçta korunmuyor; secondary noktalar ağırlıkla uyarı olarak birleşiyor | Ortak doğrulanmış simülasyon yolu, hata ayrımı, nokta sonuçları ve skor girdisi hook'u |
| [base_simulator.py](../src/sunimuhendis/core/base_simulator.py) | Dört elemanlı tuple sözleşmesi | Mevcut sözleşmeyi koruyan typed public sonuç dönüşümü |
| [types.py](../src/sunimuhendis/core/types.py) | EvaluationResult/ScoreResult/Requirement mevcut | SimulationResult ve tipli tanı sözleşmesi; uyumluluk kontrollü |
| [cache.py](../src/sunimuhendis/core/cache.py) | Cache evaluate'a bağlı değil; anahtar yalnız görev/tasarım içeriyor | Fizik fingerprint'i içeren throughflow cache yolu |
| [run_api_benchmark.py](../scripts/run_api_benchmark.py) | Ortam ve simulator_version heat exchanger'a bağlı | Ortamı görevden seçme, sürümü ortamdan alma |
| [run_llm_eval.py](../scripts/run_llm_eval.py) | Heat exchanger import/kurulumu | Aynı ortam seçme yoluna geçiş |
| [rescore_benchmark_results.py](../scripts/rescore_benchmark_results.py) | Heat exchanger skoruna bağlı | Ortam/score registry; yeniden puanlama ve yeniden simülasyonu ayırma |
| [dashboard.py](../scripts/dashboard.py) | Heat exchanger metrik ve metin varsayımları | Ortam bazlı gereksinim, metrik ve sürüm ayrımı |
| [pyproject.toml](../pyproject.toml) | Optional environment extras ve src-layout var | throughflow extra, paket verisi, temiz wheel kurulumu |
| [NOTICE](../NOTICE) | Mevcut üçüncü taraf bağımlılıklar listelenmiş | NASA ve dağıtılan varlıklar için doğrulanmış bildirimler |

## 4. Faz haritası ve kilometre taşları

| Faz | Amaç | Bağımlılık | Somut çıkış |
|---|---|---|---|
| 0 | Mevcut davranışın ve kapsamın kaydı | Yok | Başlangıç raporu ve kabul matrisi |
| 1 | Lisans, kaynak ve çalıştırma ortamı | 0 | Dağıtım kararı, sabitlenmiş bağımlılık adayı |
| 2 | NASA yeteneklerinin deneysel doğrulanması | 1 | Çalışan referanslar ve destek matrisi |
| 2.5 | Python 3.12 runtime ve tüketici sözleşmesi | 2 | Metadata, constraint, CI ve temiz-wheel kontrolü |
| 3 | Tasarım/görev/sonuç sözleşmeleri | 2.5 | Şema v1 ve API ADR'leri |
| 4 | Ortak çekirdeğin kontrollü genişletilmesi | 3 | Geriye uyumlu doğrulanmış simülasyon yolu |
| 5 | İlk gerçek uçtan uca throughflow yolu | 2–4 | Tek kademeli ampirik kayıplı örnek |
| 6 | Çok kademe ve çözünürlük yönetimi | 5 | Çok kademeli doğrulanmış sonuçlar |
| 7 | Kayıp/sapma modellerinin fiziksel kapsamı | 6 | Model bazlı doğrulama ve seçim sistemi |
| 8 | İleri fizik ve çoklu çalışma noktaları | 6–7 | Aynı tasarımın çok noktalı/ileri çözümü |
| 9 | Skor, görev ailesi ve feasibility audit | 8 | Eğitim için kalibre edilmiş görevler |
| 10 | Dış tüketici, toplu eğitim ve performans | 9 | Temiz kurulum ve güvenilir reward entegrasyonu |
| 11 | Benchmark, dashboard ve kayıtlar | 9–10 | Repo içi bütünleşik kullanım |
| 12 | Sürüm, dokümantasyon ve güncelleme provası | 10–11 | Dağıtıma hazır sürüm adayı |

Kilometre taşları: M0 = Faz 2 sonunda gerçek backend kanıtı; M0.5 = Faz 2.5 sonunda ortak runtime kabulü; M1 = Faz 5 sonunda ilk uçtan uca örnek; M2 = Faz 8 sonunda çok kademeli/ileri simülasyon; M3 = Faz 10 sonunda dış eğitim tüketicisi; M4 = Faz 12 sonunda bütünleşik sürüm adayı.

## 5. Faz 0 — Başlangıç durumu ve regresyon tabanı

**Amaç:** Entegrasyonun neyi değiştirdiğini ölçebilmek ve eski ortamı korumak.

Yapılacak işler:

- [x] Python/işletim sistemi/kurulu bağımlılık sürümlerini ve mevcut git durumunu kaydet; gizli anahtarları rapora alma.
- [x] Mevcut testleri proje venv'iyle çalıştır; önceden var olan arızaları entegrasyon regresyonundan ayır.
- [x] Heat exchanger için başarılı, schema_error, drc_error, simulation_error ve çok noktalı örneklerden küçük bir regresyon seti oluştur.
- [x] Mevcut import davranışı ve wheel içeriğini doğrula; `prompts` paketinin dağıtımıyla ilgili belge/kod tutarsızlığını not et.
- [x] Kullanıcı gereksinimlerini test kimliklerine bağla: basit kullanım, çok kademe, çözünürlük, kayıp, dış kurulum, güncelleme.
- [x] İstenen özellikleri core/advanced/experimental olarak etiketle; bu etiketlerin destek kanıtını temsil ettiğini, kullanıcı isteğini sessizce daraltmadığını belirt.

Çıktılar: başlangıç test raporu, eski çıktı örnekleri, gereksinim–test matrisi.

Kabul: Değişiklik öncesi durum tekrar üretilebilir; yeni geliştirme sırasında kıyaslanacak küçük referans seti hazırdır. Mevcut kırık testler ayrı kayıtlıdır.

## 6. Faz 1 — Lisans sınırı, kaynak sabitleme ve kurulum

21 Eylül durumu: Windows 3.12 import başarılı; 3.9.0 import başarısız. Kullanıcı kararıyla public runtime Faz 2.5'te 3.12'ye yükseltildi; tam 3.9.6 deneyi artık kabul hedefi değil. Linux denenmedi. Lock adayları ve hash manifest'i hazır; dağıtım onayı veya production kurulum garantisi yok. İşaretli maddeler incelemenin yapıldığını, belirsizliğin çözüldüğünü değil, gösterir.

**Amaç:** Kurulabilir ve dağıtım sınırları anlaşılmış bir backend temeli hazırlamak.

Yapılacak işler:

- [x] Seçilecek NASA release/commit'inde README lisans bağlantısını, paket metadata'sını, telif bildirimlerini ve dağıtım dosyalarını doğrula. Kök LICENSE eksikliğini genel NASA lisans şablonunu kendimiz doldurarak kapatma.
- [x] Kod, kayıp tabloları, referans geometri ve örnek çıktıların kaynak/hak kayıtlarını ayrı tut. Çözülmemiş dağıtım izni ilgili varlığın yayınını bloke eder; bağımsız şema/API çalışmasını durdurmaz.
- [x] Yeniden dağıtımda lisans/bildirim ve kaynak erişimi; değişiklikte tarih/yazar/köken kaydı yükümlülüklerini kontrol listesine çevir. NASA onayı izlenimi veren ürün ifadeleri kullanma. [NOSA §3](https://opensource.org/license/NASA-1.3)
- [x] Özgün SuniMuhendis kodu ile NASA'dan türetilen patch'leri ayır. Fork gerekirse kaynak adresi, parent SHA, patch listesi ve lisans kaydını zorunlu kıl.
- [x] Eski Python 3.9 hedefinin dependency/import uyumsuzluğunu ölç; runtime kararını ayrı fazda kaydet. Python 3.12 Windows/Ubuntu paket CI kabulü Faz 2.5'te tamamlandı; NASA backend'inin Linux probe'u ayrıca açık.
- [ ] Doğrulanmış Python/NASA/NumPy/SciPy/Cantera ve diğer transitif bağımlılık kombinasyonunu kilitle.
- [x] Bir paket indeksindeki benzer isimli dağıtımı otomatik olarak NASA kaynağı sayma; wheel/sdist kaynak kökenini doğrula.
- [x] `throughflow` extra'sı için yayın stratejisini seç: doğrulanmış indeks sürümü veya ilk geliştirme döneminde sabit Git commit'i. Git bağımlılığı kullanılırsa gerekli Git erişimini ve indeks yayın kısıtlarını belgele.
- [ ] Kayıp verileri için sabit kaynak SHA + hash manifest'i tasarla. Python sürümüne bağlı pickle uyumluluğunu sınama kapsamına al.
- [ ] Verileri kurulum/hazırlık aşamasında atomik indir; hash doğrulamasından önce yükleme. Değerlendirme yolunda indirme yapma.

NOSA'nın özgün katkı şartı ve ayrı eser sınırı bakımından dağıtım adayı incelemesi planlanır; yalnız dosyaları farklı klasöre koymak lisans sonucunu garanti etmez. Hukuki belirsizlikler ve gerekiyorsa uzman doğrulaması yayın öncesi kayıtta görünür olur.

Çıktılar: bağımlılık kilidi adayı, lisans/köken envanteri, backend manifest'i, kurulum raporu.

Kabul: Backend temiz ortamda import olur; seçilen kaynak kimliği sabittir; dağıtılacak bileşenlerin lisans durumu kaydedilmiştir. Python 3.12 kararı Faz 2.5'te kullanıcı onayı, metadata, test ve temiz tüketici kanıtıyla kaydedilmiştir; Linux ve eğitim reposu kabulü ayrıca kapanır.

## 7. Faz 2 — NASA yetenek ve doğruluk araştırması

21 Eylül durumu: Deney taraması ve hata vakaları kaydedildi. Geometri/closure incelemesi kısmi; gelişmiş ampirik kayıplı güvenilir referans kabul şartı açık. Düzeltmeler [rapordaki B01–B08 listesinde](throughflow_phase_0_2/README.md).

**Amaç:** README'de anlatılan ile gerçekten çalışanı ayırmak; adaptörü varsayımlara göre tasarlamamak.

Yapılacak işler:

- [x] Upstream örneklerinden küçük ve hızlı türbin/kompresör referansları seç; geometri/sonuç kökenini kaydet.
- [x] Önce doğrudan NASA API'siyle çalıştır; adaptör ortaya çıkmadan backend davranışını ölç.
- [ ] Tek kademe ve en az iki kademe örneklerinde sıra/stage eşleşmesini, RPM atamalarını ve geometri mutasyonlarını incele.
- [x] `num_streamlines=1` yolunu ayrı test et. Desteklenmeyen model/mod kombinasyonunda meanline çalışıyor iddiası üretme; doğrulanmış en düşük çözünürlüğü bildir.
- [x] Örneğin 3/5/9/17 streamline seviyelerini aday tarama olarak dene; bunlar garanti edilmiş destek veya nihai varsayılan değildir.
- [ ] Pressure-balance ve angle-matching modlarında başlangıç/son geometri ve açıları karşılaştır; kütüphanenin neleri değiştirdiğini kaydet.
- [x] Her makine için en az bir sabit ve bir ampirik kayıp yolunu sınama adayı yap. Hata veren model için tekrarlanabilir minimal örnek çıkar.
- [x] Modelin kaybı gerçekten radyal hesaplayıp hesaplamadığını kontrol et; skaler değerin diziye yayılmasını ayrı raporla.
- [ ] İnlet/outlet closure'ın hangi girdileri kabul ettiğini ve hangi miktarları çözdüğünü kaydet; aşırı belirlenmiş sınır koşullarını tespit et.
- [x] Convergence history, massflow dizisinin kümülatif mi bant bazlı mı olduğu, güç işareti ve basınç oranı yönünü denetle.
- [x] Tekrarlı çağrı ve A→B→A sırasıyla mutable-state etkisini araştır.
- [x] Soğutma, karşı dönüş, radyal geçit ve tasarım dışı noktaları küçük örneklerle tarayarak ileri yetenek tablosunu hazırla.
- [x] Her örnekte süre, bellek, yakınsama ve dış ağ/GUI/dosya yan etkilerini ölç.

Kaynak incelemesi için başlangıç noktaları: [türbin çözücüsü](https://github.com/nasa/turbo-design/blob/main/turbodesign/turbine_spool.py), [kompresör çözücüsü](https://github.com/nasa/turbo-design/blob/main/turbodesign/compressor_spool.py), [TD2](https://github.com/nasa/turbo-design/blob/main/turbodesign/loss/turbine/TD2.py), [Kacker–Okapuu](https://github.com/nasa/turbo-design/blob/main/turbodesign/loss/turbine/kackerokapuu.py). Bu bağlantılar hareketli `main` kaynaklarıdır; kanıt raporunda test edilen SHA'ya çevrilir.

Destek tablosunun her satırı şu alanları taşır: makine/geometri/model/çözüm modu, denenmiş çözünürlükler, referans kimliği, kaynak SHA, sonucu doğrulayan test, sınırlama, supported/experimental/unsupported durumu.

Çıktılar: çalışan NASA referansları, sayısal başlangıç sonuçları, yetenek matrisi, patch gereksinim listesi, performans ölçümü.

Kabul: En az bir ampirik kayıplı throughflow yolu gerçekten çalışmıştır; çok kademe ve yüksek çözünürlüğün engelleri somuttur. Bir yetenek başarısızsa kapsam dışı diye kaybolmaz: düzeltme, alternatif desteklenen model veya açık ürün sınırlaması kararı alınır. Kullanıcının temel hedeflerini engelleyen açıklar M4 öncesi kapanmalıdır.

### 7.1 Faz 2.5 — Python 3.12 runtime geçişi

**Amaç:** SuniMuhendis, NASA backend ve dış eğitim tüketicisini tek desteklenen Python minor sürümünde birleştirmek.

- [x] Paket sözleşmesini `>=3.12,<3.13` yap; eski classifier'ları kaldır.
- [x] Geliştirme referansını `.python-version` ile 3.12.10 olarak kaydet.
- [x] Doğrulanmış doğrudan bağımlılıklar için `constraints/python312.txt` ekle.
- [x] Windows'ta tam testi, wheel build/metadata kontrolünü ve repo-dışı temiz tüketici kurulumunu çalıştır.
- [x] Python 3.9'un yeni wheel'i reddettiğini doğrula.
- [x] Windows ve Linux için Python 3.12 CI işi ekle.
- [x] Uzak CI'da Windows ve Linux işlerinin geçtiğini gör.
- [ ] Özel eğitim reposunu aynı runtime/constraint sözleşmesine geçirip gerçek environment çağrısını çalıştır.

Kabul: Yerel Windows kanıtı tamamlandı: 229 test geçti; wheel doğru runtime metadata'sı taşıdı ve temiz venv'de heat exchanger çalıştı. Uzak Windows/Ubuntu CI da geçti. Fazın tüketici kabulü özel eğitim reposu deneyi tamamlanınca kapanır. [Geçiş raporu](python312_migration.md).

## 8. Faz 3 — Tasarım, görev ve sonuç sözleşmeleri

**Amaç:** Basit örnekte kolay, çok kademede yeterli ve eğitimde kararlı bir dış arayüz tanımlamak.

### 8.1 Tasarım sözleşmesi

- [ ] Birim sistemini SI olarak sabitle; açılarda derece/radyan alan adları ve dönüşüm tek bir yerde tanımlansın.
- [ ] Hub/shroud geçit eğrileri, kanat sıraları, stage kimlikleri, shaft bağlantıları ve geometri alanlarını tanımla.
- [ ] Türbin/kompresör ve axial/radial/mixed-flow ayrımını tipli tanımla; yalnız doğrulanan türler supported olur.
- [ ] Kanat sayısı, chord, axial chord, pitch/solidity gibi birbirinden türeyen büyüklüklerde bağımsız değişkenleri seç. Çelişen girdiyi sessizce üstüne yazarak çözme.
- [ ] Clearance'ın metre mi span oranı mı olduğunu açık alan adıyla belirt; NASA dönüşümünü adaptöre bırak.
- [ ] Metal açılarıyla akış açılarını, rotor relatif açılarıyla mutlak açıları ayır. Akış açısını otomatik olarak imal edilebilir kanat geometrisi sayma.
- [ ] Radyal dağılımları `[0,1]` span koordinatında kontrol noktalarıyla tanımla; sıralı/benzersiz koordinat, endpoint ve interpolasyon kurallarını yaz.
- [ ] Sayısal streamline ağı değişirken kontrol noktalarını yeniden tasarımlama; interpolasyon yöntemi sürümlensin.
- [ ] `extra="forbid"`, finite-number denetimi, gerçek integer alanları ve belgelenmiş optional/default/null davranışı uygula.
- [ ] Varsayılanlar yalnız belgelenmiş model için geçerli olsun; gereken geometri bilgisi yoksa gelişmiş model uydurma sabitle çalışmasın.
- [ ] Kademe sayısını sıralardan türet veya bağımsız verilirse eşitliğini doğrula; çelişen iki topoloji kaynağı oluşturma.

### 8.2 Görev ve yürütme sözleşmesi

- [ ] `environment`, task/schema/score sürümleri, operating_conditions, design_space, physics, numerics, requirements ve objectives bloklarını tanımla.
- [ ] Sabit ve serbest RPM, kademe sayısı, soğutma payı gibi değişkenler için sahiplik/öncelik kuralı belirle; aynı alan iki yerde çelişirse hata ver.
- [ ] Kayıp/sapma modellerini görev belirlesin; gerekirse her sıra için görevde eşleme bulunsun. Tasarım JSON'undan çalıştırılabilir kod veya keyfi Python import yolu kabul etme.
- [ ] Benchmark modunda çözünürlük ve model seçimlerini kilitle. Araştırma amaçlı override etkin görevden yeni fingerprint üretsin ve kıyaslanabilirliği açıkça işaretlesin.
- [ ] Solver-supported iterasyon ayarı ile dış kabul toleransını ayır. Backend ayarı desteklemiyorsa konfigürasyonu reddet; etkisiz parametre kabul etme.
- [ ] Kaynak tüketimini sınırlamak için görev bazlı sıra/kontrol noktası/streamline üst sınırı koy; tek kademeyi mimariye gömülü sabit sınır yapma.
- [ ] Secondary çalışma noktalarının primary koşulların hangi alanlarını devralabildiğini whitelist ile belirle.

### 8.3 Sonuç ve hata sözleşmesi

- [ ] `SimulationResult`: status, metrics, raw_data, diagnostics, provenance; skor alanı yok.
- [ ] Toplam metriklerle row/stage/span dağılımlarını ayır; küçük ödül yanıtı ile ayrıntılı inceleme yanıtı aynı çözümden gelsin.
- [ ] Güç tüketimi/üretimi, total/static basınçlar, pressure/expansion ratio ve verim tanımlarını isimleriyle ayrıştır.
- [ ] Alan ortalaması, aritmetik ortalama ve kütlesel ağırlıklı ortalamayı birbirinin yerine kullanma; her metrik için toplama tanımı yaz.
- [ ] NaN/Inf değerlerini normal JSON sayısı gibi dışarı çıkarma; geçersiz sonucu tanısıyla döndür.
- [ ] Fiziksel tasarım ihlali, model geçerlilik notu, numerical_failure, infrastructure_failure ve configuration_error sınıflarını tanımla.
- [ ] `reward_eligible` bilgisini güvenilirlik/başarıyla ilişkilendir; bir sonuçta sayısal skor bulunması otomatik eğitim örneği olması anlamına gelmesin.
- [ ] Zaman damgası, duvar saati, işçi PID gibi değişken telemetriyi deterministik fizik payload'ından ayır.

Çıktılar: JSON Schema v1, Python tipleri taslağı, basit/çok kademeli örnek JSON'lar, API ve hata politikası ADR'leri.

Kabul: Aynı örnek hem basit kullanıcı akışını hem ayrıntılı tasarımı ifade eder. Her alanın sahibi, birimi, varsayılanı ve hata davranışı bellidir. Henüz gerçek olmayan tam geometri örnekleri çalışır örnek olarak yayımlanmaz.

## 9. Faz 4 — Ortak çekirdeği geriye uyumlu genişletme

**Amaç:** Fizik ve skor yollarını ortaklaştırmak; throughflow için gerekli kontrolleri heat exchanger'a özel kurallara dönüştürmemek.

Yapılacak işler:

- [ ] Public `BaseEnvironment.simulate(design_params, task_params)` yolu ekle; schema→DRC→prepared inputs→physics sıralamasını ortak yardımcıya taşı.
- [ ] `evaluate()` aynı çözüme skor eklesin; aynı tasarım için iki farklı doğrulama/fizik uygulaması oluşmasın.
- [ ] Mevcut `BaseSimulator.simulate()` tuple arayüzünü ilk sürümde koru; public typed sonuç ona uyum katmanı olsun.
- [ ] Göreve bağlı tasarım sınırları için varsayılan no-op hook ekle; mevcut `run_drc(design)` imzasını zorunlu olarak değiştirme.
- [ ] Throughflow görev/bağımlılık ön kontrolünü pahalı çözümden önce yap; deney konfigürasyonu hataları reward sıfıra çevrilmesin.
- [ ] Tipli backend/altyapı istisnaları genel `except Exception` içinde tasarım hatasına dönüşmeden yeniden yükseltilebilsin.
- [ ] Simülasyon başarısızlığında mevcut tanılar ve kısmi çıktılar korunsun; kısmi çıktı başarılı skor girdisi olmasın.
- [ ] Secondary nokta sonuçlarının metrics, diagnostics ve gerekirse ayrıntılı payload'ını koru.
- [ ] Nokta sonuçlarından skor girdisi hazırlayan environment-agnostic hook ekle. Varsayılan davranış eski uyarı toplamını korusun.
- [ ] Requirement v1'in gte/lte yapısını koru; bant gereksinimini iki sınırla ifade et, gerekmedikçe genel operatör sistemini büyütme.
- [ ] Heat exchanger ve dummy ortamlar için durum, metrik, skor ve mevcut hata mesajı davranışını regresyon testleriyle kontrol et.

Özel dikkat: Bu fazda bütün eski hataları yeni bir sınıflandırmaya zorlamak yoktur. Throughflow'un açık tipli hataları ve yeni hook'lar eklenirken eski ortamların sözleşmesi korunur.

Çıktılar: ortak simulate/evaluate yolu, tanı tipleri, çok nokta skor hook'u, çekirdek regresyon testleri.

Kabul: Mevcut testler geçer; eski sonuçlar beklenen biçimde kalır; throughflow için hatalar doğru sahipliğe ayrılır. Geometri/geçerlilik kontrolleri tasarım girdisini mutasyona uğratmaz.

## 10. Faz 5 — İlk uçtan uca gerçek throughflow ortamı

**Amaç:** Bir NASA örneğini bütün SuniMuhendis katmanlarından geçirmek.

Yapılacak işler:

- [ ] Registry'ye lazy factory ekle; optional dependency eksikliğinde anlaşılır kurulum hatası ver.
- [ ] En küçük doğrulanmış geçit ve kanat sırası şemasını implement et; çok kademe alanlarını mimaride baştan koru.
- [ ] Pozitif boyut, hub/shroud sırası, sıra konumları, çakışma ve geometri tutarlılığı için DRC ekle.
- [ ] Adaptörde yalnız açık eşlemeler kullan; dict alanlarını keyfi `setattr` ile NASA nesnesine taşımaktan kaçın.
- [ ] Her değerlendirmede bağımsız NASA/akışkan durumu oluştur. Global cache dizini gibi süreç ayarlarını işçi başlatımında sabitle.
- [ ] Bir sabit kayıp örneği ve Faz 2'de çalışan bir ampirik kayıp örneği sağla; ampirik yol bu fazın zorunlu kabulüdür.
- [ ] Çıktıyı tanımlı metriklere dönüştür; NASA API'siyle doğrudan çalıştırılan referansla karşılaştır.
- [ ] Çözüm kabulünde finite değerler, boundary koşulları, kütle dengesi ve fiziksel işaret denetimini uygula.
- [ ] Ham girdi ve çözüm sonrası etkin geometriyi ayrı kaydet; sabit tasarım modunda değişmemesi gereken alanları doğrula.
- [ ] `examples` altında script ve JSON örneği, kurulan pakette küçük bir demonstration fixture sağla.

Çıktılar: çalışan `make_env("turbomachinery_throughflow")`, skorsuz simülasyon, ilk hata örnekleri ve doğru metrik dönüşümü.

Kabul: NASA doğrudan çağrısı ile adaptör sonucu ilan edilmiş toleranslarda uyuşur. Fiziksel doğruluk ayrıca dengeler/referanslarla sınanır; yalnız aynı kütüphaneyle eşleşmek doğruluk kanıtı sayılmaz. Tek kademeli ampirik örnek internet ve GUI olmadan tekrar çalışır.

## 11. Faz 6 — Çok kademe, sıra topolojisi ve çözünürlük

**Amaç:** Kullanıcının çok kademeli ve çok streamtube isteğini tam tasarım sözleşmesi içinde karşılamak.

Yapılacak işler:

- [ ] Değişken uzunluklu rotor/stator listeleri ve tutarlı stage/shaft bağlantıları uygula; türbin ve kompresörün sıra düzenlerini karıştırma.
- [ ] Sıra aralıkları, eksenel konum/geçit koordinatı dönüşümü, yarıçap ve blade geometry aktarımını doğrula.
- [ ] Sıra ve kademe güçleri, toplam basınç/sıcaklık değişimleri ve makine toplamları arasında tutarlılık kontrolleri ekle.
- [ ] `num_streamlines` ile streamtube bant sayısını açıkça ayır; backend'in kümülatif debi dizisini yanlış toplamayı engelle.
- [ ] Aynı radyal tasarım kontrol noktalarını farklı çözüm ağlarına taşı; ağ sayısını tasarım özgürlük derecesi yapma.
- [ ] Düşük/orta/yüksek çözünürlük karşılaştırması yap; güç, debi, verim ve radyal profillerin değişimini raporla.
- [ ] Mesh/refinement çalışmalarında değişimin monoton olacağını varsayma; seçilen referanslarda kabul edilebilir stabiliteyi ölç.
- [ ] Kademeye göre debi dengesi ve soğutmasız enerji denklemlerini bağımsız hesapla.
- [ ] Küçük ve büyük problem süre/bellek ölçümünden görev üst sınırları için ilk öneriyi çıkar.

Çıktılar: en az iki kademeli türbin ve kompresör örnekleri, çözünürlük raporu, sıra/kademe metrikleri.

Kabul: Kademe eklemek yeni Python sınıfı veya özel script gerektirmez. Çok kademeli çözümler fiziksel kabulden geçer. Çözünürlük değişiminin tasarımı değiştirmediği test edilir. Çok noktalı/geometrisi değişken tasarımlarda backend sınırları açıkça kayıtlıdır.

## 12. Faz 7 — Kayıp/sapma modelleri ve geçerlilik

**Amaç:** Sabit kayıptan daha ayrıntılı fiziği güvenilir şekilde kullanılabilir kılmak.

Yapılacak işler:

- [ ] Kayıp modeli registry'si oluştur: stable id, backend implementation, required fields, data manifest, machine/geometry/mode desteği, loss definition ve valid range.
- [ ] Sapma modellerini ayrı seçim olarak ele al; loss ile deviation aynı varsayım değildir.
- [ ] Sabit loss/efficiency yalnız açık seçilmiş baseline olarak kullanılabilsin; başarısız ampirik modele fallback yapılmasın.
- [ ] Her desteklenen model için rotor ve stator, birden fazla streamline, kritik geometri ve sınıra yakın çalışma testleri ekle.
- [ ] Pressure/enthalpy/entropy/polytropic kayıp türlerinin backend tarafından gerçekten desteklenen kombinasyonlarını doğrula; enum'da var diye destek ilan etme.
- [ ] Modelin girdilerini pertürbe ederek ilgili fiziksel etkinin hesapta aktif olduğunu sınama: Reynolds, Mach, clearance, solidity, açı vb. Her büyüklük için evrensel monotonluk dayatma.
- [ ] Ortalama kaybı bütün açıklığa yayan modelleri bu şekilde etiketle; bunu yerel radyal kayıp çözümü diye sunma.
- [ ] Modelin yerel uygulanması isteniyorsa upstream algoritmanın bu kullanıma uygunluğunu doğrula; ortalama korelasyonu her noktaya çağırmak kendiliğinden geçerli yöntem değildir.
- [ ] Kayıp verisi dosyalarını ve interpolasyon nesnelerini sabit/hash doğrulamalı cache'ten yükle; veri eksikliği eğitim ödülüne dönüşmesin.
- [ ] Model kullanım aralığı dışındaki çıktıyı fidelity note olarak bildir. Eğitime uygunluk için görevin önceden tanımlı politikası uygulansın; hakemin sınırlamasını keyfi tasarım cezası yapma.
- [ ] Kimliği/sürümü belli özel kayıp modelleri için Python tarafında güvenilir registration yolu tasarla; benchmark JSON'undan kod çalıştırma yok.
- [ ] Hata/fizik düzeltmeleri gerekiyorsa ayrı patch set'i ve öncesi/sonrası raporu hazırla; SuniMuhendis içine NASA fonksiyonu kopyalama.

Çıktılar: model manifest'leri, test edilmiş kayıp/sapma seçenekleri, geçerlilik tanıları, gerekiyorsa fork commit'i.

Kabul: Desteklenen her ampirik modelin gerçekten akış/geometriye bağlı olduğu ve çoklu streamline girdilerini doğru işlediği kanıtlıdır. Eksik geometri açık hata üretir. En az bir doğrulanmış ampirik seçenek hem temel türbin hem temel kompresör yolunda mevcuttur; farklı modeller kullanılabilir.

## 13. Faz 8 — İleri fizik, tasarım modu ve çoklu çalışma noktaları

**Amaç:** Backend'in doğrulanabilen ileri olanaklarını kullanıcıya tutarlı konfigürasyonla açmak.

Yapılacak işler:

- [ ] Sabit tasarım değerlendirmesi ve solver-assisted inverse design için ayrı mode değerleri uygula; görevler/skor kıyasları bu ayrımı taşısın.
- [ ] Assisted modda değiştirilebilir alanları whitelist ile tanımla; çözücü değiştirdiği alanların başlangıç/son değerlerini raporlasın.
- [ ] Secondary noktalarda aynı fiziksel geometriyi kullan; assisted tasarım çözümü gerekiyorsa önce tek geometriyi dondur, sonra off-design değerlendir.
- [ ] Debi/basınç/devir sınır koşullarının closure kurallarını makineye göre uygula; bütün noktaları aynı sayısal çözüm biçimine zorlamadan aynı görev API'sinde tut.
- [ ] Değişken akışkanlar için mechanism dosyası, bileşim, faz ve termodinamik referansları kaydet; mekanizma hash'i deney kimliğine girsin.
- [ ] Soğutma için giriş noktası, miktarı, T/P/bileşimi ve payın hangi debiye göre tanımlandığını sabitle; kütle/enerji dengesine soğutmayı dahil et.
- [ ] Görev izin veriyorsa sıra/shaft bazlı RPM ve karşı dönüş tanımla; backend spool varsayılanlarının bunları ezmediğini test et.
- [ ] Axial dışındaki passage yollarını model uygunluğu ve referans sonuçla doğrula. Radyal çözücü desteği ile axial kayıp korelasyonunun geçerliliğini birbirine eşitleme.
- [ ] Incidence/off-design geçerliliği olmayan modelden güvenilir off-design harita bekleme; gerektiğinde uyumlu model veya belgeli sınırlama kullan.
- [ ] Birleşik ileri örnekte çok kademe + yeterli radyal çözünürlük + ampirik kaybı birlikte çalıştır; tek tek feature testleriyle yetinme.
- [ ] Soğutma/karşı dönüş/radyal çalışma için en az birer destek kanıtı veya açık engel kaydı çıkar. Kullanıcının temel kabulünden ayrı, çözülmemiş ileri destek maddelerini saklama.

ShaftMatch veya tam kompresör–türbin eşleme aynı ortamın ilk sürümüne zorunlu olarak eklenmez; tek makine throughflow kapsamını aşarsa ayrı takip fazı olarak kaydedilir. Kanat yapısal/ömür analizleri ve 3B CFD bu planın fizik iddiası değildir.

Çıktılar: ileri kullanım örnekleri, çok noktalı SimulationResult, final capability matrix, geometri sabitliği testleri.

Kabul: Tek JSON/API ile temel ve doğrulanmış ileri modlar kullanılabilir. Aynı makinenin çalışma noktaları arasında geometri korunur. Destek durumu açık olmayan özellik normal benchmark görevine açılamaz. İleri örneklerin birleşik çalışması test edilmiştir.

## 14. Faz 9 — Skor, görev ailesi ve feasibility audit

**Amaç:** Çözülen sayıları anlamlı, sömürüye dayanıklı bir öğrenme sinyaline dönüştürmek.

Yapılacak işler:

- [ ] Türbin ve kompresör için ayrı görev gereksinimleri tanımla: gerekli güç/debi/basınç oranı, sıcaklık/Mach gibi doğrulanabilir sınırlar.
- [ ] Gereksinimleri tasarımcıya verilmiş boundary condition'larla karıştırma. Çözücüye zorunlu girdi olarak verilen hedefi bağımsız başarı diye tekrar ödüllendirme.
- [ ] Gate + kalite yaklaşımı kullan; gate_share ve kalite ölçeklerini bu görevin fizibilitesine göre kalibre et. Heat exchanger katsayılarını otomatik kopyalama.
- [ ] Verim tanımını göreve sabitle; total-to-total, total-to-static, polytropic ve entropy tabanlı verimleri birbirinin yerine kullanma.
- [ ] Fiziksel karşılığı olmayan genel maliyet skoru ekleme. İlk sürümde güvenilir verim ve tanımlı geometri/karmaşıklık ölçütleri kullanılabilir; proxy açıkça proxy olarak adlandırılır.
- [ ] Debi, güç ve basınç oranındaki bağlantılar nedeniyle aynı fiziksel miktarın birden fazla bileşende ödüllendirilip ödüllendirilmediğini incele.
- [ ] Çok nokta görevlerinde her noktanın hard requirement'ını ayrı denetle; kaliteyi minimum veya önceden tanımlı ağırlıklı değerle birleştir.
- [ ] Kötü tek noktayı iyi ortalamanın gizleyemediği testler yaz.
- [ ] Skor hesaplama kodu yalnız normalize edilmiş metriklerle çalışsın; backend importuna gerek olmadan offline rescore mümkün olsun.
- [ ] Yakınsamama, timeout ve altyapı hatası için eğitim örneği dışlama politikasını uygula. Kanıtlı geometrik/geçerli görev ihlalleriyle solver bilinmezliğini ayır.
- [ ] `sample_designs(n, seed, task_params)`, `get_requirements`, `list_design_checks` ve mümkün olan `analyse_physics` hook'larını uygula.
- [ ] Örnekleme uzayını geometrik geçerlilik sağlayan ama iyi tasarımlara aşırı daralmayan koordinatlarda kur; düşük fizibiliteyi sadece sampler körlüğüyle açıklamamak için kapsam raporu çıkar.
- [ ] Her görevde gereksinimleri karşılayan reference_designs ekle. Görev tam skora ulaşılabilir diyorsa bunu ayrıca doğrula.
- [ ] Üç başlangıç görev ailesi oluştur: kolay tek kademe, çok kademe, aynı geometrinin çok noktalı performansı. Holdout koşulları eğitimden ayrı tanımlansın.
- [ ] Görev başına audit bütçesini çözüm maliyetine göre ayarla; mevcut 20.000 örneklik varsayılanı pahalı çözücüye körlemesine taşıma.
- [ ] Audit raporunda çözülmüş, çözülememiş ve geçerlilik dışı örnek sayıları ayrı olsun. Gözlenen en iyi skoru kanıtlanmış global optimum diye sunma.

Çıktılar: sürümlü throughflow score v1, görev aileleri, feasibility/witness raporları, adversarial reward testleri.

Kabul: Skor `[0,1]` içinde ve deterministiktir; gereksinimi kaçıran ile geçen tasarım anlamlı ayrılır. Fizibiliteden sonra kaliteyi geliştirecek ödül aralığı vardır. Her görev referans tasarımla desteklidir; numerical/infrastructure failure başarılı eğitim etiketi olmaz.

## 15. Faz 10 — Dış eğitim reposu, paketleme ve performans

**Amaç:** Ortamı başka repodan kolayca kurulabilir ve uzun eğitim döngülerinde güvenilir biçimde çağrılabilir yapmak.

### 15.1 Paketleme ve kullanıcı API'si

- [ ] `throughflow` extra'sını ve `all` extra'sının yeni içeriğini açıkça belgele; base ve heat_exchanger kurulumlarını ayrı test et.
- [ ] Core + environments + parsing + kullanılacak prompt/schema/resource araçları wheel içinde yer alsın; model_clients/baselines/dashboard bağımlılığı oluşmasın.
- [ ] Örnek görev/tasarım dosyalarını package resources olarak sun. Mevcut çalışma dizini veya repo içindeki results klasörü gerektirmesin.
- [ ] Göreve göre JSON Schema ve prompt oluşturma API'si sağla; prompt ile gerçek doğrulama sözleşmesi aynı kaynaktan gelsin.
- [ ] `describe()` veya eşdeğer metadata API'siyle sürüm/capability/metric tanımlarını dışarı sun.
- [ ] Üretilen wheel'i yeni venv'de, kaynak repo dışındaki bir dizinden test et; editable install ile geçen test tek başına yeterli değildir.
- [ ] Kaynak checkout erişimi olmayan tüketici örneğinde simulate, evaluate, JSON serialization ve prompt üretimini çalıştır.

### 15.2 Eğitim güvenilirliği ve ölçekleme

- [ ] Büyük batch'lerde giriş sırasını koruyan evaluate-many örneği/yardımcısı sağla; ilk sürüm için gerekenden büyük dağıtık framework ekleme.
- [ ] Varsayılan paralellik izolasyonunu süreç tabanlı kur; NASA/Cantera nesnelerini işçiler arasında paylaşma.
- [ ] Windows spawn ve Linux süreç başlatımı için import-safe worker tasarla; tekrar yürütülen modül kodu hatalarını test et.
- [ ] Sert timeout gerektiğinde işçi sürecini sonlandırabilecek yürütme modeli kullan; Python thread timeout'unun hesabı durdurduğunu varsayma.
- [ ] Her işçide yeni değerlendirme durumu, temiz geçici dizin ve sabit asset cache kullan; eşzamanlı veri indirme yarışını hazırlık aşamasında çöz.
- [ ] Worker ölümü/cancel/timeout durumunda yarım sonucun cache'e veya geçerli reward'a yazılmasını engelle.
- [ ] BLAS/OpenMP thread sayısı ile worker sayısını birlikte sınırla; oversubscription altında ölçüm yap.
- [ ] Retry politikasını sürümlü ve sınırlı tut. Retry sırasında geometri, kayıp modeli veya tolerans değiştirilirse bunu aynı değerlendirme sayma.
- [ ] Duvar saati timeout'unun makine yüküne bağlı olduğunu belgeleyip altyapı durumu olarak taşı; salt süre nedeniyle deterministik fizik skoru üretme.
- [ ] Eğitim örneği açıkça `reward_eligible`/status kontrol etsin. Mevcut scalar score kolaylığı altyapı hatalarını sıfır ödüle çeviren bir yardımcıya dönüşmesin.

### 15.3 Cache ve ölçüm

- [ ] Physics cache anahtarı: canonical resolved design + physical task/points + numerics + backend/adapter versions + asset/mechanism hashes + gereken runtime fingerprint.
- [ ] Score cache kimliği ayrıca score version ve gereksinim/ağırlıkları kapsasın; fizik cache'i ile rescore ayrılabilsin.
- [ ] Canonical JSON'da key order sabitlenir; float yuvarlamasıyla farklı tasarımlar birleştirilmez.
- [ ] Başarısız altyapı sonuçlarını başarılı fizik sonucu gibi cache'leme; request id'leri ve telemetry cache'ten yanlış taşınmasın.
- [ ] Basit/çok kademeli/ileri örneklerde cold-start, warm-run, p50/p95 süre, peak memory ve başarı oranı raporla.
- [ ] Mutlak süre hedeflerini Faz 2 ölçümünden sonra sabitle; burada kanıtsız milisaniye garantisi verme.
- [ ] Aynı kilitli runtime'da tekrarlı fizik sonuçları deterministik olmalı. Platformlar arası karşılaştırmada ilan edilmiş sayısal toleranslar kullan; mevcut heat exchanger determinism testini gevşetme.

Çıktılar: kurulum yapılabilir wheel, dış tüketici örneği, reward alma akışı, batch/worker/caching testleri, performans raporu.

Kabul: Temiz tüketici yalnız yayıma aday paketi ve ilan edilmiş bağımlılıkları kullanır. Ağsız warm evaluation, çoklu süreç ve A→B→A testi geçer. Kullanıcının özel eğitim reposuna erişim yoksa sentetik tüketici testi tamamlanır; gerçek repo entegrasyonu yapılmış gibi raporlanmaz.

## 16. Faz 11 — Benchmark ve dashboard bütünleşmesi

**Amaç:** Aynı ortamın bu repo içindeki deney araçlarında kullanılmasını tamamlamak.

Yapılacak işler:

- [ ] API/manual benchmark çalıştırıcılarını ortak registry üzerinden environment seçer hale getir.
- [ ] Görevde `environment` varsa onu kullan; bilinmeyen değer hata olsun. Alanı olmayan tarihsel heat exchanger görevleri için açık legacy fallback koru.
- [ ] Simulator/schema/score/backend kimliklerini hardcoded sınıflardan değil ortam metadata'sından al.
- [ ] Prompt slug, task_id ve environment alanlarının birbiriyle uyumunu doğrula; başka ortam task'ına yanlış prompt göndermeyi engelle.
- [ ] Token/pricing accounting akışını olduğu gibi koru; simülatör çeşitlenmesi model API muhasebesini değiştirmesin.
- [ ] Throughflow için deterministic dummy design kaynağı ekle; heat exchanger tasarımı üreten dummy client'ı yeni ortama yanlışlıkla uygulama.
- [ ] Mevcut zero_shot/feedback_driven track ayrımını koru. Feedback-driven runner bu entegrasyonla kendiliğinden kapsam içine girmez.
- [ ] Dashboard task seçiminde environment + track ayrımı sağla; eski slug/dizin yapısını gereksiz taşımadan yeni görevleri ekle.
- [ ] Genel funnel, requirement tablosu ve score dağılımını ortak tut; özgül fizik panellerini ortam bazlı üret.
- [ ] Throughflow panellerinde stage/row performansı, radyal profiller, çözüm tanıları ve çalışma noktaları göster.
- [ ] Farklı backend/physics/score kimliklerini aynı leaderboard'a sessizce toplama. Karma kayıt varsa açık gruplama/uyarı sun.
- [ ] Re-score komutu yalnız mevcut metriklerle yeni skor hesaplasın; fizik değişikliği ayrı re-simulate işlemi olsun.
- [ ] Benchmark çıktılarında numerical/infrastructure hatalarına ayrı görünürlük ver; modelin tasarım başarısızlığı istatistiğine otomatik ekleme.

Çıktılar: ortam bağımsız runner seçimi, throughflow görev kataloğu, dashboard panelleri, kayıt uyumluluk testleri.

Kabul: Aynı çalıştırıcı heat exchanger ve throughflow görevini doğru ortamda çalıştırır. Offline dummy client ile tüm kayıt zinciri sınanır; ücretli LLM çağrısı test için zorunlu değildir. Eski kayıtlar ve token ledger çalışır kalır.

## 17. Faz 12 — Sürüm adayı, dokümantasyon ve NASA güncelleme provası

**Amaç:** Ortamı kullanılabilir bir paket olarak teslim etmek ve ilerideki backend değişimini yönetebilmek.

Yapılacak işler:

- [ ] Ortam/schema/adapter/score/backend sürümlerinin hangi değişiklikte arttığını ADR'de sabitle.
- [ ] Desteklenen backend kombinasyonunu çalışma başlangıcında doğrula; benchmark modunda bilinmeyen sürüme sessiz devam etme.
- [ ] Deneysel backend denemelerini açık modla ayır; bu koşullardan çıkan sonuçların standart kıyaslamaya katılmasını engelle.
- [ ] Basit kurulum, tek kademe, çok kademe, gelişmiş kayıp, çok nokta, dış eğitim ve hata yorumlama örneklerini tamamla.
- [ ] Capability matrix ve model sınırlamalarını kullanıcı dokümantasyonuna taşı; desteklenmeyen seçenekler örnek kodda çalışırmış gibi gösterilmesin.
- [ ] Wheel/sdist dosya listesi, lisans kayıtları, package resources ve dependency metadata'sını incele.
- [ ] Bu repoda henüz görünmeyen CI dizinini uygun iş akışlarıyla oluştur; temel test ve optional heavy integration test işlerini ayır.
- [ ] Doğrulanan işletim sistemi/Python matrisinde kurulumu ve referans çözümleri çalıştır; gereksiz tüm çapraz kombinasyonları vaat etme.
- [ ] Eski backend ile yeni aday backend'i ayrı venv'lerde aynı referans tasarımlara uygula.
- [ ] Karşılaştırma raporu üret: schema/DRC durumu, yakınsama, görev uygunluğu, metrikler, skor, tasarım sıralaması ve süre.
- [ ] Fizik farklarını yalnız toleransı büyüterek kapatma; nedenini belgele. Skor/sonuç anlamı değişiyorsa yeni ortam fiziği sürümü oluştur.
- [ ] Basit/karmaşık örnekleri sabit listeden seç; sadece yeni sürümün geçtiği örnekleri raporlayarak değişimi gizleme.
- [ ] Rollback provasında eski kilit ve asset manifest'i ile eski sonuçların tekrar üretilebildiğini göster.
- [ ] Kaynak ve veri erişilebilirliğini güvence altına al; lisansı uygunsa arşivleme, değilse yeniden edinim yöntemi ve erişim riski kaydı kullan.
- [ ] Son release notes içinde desteklenenler, bilinen sınırlamalar, sayısal değişiklikler ve migration adımlarını yaz.

Çıktılar: dağıtıma hazır sürüm adayı, kurulum/kullanım kılavuzu, CI, compatibility report, update/rollback runbook.

Kabul: M4 kontrol listesi tamamen değerlendirilmiştir. Gerekli ama başarısız bir madde varsa sürüm tam destekli diye etiketlenmez. Bu planın uygulanması yayın/merge/tag işlemlerini kendiliğinden yapıldığı anlamına gelmez; bunlar ayrıca kaydedilen sürüm işlemleridir.

## 18. Yakınsama ve fiziksel kabul politikası

Çözücü kabulü skor hesaplamasından önce yapılır. Üç düzey ayrı tutulur: sayısal tamamlanma, fiziksel tutarlılık ve modelin kullanım aralığı. Bunlardan yalnız birini geçen çözüm diğerlerini geçmiş sayılmaz.

| Kontrol | Uygulama ilkesi | Başarısızlığın yorumu |
|---|---|---|
| Finite state | İlgili P/T/rho/hız/güç ve dağılımlarda NaN/Inf yok | Sayısal başarısızlık |
| Kütle dengesi | Giriş + soğutma − çıkış; aynı zamanda sıralar/bantlar arası denge | Yakınsama/fizik tutarlılığı sorunu |
| Enerji dengesi | Enthalpy flux, shaft work ve soğutma birlikte; birim/işaret sabit | Yakınsama veya adaptör/backend sorunu |
| Boundary residual | Görevin gerçekten dayattığı koşullarla çözüm uyumu | Eksik/yanlış closure veya yakınsamama |
| Geometri sabitliği | Sabit modda seçilmiş tasarım alanları değişmedi | Değerlendirme sözleşmesi ihlali |
| Model geçerliliği | Korelasyon/modelin desteklenen aralığı | Fidelity sınırlaması; tasarım cezasıyla karıştırılmaz |
| Gereksinimler | Görevin istediği mühendislik performansı | Geçerli çözülmüş ama görevi karşılamayan tasarım |

Kütle residual'ı için aday tanım `abs(m_out - m_in - m_coolant) / max(abs(m_in) + abs(m_coolant), m_floor)` olur. Enerjide farklı makineler ve variable-cp akışkanlar için entalpi temelli kontrol kullanılır; sabit Cp formülü genelleştirilmez. Toleranslar Faz 2/6 referansları ve ölçek analiziyle belirlenir, testle birlikte sürümlenir. Çözücünün iç durma ölçütü bu dış kontrollerin yerine geçmez.

## 19. Hata ve eğitim davranışı matrisi

| Olay | Public davranış hedefi | Eğitim davranışı |
|---|---|---|
| Tasarım şeması geçersiz | schema_error ve alan tanısı | Görev politikası gereği geçersiz tasarım ödülü |
| Geometrik/görev tasarım sınırı ihlali | drc_error veya tipli design_constraint tanısı | Geçersiz tasarım ödülü |
| Geçerli çözüm, gereksinim eksik | success + düşük skor + unmet requirements | Normal öğrenme örneği |
| Fiziksel olarak kanıtlanmış kapasite ihlali | Tipli tasarım/fizik ihlali | Önceden tanımlı görev politikası |
| Yakınsamama | simulation_error + numerical_failure + korunmuş tanılar | Varsayılan olarak ödül örneğinden dışla; fiziksel imkânsızlık diye etiketleme |
| Geçerlilik aralığı dışı çözüm | Fidelity notu + güvenilirlik bilgisi | Görevin önceden belirlenmiş politikasına göre dışla veya ayrı deney |
| Eksik asset/yanlış backend sürümü | Tipli configuration/dependency exception | Koşuyu düzelt; sıfır reward üretme |
| Timeout/worker crash | Tipli execution failure; harness kayıt altına alır | Retry/dışlama; tasarım başarısızlığına otomatik sayma |
| Hatalı görev parametresi | Konfigürasyon exception'ı | Deneyi durdur/düzelt |

Throughflow için yeni hata ayrımları genel heat exchanger davranışını değiştirmez. Harness tipli exception'ları kayıtlayabilir; core bunları sessiz başarısız tasarıma çeviremez. `ScoreResult` şeması nedeniyle tutulabilecek placeholder skor tek başına tüketilmez; public örnek `reward_eligible` kontrolünü gösterir.

## 20. Public API hedefi ve kullanım örnekleri

Aşağıdaki API uygulanacak hedefi gösterir. `task` ve `design`, pakette sağlanacak doğrulanmış örneklerden veya kullanıcının JSON dosyalarından okunur.

```python
from sunimuhendis import make_env

env = make_env("turbomachinery_throughflow")

simulation = env.simulate(
    design_params=design,
    task_params=task,
)

evaluation = env.evaluate(
    task_id=task["task_id"],
    task_params=task,
    design_id="candidate_001",
    design_params=design,
)

# Hedef sözleşme: güvenilirlik bilgisi skorun yanında açıkça sunulur.
if evaluation.raw_simulation_output.get("reward_eligible", False):
    reward = evaluation.score.normalized_total
else:
    # Numerical/infrastructure kayıtları normal reward örneği yapılmaz.
    reward = None
```

Schema/DRC hatalarının eğitim açısından uygunluğu da aynı işaret üzerinden tutarlı ifade edilir; bu alan yalnız başarılı simülasyonda eklenmez. Nihai alan yerleşimi Faz 3 ADR'sinde dondurulur; örnekte mevcut EvaluationResult biçimini koruyan raw payload yolu gösterilmiştir.

Hazırlık ve çalışma ayrı tutulur. Önerilen komutlar, henüz var olan komutlar değildir:

```powershell
# Repo içi geliştirme, venv aktive edildikten sonra:
python -m pip install -e ".[throughflow,dev]"

# Sabit manifest'teki gerekli fizik verilerini hazırlama:
python -m sunimuhendis.environments.turbomachinery_throughflow prepare

# Kurulum, sürüm ve veri hash'lerini hızlı kontrol:
python -m sunimuhendis.environments.turbomachinery_throughflow doctor
```

Dış repo kurulumunda yayımlanmış doğrulanmış SuniMuhendis sürümü/etiketi ve deney lock dosyası kullanılır. Paket indeksi yayını yapılmadan `pip install sunimuhendis==...` komutunun kullanılabilir olduğu iddia edilmez; mevcut Git kurulum modeli korunabilir.

## 21. Planlanan dosya ve modül sorumlulukları

Yeni modüller için hedef kök: `src/sunimuhendis/environments/turbomachinery_throughflow/`. Tablo içindeki dosya adları bu kökte oluşturulacak taslak modüllerdir; mevcut dosya değillerdir.

| Modül | Sorumluluk |
|---|---|
| `__init__.py` | Hafif public exports |
| `schema.py` | Design, passage, row ve radyal profile şemaları |
| `task.py` | Görev/physics/numerics/çalışma noktası doğrulaması ve çözümleme |
| `drc.py` | Geometrik ve topolojik kontroller |
| `env.py` | BaseEnvironment hook'ları ve public ortam |
| `simulator.py` | Backend çağrısı, tanı ve kabul akışı |
| `backend.py` | NASA sürümüne özgü nesne eşlemesi; başlangıçta tek backend dosyası yeterli |
| `loss_models.py` | Kayıp/sapma model registry ve capability metadata |
| `metrics.py` | Birimler, ortalama/toplama ve row/stage/machine sonuçları |
| `validation.py` | Yakınsama, dengeler ve fiziksel kabul |
| `score.py` | Sürümlü skor ve requirement aggregation |
| `sampling.py` | Deterministik audit örneklemesi; wheel dışında kalan baselines paketine bağlı değil |
| `assets.py` | Manifest, hash kontrolü ve hazırlık |
| `provenance.py` | Fizik fingerprint'i ve sonuç kimliği |
| `execution.py` | Gerekli throughflow worker/timeout/cache işlemleri |
| `__main__.py` | prepare/doctor kullanıcı komutları |
| `resources/` | Dağıtım hakkı doğrulanmış küçük örnekler ve manifest'ler |

Bu liste sorumluluk sınırını tanımlar; her küçük sorumluluk için hemen ayrı dosya zorunlu değildir. Birden fazla backend sürümü gerçek ihtiyaç oluşturmadan genel plugin framework'ü inşa edilmeyecek.

Yeni testlerin hedef kökü `tests/throughflow/`; temiz tüketici senaryoları `tests/packaging/` altında önerilir. Dokümantasyon için `docs/throughflow/` hedeflenir. Bu dizinler uygulama fazlarında oluşturulur.

## 22. Test stratejisi ve kabul matrisi

| Test ailesi | Kritik senaryo | Hangi fazda zorunlu? |
|---|---|---|
| HE regresyon | Eski başarı/hata, primary/secondary, skor sürümleri | 0, 4 ve son entegrasyon |
| Şema/DRC | Yanlış birim/alan, çelişen geometri, sıra/topoloji, görev sınırı | 3–5 |
| Adaptör | Aynı NASA örneğiyle metrik ve geometri eşlemesi | 5 |
| Fizik | Kütle/enerji/sınır koşulu, finite, işaretler | 5–8 |
| Çok kademe | İki veya daha fazla stage, sıra toplamları | 6 |
| Çözünürlük | Aynı tasarımın farklı streamline sayıları | 6 |
| Kayıp | Modelin girdilere tepkisi, radyal davranış, required fields | 7 |
| İleri özellik | Soğutma, karşı dönüş, axial dışı passage; uygun model | 8 |
| Çok nokta | Aynı geometri, bir noktadaki başarısızlık, aggregation | 8–9 |
| Reward | Gate sınırları, çifte ödül, exploit, tutarlı uygunluk işareti | 9 |
| Audit | Witness geçer; bozuk/imkânsız görevler yakalanır | 9 |
| Paket | Wheel, base-only, HE-only, throughflow, repo dışı cwd | 10 |
| Determinizm | A→A, A→B→A, tek/çok worker | 10 |
| Yürütme | Timeout, crash, cancel, cache invalidation | 10 |
| Harness | Ortam seçimi, eski görev fallback, sürüm kaydı | 11 |
| Güncelleme | Eski/yeni backend karşılaştırması ve rollback | 12 |

Golden sonuçlar regresyonu gösterir; fiziksel doğruluğun tek kanıtı değildir. Kapalı form/korunum kontrolleri, uygun bağımsız referans ve mümkünse ölçüm/CFD karşılaştırmasıyla desteklenir. Bu ek referanslar birebir geometri/koşul eşleşmiyorsa farkların nedeni ve kıyasın sınırı belirtilir.

Hızlı sözleşme testleri NASA bağımlılığı olmadan çalışabilir; gerçek fizik integration testleri yalnız ilgili extra kurulu işlerde koşar. İlgili extra yok diye tüm CI'da fizik testlerinin sürekli skip olması başarılı doğrulama sayılmaz. Her desteklenen kayıp/mode kombinasyonunun en az bir çalışan CI/release testi olur.

## 23. Riskler, erken göstergeler ve karşılıkları

| Risk | Erken gösterge | Karşılık |
|---|---|---|
| Lisans/köken belirsizliği | Seçilen artifact'ta bildirim yok | İlgili yeniden dağıtımı durdur, kaynağı netleştir; özgün API çalışması sürer |
| Python minor/runtime ayrışması | Tüketici kurulumunun metadata veya dependency çözümünde durması | `>=3.12,<3.13`, ortak constraint, temiz-wheel tüketici testi ve iki işletim sistemi CI |
| Model multi-streamline çalışmıyor | Scalar/array hataları | Minimal repro, fiziksel anlamı korunmuş patch, ayrı sürüm |
| Ortalama kayıp sanılan yerel model | Bütün radyal noktalarda aynı sonuç | Yeteneği doğru etiketle; yerel modeli bağımsız doğrula |
| Geometri çözüm sırasında değişiyor | Önce/sonra farkı | Sabit/assisted ayrımı ve invariant kontrolü |
| Solver hatası model başarısızlığı sayılıyor | Timeout/asset hatalarında sıfır reward | Tipli hata ve reward eligibility |
| Çalışma noktası aşırı belirlenmiş | Hedefler aynı anda dayatılıyor | Makine/mod bazlı closure doğrulaması |
| Eğitim modeli hakemi sömürüyor | Uç geometride yüksek skor, düşük fidelity | Domain sınırı, audit, adversarial test ve uygunluk politikası |
| Yeni sürüm fiziği değiştiriyor | Golden/witness/skor sırası kayıyor | Fizik sürümü, karşılaştırma raporu ve rollback |
| Kurulum yalnız repo içinde çalışıyor | Wheel'de eksik veri veya scripts importu | Repo dışı temiz tüketici testi |
| Eğitim maliyeti çok yüksek | Çok kademe yüksek p95 süresi | Ölçülmüş fidelity profilleri, worker/caching; fizik düşürmeyi açık deney yap |

## 24. İş paketleri ve uygulama sırası

Her paket incelemeye uygun sınırlı bir değişiklik olarak hazırlanır. Bu liste otomatik commit/PR/yayın talimatı değildir.

| Paket | İçerik | Çıkış bağımlılığı |
|---|---|---|
| P01 | Başlangıç regresyonu, kaynak/lisans ve runtime raporu | Faz 0–1 |
| P02 | NASA capability spike ve doğrudan referanslar | Faz 2 |
| P02.5 | Python 3.12 metadata, constraint, CI ve temiz-wheel tüketici kontrolü | Faz 2.5 |
| P03 | Şemalar, hata/API/closure ADR'leri | Faz 3 |
| P04 | Geriye uyumlu core simulate ve tanı akışı | Faz 4 |
| P05 | Throughflow registry, adaptör, ilk ampirik örnek | Faz 5 |
| P06 | Çok kademe ve streamline refinement | Faz 6 |
| P07 | Loss/deviation registry, veri manifest ve fizik testleri | Faz 7 |
| P08 | Çok nokta ve doğrulanmış ileri özellikler | Faz 8 |
| P09 | Skor, görev ailesi, witness/audit | Faz 9 |
| P10 | Wheel/resources, dış tüketici, batch/timeout/cache | Faz 10 |
| P11 | Runner, dashboard, kayıt ve rescore | Faz 11 |
| P12 | Dokümantasyon, CI, update/rollback, sürüm adayı | Faz 12 |

İlk çalışma P01 ve P02'dir: upstream'in gerçek davranışı görülmeden kapsamlı adaptör veya skor yazılmayacak. Mimariyi dondurma eşiği Faz 3; eğitim ödülü için kabul eşiği Faz 9–10; bütünleşik teslim eşiği Faz 12'dir.

Kesin takvim Faz 2'den önce verilmez. En büyük belirsizlik dosya sayısı değil; upstream kayıp modellerinin doğruluğu, çoklu streamline uyumluluğu ve gerekli fizik düzeltmeleridir. Faz 2 sonunda iş paketleri için ölçülmüş referans süreleri ve patch boyutuna dayalı süre tahmini yapılır.

## 25. Faz 2 sonrasında kapatılacak kararlar

| Karar | İlk tercih | Karar için gereken kanıt |
|---|---|---|
| Backend kaynak kimliği | Doğrulanmış upstream release/commit | Gerçek kurulum, lisans/köken ve referans çözümler |
| Fork ihtiyacı | Yalnız zorunlu düzeltmede | Repro + test + upstream düzeltme durumu |
| İlk türbin kayıp modeli | Çalışan/geçerli ampirik aday | Çoklu streamline ve fizik kapsamı |
| İlk kompresör kayıp modeli | Çalışan/geçerli ampirik aday | Aynı koşullarda model doğrulaması |
| Minimum streamline | Backend/model için doğrulanan sayı | Tek streamline ve düşük çözünürlük deneyleri |
| Varsayılan benchmark fidelity | Ölçümle seçilen sabit profil | Refinement ve süre raporu |
| Runtime | `>=3.12,<3.13`; referans 3.12.10 | Windows/Ubuntu CI tamam; eğitim reposu bekleniyor |
| Off-design destek kapsamı | Uygun model ve sabit geometri | Closure/incidence/korunum kontrolleri |
| İleri kombinasyon sınırları | Mümkün olan doğrulanmış kapsam | Birleşik senaryo testleri |
| Sürüm numarası | Mevcut paket politikasına uygun yeni sürüm | API/physics değişikliklerinin son hali |

Bu kararlar olağan mühendislik bulgularıyla kapatılır. Kullanıcıya ancak Python hedefini değiştirmek, ana kapsamı daraltmak veya dış yayın yapmak gibi mevcut kapsamı etkileyen bir karar kaldığında somut seçeneklerle dönülür.

## 26. Son teslim paketi

- Kurulabilir SuniMuhendis sürüm adayı ve sabitlenmiş throughflow bağımlılık profili.
- Repo içinden ve repo dışından aynı public API ile çalışan örnekler.
- Tek kademe, çok kademe, ampirik kayıp ve doğrulanmış ileri kullanım senaryoları.
- Tasarım/görev JSON Schema'ları, prompt üretimi ve birimli metrik kataloğu.
- Fiziksel kabul, hata ayrımı ve eğitimde reward tüketimi belgeleri.
- Görev ailesi, reference designs ve audit raporları.
- Lisans/kaynak/veri envanteri ve backend/asset manifest'leri.
- Performans, determinism, temiz kurulum ve regresyon kanıtları.
- NASA sürüm yükseltme/karşılaştırma/geri dönüş kılavuzu.
- Destek matrisi ve tamamlanmamış ileri yeteneklerin açık listesi.

Tamamlanma raporu her gereksinimi kanıtlayan test/örnek/rapora bağlar. Desteklenmeyen özelliği yalnız yeni bir isimle veya hazır ayarla gizlemek; yalnız sabit loss demosunu bitirip tüm throughflow entegrasyonunu tamamlandı saymak kabul edilmez.
