import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

print("Chaves carregadas do .env:")
print(f"API Key: {api_key}")
print(f"Secret Key: {secret_key}")
print(f"Comprimento API Key: {len(api_key) if api_key else 0}")
print(f"Comprimento Secret Key: {len(secret_key) if secret_key else 0}")
