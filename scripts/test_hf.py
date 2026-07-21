import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ====== SETTINGS ======
# Reads from .env file, or you can hardcode it here as a string.
API_KEY = os.environ.get("HF_TOKEN", "")

BASE_URL = "https://router.huggingface.co/v1" 

# Write the model you want to test here
# You can try models that previously failed:
MODEL_NAME = "Qwen/Qwen3.6-27B" # or "google/gemma-4-31B-it" etc.
PROMPT = "Please return only the following JSON: {\"status\": \"ok\", \"test\": 1}"
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
    
    print("Sending request, please wait...")
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=200
    )
    
    print("\n✅ SUCCESS! Received Response:\n")
    print(resp.choices[0].message.content)
    
except Exception as e:
    print("\n❌ ERROR OCCURRED:\n")
    print(type(e).__name__, "-", str(e))
