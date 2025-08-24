import ccxt
from dotenv import load_dotenv
import os

load_dotenv()

exchange = ccxt.binance({
    'apiKey': os.getenv("KEY_BINANCE"),
    'secret': os.getenv("SECRET_BINANCE"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    }
})

try:
    markets = exchange.load_markets()
    print("✅ Conexão com CCXT bem-sucedida!")
    ticker = exchange.fetch_ticker('SOL/USDT')
    print(f"✅ Preço do SOL/USDT: {ticker['last']}")
except Exception as e:
    print(f"❌ Erro: {e}")
