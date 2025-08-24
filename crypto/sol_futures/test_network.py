import requests

try:
    response = requests.get("https://testnet.binance.vision/api/v3/time", timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Erro de rede: {e}")
