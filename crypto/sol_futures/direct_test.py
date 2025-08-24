import requests
from dotenv import load_dotenv
import os
import time

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

# Testar conexão com a API REST diretamente
url = "https://testnet.binance.vision/api/v3/time"
headers = {"X-MBX-APIKEY": api_key}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Resposta: {response.text}")
    
    if response.status_code == 200:
        print("✅ Conexão REST básica funcionando!")
    else:
        print("❌ Falha na conexão REST")
        
except Exception as e:
    print(f"❌ Erro na requisição: {e}")
