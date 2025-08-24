import os
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

print("Testando conexão com Binance Testnet...")

try:
    client = Client(api_key, secret_key, testnet=True)
    server_time = client.get_server_time()
    print("✅ Conexão básica OK! Server time:", server_time['serverTime'])
    
    # Testar futuros
    balance = client.futures_account_balance()
    print("✅ Futuros balance OK!")
    
    # Testar ticker
    ticker = client.futures_symbol_ticker(symbol='SOLUSDT')
    print(f"✅ Ticker SOLUSDT: {ticker['price']}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
