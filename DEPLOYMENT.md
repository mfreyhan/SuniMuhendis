# Vast.ai Deployment Guide

Bu doküman, SuniMuhendis projesini modelleri benchmark etmek ve simülasyonları koşturmak için kiralayacağınız Vast.ai (Ubuntu + GPU) sunucularına nasıl kuracağınızı açıklar.

## 1. Sunucuya Bağlanma
Vast.ai üzerinden kiraladığınız sunucuya size verilen SSH komutuyla bağlanın:
```bash
ssh -p <PORT_NUMARASI> root@<IP_ADRESI>
```

## 2. GitHub Reposunu Klonlama
Sunucuya bağlandıktan sonra, kodlarımızı çekiyoruz:
```bash
git clone https://github.com/mfreyhan/SuniMuhendis.git
cd SuniMuhendis
```

## 3. Python Sanal Ortamı Kurulumu
Genelde Vast.ai makinelerinde Python yüklüdür ancak `venv` modülü eksik olabilir.
```bash
apt update
apt install python3-venv python3-pip -y
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Kütüphanelerin Yüklenmesi
```bash
pip install -r requirements.txt
```

