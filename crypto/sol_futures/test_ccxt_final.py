import ccxt
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('KEY_BINANCE')
secret_key = os.getenv('SECRET_BINANCE')

print("Testando com CCXT...")
print(f"API Key: {api_key}")
print(f"Secret Key: {secret_key[:10]}...")

# Configuração específica para Testnet
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    }
})

try:
    # Testar carga de mercados
    markets = exchange.load_markets()
    print(f"✅ {len(markets)} mercados carregados")
    
    # Testar ticker
    ticker = exchange.fetch_ticker('SOL/USDT')
    print(f"✅ Preço SOL/USDT: {ticker['last']}")
    
    # Testar saldo
    balance = exchange.fetch_balance()
    print(f"✅ Saldo: {balance['USDT']['free']} USDT")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    print("\n📋 Possíveis causas:")
    print("1. Chaves API inválidas ou expiradas")
    print("2. Problema de sincronização de tempo")
    print("3. Restrições de IP na Binance")
