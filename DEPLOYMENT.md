# Vast.ai Deployment Guide

Bu belge, benchmark ve dashboard araçlarını Python 3.12 bulunan bir Vast.ai
Ubuntu makinesinde çalıştırmak için kısa kurulum yoludur. Heat-exchanger
simülatörü GPU gerektirmez; GPU yalnız seçtiğiniz model sunumu için gerekebilir.

## 1. Sunucuya bağlanma

```bash
ssh -p <PORT_NUMARASI> root@<IP_ADRESI>
```

## 2. Runtime kontrolü

```bash
python3.12 --version
```

İmaj Python 3.12 sağlamıyorsa projeyi kurmadan önce 3.12 içeren başka bir imaj
seçin. Sistem Python'unu yerinde değiştirmeyin.

## 3. Projeyi kurma

```bash
git clone https://github.com/mfreyhan/SuniMuhendis.git
cd SuniMuhendis
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -c constraints/python312.txt -r requirements.txt -e .
python -m pip check
python -m pytest tests/ -q
```

## 4. Anahtarlar

```bash
cp .env.example .env
```

Yalnız kullanacağınız sağlayıcı anahtarlarını `.env` içine ekleyin. Dosya Git
tarafından izlenmez; loglara, issue'lara veya imaj katmanlarına kopyalamayın.

## 5. Çalıştırma

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v4 --model <MODEL>
streamlit run scripts/dashboard.py --server.address 0.0.0.0
```

Dashboard portunu yalnız güvenilir ağlara açın. Üretim benzeri kullanımda Vast.ai
firewall/port kurallarını ve erişim kontrolünü ayrıca yapılandırın.
