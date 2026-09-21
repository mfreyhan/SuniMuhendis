# Python 3.12 geçişi

Tarih: 21 Eylül 2026  
Dal: `codex/throughflow-phase-0-2`

## Karar

SuniMuhendis public runtime sözleşmesi `>=3.12,<3.13` olarak değiştirildi. Geliştirme referansı `.python-version` içinde CPython 3.12.10'dur. 3.13 desteği, tam test ve temiz-wheel tüketici kontrolü o minor sürümde geçmeden açılmaz.

NASA turbo-design'ın seçili SHA'sı 3.9 metadata ilan etmesine rağmen 3.9'da import edilemiyor; 3.12'de import ve testleri çalışıyor. Tek runtime, ayrı worker kurulumuna göre repo içi ve dışı tüketimi sadeleştiriyor. Bu karar solver fiziği, kayıp modeli veya lisans sorunlarını çözmüş sayılmaz.

## Değişiklikler

- `pyproject.toml`: `requires-python = ">=3.12,<3.13"`; yalnız 3.12 classifier'ı.
- `.python-version`: `3.12.10`.
- `constraints/python312.txt`: Windows'ta doğrulanan doğrudan geliştirme bağımlılıkları.
- `requirements.txt`: build aracı eklendi, yinelenen OpenAI girdisi kaldırıldı, constraint kullanımına yönlendirme eklendi.
- README, AGENTS ve CLAUDE kurulum/sürüm metinleri güncellendi.
- `tests/test_python_runtime.py`: çalışan interpreter ve metadata tutarlılığı.
- `scripts/check_wheel_metadata.py`: runtime metadata'sı ve public wheel sınırı.
- `scripts/check_wheel_consumer.py`: geçici temiz venv'e HE extra'sını kurup repo dışı public API smoke testi.
- `.github/workflows/tests.yml`: Python 3.12.10 ile Windows ve Linux test/build/consumer işleri.

## Yerel kabul sonucu

| Kontrol | Sonuç |
|---|---|
| Windows CPython | 3.12.10 |
| Tam test | 229 geçti |
| Dependency health | `pip check` başarılı |
| Wheel metadata | `Requires-Python: <3.13,>=3.12` |
| Public wheel içeriği | prompts mevcut; model_clients, baselines ve turbodesign yok |
| Temiz repo-dışı tüketici | HE başarı; skor 0.7288073927259057 |
| Python 3.9 negatif kurulum | Beklenen şekilde metadata tarafından reddedildi |

JUnit kaydı: [python312_migration_pytest.xml](throughflow_phase_0_2/python312_migration_pytest.xml).

## Açık maddeler

Linux sonucu yerelde üretilmedi; eklenen GitHub Actions işi Ubuntu'da test, build, metadata ve temiz-wheel tüketici kontrollerini başarıyla tamamladı. Windows işi de aynı committe geçti. Özel eğitim reposu bu workspace'te olmadığı için sürümü burada değiştirilemedi. Orada Python 3.12 ortamı kurulmalı, bu wheel/tag tüketilmeli ve gerçek eğitim çağrısı en az bir HE ve ileride bir throughflow vakasıyla sınanmalıdır.

`constraints/python312.txt` tüm transitif dependency'lerin hash'li lock dosyası değildir. Doğrudan geliştirme profilini sabitler; platforma özel transitif kilit ve artifact hash'leri release aşamasında üretilir. Throughflow backend'inin NASA/Cantera/pyturbo bağımlılıkları Faz 0–2 araştırma profillerinde ayrı kalır ve backend kabul edilmeden public `throughflow` extra'sına eklenmez.
