# Throughflow — Faz 0–2 araştırma raporu

Tarih: 21 Eylül 2026. Çalışma dalı `codex/throughflow-phase-0-2`, PR #2 ile `main` dalına birleştirildi. Başlangıç commit'i: `41332783398f847f3aab5b6c38d398c91f078b40`.

**Karar: Entegrasyon için araştırma tabanı hazır; backend henüz eğitim hakemi olarak kabul edilebilir değil.** Mevcut heat exchanger korunarak gerçek NASA örnekleri çalıştırıldı. Basit ve çok kademeli çözüm yolları gözlendi; gelişmiş kayıp, Python uyumu ve sayısal kabul konusunda açık engeller bulundu. Bu çalışma yeni bir production environment veya `throughflow` extra'sı yayımlamaz.

## Fazların durumu

| Faz | Yapılan | Kapanış durumu |
|---|---|---|
| 0 | Mevcut testler, beş regresyon örneği, kaynak hash'leri, temiz wheel tüketimi ve gereksinim matrisi | Tamamlandı |
| 1 | Sabit NASA checkout, iki Python kurulumu, dependency envanteri, lisans ve asset araştırması | Araştırma tamamlandı; Linux ve dağıtım kapısı açık |
| 2 | 65 backend senaryosu + 7 bağımlılık uyumsuzluğu deneyi; gerçek upstream testleri ve semantik inceleme | Araştırma tamamlandı; gelişmiş ampirik kayıplı güvenilir referans kabul şartı sağlanmadı |
| 2.5 | Public paket ve geliştirme ortamı Python 3.12'ye geçirildi; constraint, CI ve wheel kontrolleri eklendi | Windows ve Ubuntu CI tamamlandı; özel eğitim reposu geçişi bekliyor |

Bu ayrım önemlidir: hata bulmuş olmak araştırmanın çıktısıdır, fakat başarısız kabul ölçütünü tamamlanmış saymaz. Faz 3 API taslağı bu bulgularla ilerleyebilir; backend destek sözleşmesi ve yayın kararı henüz dondurulmamalıdır.

## İzolasyon ve Faz 0

Çalışma, ana repo yerine Codex tarafından yönetilen ayrı worktree'de yapıldı. Ana repodaki HE score/CLAUDE değişiklikleri, `heat_exchanger_hard_v5` sonuçları ve `test_score_v5.py` bu dala alınmadı. Önceki fazlı plan yalnız belge olarak kopyalandı. Faz 0 ölçümü alınırken `src/`, `pyproject.toml`, `LICENSE` ve `NOTICE` değiştirilmemişti; Faz 2.5 sonradan yalnız Python paket metadata'sını değiştirdi.

- Başlangıç: **222 test geçti**, arıza yok; [JUnit](baseline_pytest.xml).
- [Beş referans vaka](heat_exchanger_baseline.json): başarı, schema_error, drc_error, çok çalışma noktası ve bilerek enjekte edilmiş simulation_error. Sonuncusu fizik arızası örneği değil, hata sözleşmesi testidir. Fizik vakaları tekrarlandığında birebir aynı çıktı alındı; son kontrol de aynı sonuçları verdi.
- [Temiz tüketici sonucu](packaging_baseline.json): wheel ayrı venv'e kuruldu, repo dışında geçici dizinde `python -I` ile çağrıldı. Skor **0.7288073927259057**, metrikler referansla birebir aynı. `turbodesign` import edilmedi.
- Wheel `prompts` paketini içeriyor; `model_clients` ve `baselines` içermiyor. Eski AGENTS açıklamasındaki prompts hariç varsayımı güncel paket davranışıyla uyuşmuyor.
- Kullanılan proje venv'i **Python 3.12.10**. Belgede belirtilen Python 3.9.6'yı çalıştırmış gibi raporlamıyoruz.

Son test sayıları ve deney ölçümleri [summary.json](summary.json) dosyasından okunabilir. Araştırma araçlarının testleri solver fizik testleri değildir.

## Sabit kaynak, runtime ve güncelleme kararı

Kaynak: [nasa/turbo-design, 23c2b0b](https://github.com/nasa/turbo-design/tree/23c2b0bf781b4b030014f458ecfde872896777a2).
Tam SHA: `23c2b0bf781b4b030014f458ecfde872896777a2`; kaynak metadata sürümü **1.4.3**.

| Deneme | Sonuç | Kanıt |
|---|---|---|
| Windows / Python 3.12.10 / NumPy 2.5.3 / SciPy 1.18.1 / Cantera 3.2.0 | Temiz kurulum ve import başarılı; fizik sorunları aşağıda | [manifest](backend_manifest_py312.json), [runtime](runtime_py312_followup.json) |
| Windows / Python 3.9.0 | Dependency çözümü ve `pip check` başarılı; NASA import başarısız | [manifest](backend_manifest_py39.json), [traceback](runtime_py39.json) |
| Python 3.9.0 | Yeni SuniMuhendis wheel'i kurulumu metadata tarafından reddediliyor | Faz 2.5 negatif kurulum kontrolü |
| Linux | WSL/Docker çalışma ortamı bulunmadığı için denenmedi | Açık kabul maddesi |
| NumPy 1.26.4 + aynı SciPy 1.18.1 | Uyumsuz dependency kombinasyonu: SciPy >=2.0 NumPy istiyor, `np.long` import arızası | `probes/py312_numpy126/` |

3.9 import hatası `fixedpressureloss.py:16` satırındaki ertelenmemiş `float | npt.ArrayLike` annotation'ında çıkıyor; kaynakta başka PEP 604 kullanımları da var. Metadata'nın `>=3.9` demesi yeterli değil. Yalnız NumPy düşürme deneyi geçerli bir alternatif dependency çözümü değildir ve KO modelinin eski NumPy'de çalışmadığını kanıtlamaz. Deney sonrası araştırma venv'i 2.5.3'e geri alındı ve `pip check` geçti.

İlk kurulumun [Python 3.12 kilit adayı](requirements_py312.txt) ve [Python 3.9 kilit adayı](requirements_py39.txt) ayrı. Bunlar hash'li yayın lock'u değil, kurulan Windows sürümlerinin kaydıdır. EEE-HPC için sonraki profile `openpyxl==3.1.5` ve `et-xmlfile==2.0.0` eklendi; [follow-up gereksinimleri](requirements_py312_followup.txt) bunu açıkça gösterir.

PyPI sorgusunda en yeni dağıtım **1.4.2** çıktı; `license` ve `project_urls` alanları boştu. Kaynak 1.4.3 ile eşdeğerliği kurulmadı: [PyPI kaydı](pypi_provenance.json). Bu nedenle ilk geliştirme adayı sabit Git SHA'sıdır; `pip install turbo-design` üretim kaynağı kabul edilmez.

Faz 2.5 kararıyla SuniMuhendis public runtime sözleşmesi `>=3.12,<3.13` oldu; geliştirme referansı 3.12.10'dur. Ayrı 3.12 worker varsayımı kaldırıldı. Windows'ta 229 test, wheel metadata kontrolü ve temiz repo-dışı HE tüketici deneyi geçti; aynı skor **0.7288073927259057** üretildi. PR ve birleşme sonrası workflow koşularında Windows ve Ubuntu test/build/temiz-wheel işleri geçti. Özel eğitim reposu bu workspace'te bulunmadığı için onun migration'ı ayrıca yapılacak. Ayrıntı: [Python 3.12 geçiş raporu](../python312_migration.md).

Güncellemede yeni SHA + tam dependency profili + asset hash'leri birlikte sürümlenmeli. Bu rapordaki baseline ve yetenek vakaları yeniden çalışmadan sürüm değiştirilmemeli. Hareketli `main` veya sessiz solver/model fallback'i kabul edilmeyecek.

## Lisans ve veri kökeni

Kendi paketin metadata'sı Apache-2.0. NASA [README](https://github.com/nasa/turbo-design/blob/23c2b0bf781b4b030014f458ecfde872896777a2/README.md#license) NOSA'ya işaret ediyor; fakat seçili checkout'ta LICENSE/NOTICE/COPYING dosyası ve paket metadata'sında lisans kaydı bulunamadı. Oluşturulan NASA wheel'inde de lisans dosyası ve `.pkl` kayıp tabloları yok: [wheel incelemesi](nasa_wheel_inspection.json). Bu, izin yok hükmü değildir; dağıtım adayı için eksik kanıttır. Genel şablondaki NASA alanları tarafımızdan doldurulmadı.

[NOSA 1.3](https://opensource.org/license/NASA-1.3) §1E–F ve §3I ayrı yazılımın daha büyük bir ürün içinde birleşmesini ele alır. Bu temel üzerinde özgün adaptörümüzün Apache-2.0 kalması hedeflenebilir; NASA bileşeni ve ondan türeyen değişiklikler kendi koşullarını korur. Sadece ayrı klasör veya process kullanmak türev eser değerlendirmesini otomatik çözmez.

Yayın öncesi kontrol: NASA'nın geçerli lisans/telif metnini edinmek; dağıtıma lisans ve gerekli kaynak erişimini eklemek (§3A–B); patch için köken, tarih, değişiklik ve katkı sahibi kaydı tutmak (§3C–D); özgün katkı haklarını doğrulamak (§3G); NASA onayı izlenimi yaratmamak (§3E). Fork olursa parent SHA, patch listesi ve lisans dosyaları ayrıca izlenecek. Bu araştırmada NASA kaynağı patch'lenmedi.

| Varlık | Bu fazda kullanım | Dağıtım durumu |
|---|---|---|
| NASA Python kaynakları | Ignore edilen ayrı `build/` checkout'unda import | SuniMuhendis wheel'ine alınmadı; lisans/telif kaydı açık |
| Dört `.pkl` kayıp tablosu | Aynı SHA'dan lokal kopya, boyut ve SHA-256 manifest'i | Repo paketine alınmadı; veri hakları ve pickle/Python uyumu ayrı incelenecek |
| Örnek geometri / giriş dosyaları | Orijinal checkout'tan okunuyor | Kaynak dosyaları kopyalanmadı; hak kaydı açık |
| Araştırma JSON sonuçları | Türetilmiş sayısal sonuçlar; bazı geometri ve açı değerlerini de içerir | Kaynak SHA/vaka bilgisi tutulur; herkese açık yayın öncesi geometri kökeni incelemesine dahildir |
| Transitif bağımlılıklar | Sürüm ve metadata envanteri | Tam üçüncü taraf bildirim incelemesi henüz yapılmadı |

Özellikle `pyturbo-aero` ve `plot3d` için boş lisans metadata'sı lisanssızlık olarak yorumlanmadı. Cantera/NumPy/SciPy dahil envanter manifest'te; bağımlılıkların kaynak lisans dosyaları ayrıca doğrulanmalı. Bu rapor hiçbir NASA bileşenini Apache-2.0 olarak yeniden lisanslamaz.

## Faz 2: Gerçek çalıştırma sonuçları

[Makineyle okunabilir özet](summary.json), [tam yetenek matrisi](capability_matrix.md) ve `probes/` altında traceback dahil vaka kayıtları var.

İlk 59 vakada **22 sonuç dönüşü / 37 hata**; 6 takip vakasında **1 sonuç dönüşü / 5 hata**. Geçersiz NumPy/SciPy kombinasyonundaki 7 import hatası ayrı grupta tutuldu. `completed`, yalnız solve çağrısının döndüğünü anlatır; bütün kayıtlarda `physical_validation=not_certified` vardır. Bu oranlardan genel backend başarı oranı veya tasarım kalitesi çıkarılamaz.

| Yol | Gözlem | Destek kararı |
|---|---|---|
| 1 ve 2 kademeli axial türbin, upstream sabit kayıp, n=1/3/5/9/17 | Varsayılan streamline ayarında argüman hatası; açıkça `adjust_streamlines=False` seçilince bütün seviyeler döndü | Experimental; otomatik fallback yapılmadı |
| 2 kademe / 17 streamline | 11.120 MW civarı, fakat sıralar arası debi yayılımı yaklaşık **%3.188** | Yakınsama kabulü geçilmiş sayılmaz |
| Tek kademe kompresör, upstream sıfır sabit kayıp, n=1/3/5/9/17 | Döndü; n=3: 527.700 kW, PR=1.322718, eta_p=1.007857 | Experimental; verim tanımı/fizik incelemesi gerekli |
| Tek kademe kompresör / DiffusionLoss / n=3 | 527.297 kW, PR=1.322383, eta_p=1.007867 | Basit akışa bağlı kayıp; gelişmiş ampirik doğrulama kabulü değil |
| Türbin TD2; ayrıca EEE-HPT ve fixed-loss warm start | Denenen yollar NaN/Cantera hatasıyla kesildi | Bu konfigürasyonlarda desteklenmedi |
| Kacker–Okapuu / Ainley–Mathieson / n=3 | Sırasıyla array→float ve array truth-value hataları | Model/geometri/runtime incelemesi açık |
| Craig–Cox / Traupel / n=3 | NaN sıcaklık / Cantera hataları | Bu örneklerden doğruluk iddiası çıkarılamaz |
| AxialCompressorAungier / n=1/3/5/9/17 | Relative Mach bracket; daha düşük üç debi denemesi de başarısız | Modelin kendisinin her koşulda çalışmadığı hükmü değil; geçerli referans aranacak |
| EEE-HPC / 10 kademe / 12 streamline | Önce eksik openpyxl; sonra IGV kapasite kontrolünde durdu | Çok kademeli kompresör kabulü henüz yok |
| EEE-HPT / 2 kademe / 5 streamline | Upstream sabit kayıp, sabit streamline ile 16.786 MW, PR≈4.812 | Experimental |
| Radyal türbin / 5 streamline | 28.609 kW, PR≈1.282; eta_p≈1.0117 | Experimental; fizik kabulü yok |
| Angle matching, %1 soğutma, karşı dönüş | Sabit streamline türbin varyantları sonuç döndürdü | İleri özellik taraması; kalibrasyon/validasyon yok |
| Off-design | Varsayılan türbin yolu argüman hatasına takıldı; A→B→A deneyindeki sabit streamline B noktası çalıştı | Harita doğrulaması veya sabit geometri off-design garantisi değil |
| Tekrar kullanım | Türbin aynı obje tekrarı ve yeni objelerle A→B→A birebir aynı; kompresör ikinci solve'da hata | Her çağrıya yeni backend state önerilir |

NASA'nın kendi testleri ayrıca çalıştı: **372 geçti, 4 xfail** (361 hızlı + 11 slow). Xfail'ler santrifüj modellerde upstream'in kabul ettiği açık sorunları içeriyor; beklenen başarısızlıklar başarı sayılmadı. Bunlar axial yetenek matrisindeki arızaları ortadan kaldırmaz: [hızlı testler](upstream_py312.xml), [slow testler](upstream_slow_py312.xml).

## Fizik/API sözleşmesine etki eden bulgular

Kaynak bağlantıları aynı [sabit SHA](https://github.com/nasa/turbo-design/tree/23c2b0bf781b4b030014f458ecfde872896777a2/turbodesign) içindir.

1. **Streamline ve streamtube aynı sayaç değildir.** Çok noktalı `flow_math.compute_massflow` dizisi kümülatif debidir: bant debisi ardışık farklardan çıkar; ilk eleman sınırdır. n=1 özel yolu tek annulus alanını kullanır. Adaptör NASA'nın `num_streamlines` terimini açıklamalı; n=17'yi 17 bağımsız bant diye sunmamalı.
2. **TD2 radyal çözünürlüklü kayıp değildir.** Kaynak açı/hız ortalamalarından tek Y hesaplayıp `row.r` boyunca yayar. Streamline sayısını artırmak bu modeli tam spanwise korelasyona dönüştürmez. DiffusionLoss spanwise dizi hesaplar fakat eşik/ramp biçiminde basit bir modeldir. Aungier implementasyonunun kaynak açıklamaları da kısmi/best-effort kapsam belirtir.
3. **İşaret ve ortalamalar farklıdır.** Türbinde PR=P0_in/P0_out, kompresörde tersidir. İkisinin `total_power()` çıktısı da kendi üretim/tüketim yönünde pozitiftir. PR ve eta hesaplarında aritmetik ortalamalar var; bunu kütlesel ağırlıklı performans diye adlandırmayacağız. Eta>1 değerlerini clip ederek gizlemek yok.
4. **Çözüm modu tasarımı değiştirebilir.** `massflow_static_pressure`, angle matching'i seçiyor; solver `alpha2/beta2` akış açılarını değiştiriyor. Metal açılarını aynı alan sanmamalıyız. `axial_chord` hem spool hazırlığında hem Reynolds hesabında yeniden atanabiliyor. Kaydedilen solve öncesi/sonrası geometri, constructor öncesi mutasyonları kapsamaz. Tam geometri immutability kabulü sonraki faza açık.
5. **Boundary profili kaybı var.** `Outlet.init_static/init_total`, verilen basınç dizisinin ilk değerini tüm span'a yayıyor (`outlet.py:48–50,68–70`). Keyfi outlet basınç profili destekleniyor diye şema dondurulamaz. Debi+basınç+açı birlikte verildiğinde hangi büyüklüğün serbest olduğu mode ile belirlenmeli; tam aşırı-belirlenmişlik validator'ı bu fazda yok.
6. **Dönmek yakınsamak değildir.** Kayıtlarda convergence history ve seçili alanlarda finite kontrolü var. Debi yayılımı `(max-min)/abs(mean)` ile `total_massflow_no_coolant` üzerinden ölçüldü. Bu, enerji/radyal denge/soğutma bilançosunu kanıtlamaz. 17 streamline iki kademe sonucu sayısal kabul katmanını zorunlu kılıyor.
7. **Yan etkiler kontrol edilmelidir.** LossBaseClass kullanıcı `TD3_HOME` değerini üzerine yazar; bazı modeller eksik pickle'ı hareketli GitHub main'den indirir. Araştırma child process'inde USERPROFILE izole edildi, dört dosya hash kontrolünden sonra yerleştirildi, socket bağlantıları engellendi, GUI/export çağrıları AST ile bastırıldı. Bu, ham NASA API'sinin yan etkisiz olduğu iddiası değildir.

Süre ölçümü worker içindeki import+solve bölümünü kapsar; OS process başlatma ve bazı hazırlık işleri dışarıdadır. İlk matris medyanı ≈1.96 s, maksimumu ≈14.81 s; tepe working set ≈199 MiB. Farklı vaka ve hatalar birlikte olduğu için bunu eğitim throughput tahmini saymıyoruz. İlk run log isimleri profiller arasında çakışmış olabilir; kanonik kanıt ayrı JSON kayıtlarıdır. Güncel araç logları da profile göre ayırır.

## Faz 2 kapanışı için düzeltme sırası

| ID | Gerekli iş | Kapanış kanıtı |
|---|---|---|
| B01 | Lisans/telif, tablo ve örnek geometri kökenini tamamla | Dağıtılacak her varlık için kaynak/lisans/bildirim kaydı |
| B02 | Python 3.12 stratejisini bütün tüketicilerde doğrula | Windows/Ubuntu CI tamamlandı; özel eğitim reposu kurulumu geçmeli |
| B03 | `adjust_streamlines` üç argüman sözleşmesi ile iki argüman çağrılarını düzelt | Hareketli streamline ile 1/2 kademe ve çözünürlük regresyonu |
| B04 | TD2 başlangıç NaN, KO skaler/dizi, AM array ve diğer kayıpların gereken geometri/alanlarını doğrula | Her makine için fiziksel referansla doğrulanmış ampirik kayıp yolu; fixture yanlışsa önce fixture düzeltmesi |
| B05 | Debi/enerji/radyal denge ve verim tanımlarını dış kabul katmanında doğrula | Dönen ama kabul edilmeyen çözüm reward girdisi olmasın |
| B06 | EEE-HPC operating point/geometri tutarlılığı ve Aungier closure'ını incele | Çok kademeli kompresör için tekrarlanabilir kabul edilmiş referans |
| B07 | Mutable state, chord ve angle matching sahipliğini ayır | Girdi değişmezliği, taze obje tekrarları, gerçek sabit geometri off-design testi |
| B08 | Asset hazırlığını ve cache yolunu backend sözleşmesine taşı | Sabit SHA/hash, offline solve; pickle uyumu ve cache izolasyonu |

Önerilen bir sonraki adım B03–B04 için küçük, ayrı testli backend düzeltme çalışmasıdır; B02'nin kalan eğitim-reposu kontrolü paralel kabul kapısıdır. NASA kaynaklarını bu repoya kopyalayıp rastgele katsayılarla sonuç üretmek yerine, her değişiklik kendi minimal hata vakası ve fizik gerekçesiyle ele alınmalı. Gerekirse ayrı fork ve NOSA değişiklik kaydı kullanılmalı. B01, NASA backend'i veya varlıklarının dağıtımını bloke eder; proje tarafından yazılan API/şema taslağına ve açıkça sınırlandırılmış araştırma raporunun yayımlanmasına engel değildir. Public sınır [THIRD_PARTY.md](../../THIRD_PARTY.md) dosyasında korunur.

## Tekrar üretim

PowerShell komutları worktree kökünden çalıştırılır. Üretim venv'ini değiştirmeyin. `build/` ve `.venv/` ignore edilir. Windows checkout uzun yollar için yalnız ilgili clone'da `core.longpaths=true` kullanır.

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
git -c core.longpaths=true clone https://github.com/nasa/turbo-design build/throughflow_research/turbo-design
git -C build/throughflow_research/turbo-design config core.longpaths true
git -C build/throughflow_research/turbo-design checkout --detach 23c2b0bf781b4b030014f458ecfde872896777a2
python -m pip install -r reports/throughflow_phase_0_2/requirements_py312.txt
python -m pip install --no-deps -e build/throughflow_research/turbo-design
python scripts/throughflow_research/inspect_backend.py
python scripts/throughflow_research/probe_backend.py --label reproduction --timeout 90
python -m pip install -r reports/throughflow_phase_0_2/requirements_py312_followup.txt
python scripts/throughflow_research/probe_backend.py --select followup --label reproduction_followup --timeout 90
python scripts/throughflow_research/summarize.py
```

Bu kurulumda `python` 3.12.10 olmalıdır. `inspect_backend.py` çalışılan Python'a ait manifest/kilit dosyasını yeniler: mevcut kanıtı korumak için yeniden üretimde temiz dal veya rapor kopyası kullanın. Probe `--select` kimlik substring'i ile tek vaka çalıştırır; aynı label+vaka yeniden çalıştırılırsa JSON yenilenir. Hash kontrolü, pinned checkout'ın değiştirilmemiş olmasını ve beklenen editable import'u denetler. Araştırma scriptleri upstream örneklerinin Python kodunu çalıştırır; kullanıcı tasarım JSON'u çalıştıran production API değildir.

```powershell
python -m pytest build/throughflow_research/turbo-design/tests -m "not slow" -q
python -m pytest build/throughflow_research/turbo-design/tests -m slow -q
```

Heat exchanger baseline/research testleri HE bağımlılıkları kurulu proje venv'iyle; NASA probe'ları ayrı araştırma venv'iyle çalışır. Wheel tüketim testi için `python -m build --wheel --outdir build/throughflow_research/wheels`, ayrı consumer venv'ine oluşan wheel'in `[heat_exchanger]` extra'sı ile kurulması ve `check_packaging.py --python <consumer-python>` gerekir. Tüm çıktıların kaynakları [araştırma scriptleri](../../scripts/throughflow_research/) altında; PyPI ve NASA wheel envanterleri bu oturumda yapılan bağımsız incelemelerin kayıtlarıdır.
