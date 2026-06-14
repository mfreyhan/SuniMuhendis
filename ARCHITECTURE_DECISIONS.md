# Mimari Kararlar ve Best Practices

Bu dosya projede neden bazı spesifik paketlerin/yöntemlerin seçildiğini gelecekte unutmamak adına tutulmaktadır.

## ADR-01: LLM Çıktılarından JSON Ayıklama (Parsing & Repair)
**Tarih:** 2026-06-14

**Bağlam:** Büyük Dil Modelleri (LLM), özellikle küçük olanları (7B, 8B parametre), sistem ne kadar katı yönlendirilirse yönlendirilsin zaman zaman bozuk JSON'lar üretmektedir. (Eksik virgül, fazla süslü parantez, markdown block tagleri vs.)

**Karar:** Kendi regex algoritmamızı yazmak yerine `json-repair` kütüphanesi kullanılacaktır.
**Nedenleri:**
1. Hazır, test edilmiş, yüzlerce uç durumu (edge-case) destekliyor.
2. Basit regex çözümleri kompleks iç içe geçmiş objelerde çökebiliyor.
3. Bizim asıl odağımız LLM'i eğitmek ve mühendislik simülasyonudur, kendi JSON parser'ımızı yazıp zaman kaybetmek yerine best-practice olan açık kaynak araçlara güvenmek daha verimlidir.

**Not:** İleride (Faz 4/5) modeli eğitirken, JSON formatını modelin kendisine dayatmak (constrained decoding) için `outlines`, `vllm` veya `guidance` gibi kütüphanelere geçiş yapma ihtimalimiz vardır. Ancak şimdilik üretim sonrasında (post-generation) düzeltme stratejisi seçilmiştir.
