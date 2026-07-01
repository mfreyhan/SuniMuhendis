import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ====== AYARLAR ======
# .env dosyasından okur, yoksa buraya manuel string olarak yazabilirsiniz.
API_KEY = os.environ.get("HF_TOKEN", "")

BASE_URL = "https://router.huggingface.co/v1" 

# Test etmek istediginiz modeli buraya yazin
# Onceden hata veren modelleri deneyebilirsiniz:
MODEL_NAME = "Qwen/Qwen3.6-27B" # veya "google/gemma-4-31B-it" vb.
PROMPT = "Lütfen bana sadece şu JSON'u döndür: {\"status\": \"ok\", \"test\": 1}"
# =====================

print("--- HUGGING FACE API TEST ---")
print(f"Base URL : {BASE_URL}")
print(f"Model    : {MODEL_NAME}")
print("-----------------------------\n")

try:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )
    
    print("İstek gönderiliyor, lütfen bekleyin...")
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=200
    )
    
    print("\n✅ BAŞARILI! Gelen Yanıt:\n")
    print(resp.choices[0].message.content)
    
except Exception as e:
    print("\n❌ HATA OLUŞTU:\n")
    print(type(e).__name__, "-", str(e))
