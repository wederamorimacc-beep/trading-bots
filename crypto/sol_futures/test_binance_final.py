import os
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

print("Testando com python-binance...")

try:
    # Configurar cliente para Testnet
    client = Client(api_key, secret_key, testnet=True)
    
    # Testar conexão
    server_time = client.get_server_time()
    print("✅ Tempo do servidor:", server_time['serverTime'])
    
    # Testar futuros
    account = client.futures_account()
    print("✅ Conta futures acessada com sucesso!")
    
    # Testar símbolo
    ticker = client.futures_symbol_ticker(symbol='SOLUSDT')
    print(f"✅ Preço do SOL: {ticker['price']}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
