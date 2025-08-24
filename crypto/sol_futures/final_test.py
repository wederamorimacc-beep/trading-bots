import os
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

print("Teste Final com python-binance...")

try:
    # Tentar conexão sem especificar testnet primeiro
    client = Client(api_key, secret_key)
    server_time = client.get_server_time()
    print("✅ Conexão com API principal bem-sucedida!")
    
    # Agora tentar com testnet
    client_testnet = Client(api_key, secret_key, testnet=True)
    server_time_testnet = client_testnet.get_server_time()
    print("✅ Conexão com Testnet bem-sucedida!")
    
    # Testar futuros
    futures_balance = client_testnet.futures_account_balance()
    print("✅ Conexão com Futuros bem-sucedida!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    print("Vamos tentar uma abordagem alternativa...")
    
    # Tentar com CCXT como fallback
    try:
        import ccxt
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })
        markets = exchange.load_markets()
        print("✅ Conexão com CCXT bem-sucedida!")
    except Exception as e2:
        print(f"❌ Erro no CCXT: {e2}")
