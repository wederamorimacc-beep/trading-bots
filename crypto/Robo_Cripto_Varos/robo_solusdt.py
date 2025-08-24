import pandas as pd
import os 
import time 
from binance.client import Client
from binance.enums import *

from dotenv import load_dotenv
load_dotenv()

# Configuração das chaves API
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

# Inicialização do cliente Binance
cliente_binance = Client(api_key, secret_key)
cliente_binance.REQUEST_TIMEOUT = 10
cliente_binance.timestamp_offset = 
    cliente_binance.get_server_time()['serverTime'] - int(time.time() * 1000)

# Configuração para mercado futuro
codigo_operado = "SOLUSDT"  # Par para futuros
ativo_referencia = "USDT"   # Moeda de referência para futuros
periodo_candle = Client.KLINE_INTERVAL_1HOUR
quantidade_contratos = 1  # Quantidade de contratos (ajuste conforme sua estratégia)
alavancagem = 2  # Alavancagem de 2x

# Configurar alavancagem para futuros
try:
    cliente_binance.futures_change_leverage(symbol=codigo_operado, leverage=alavancagem)
    print(f"Alavancagem configurada para {alavancagem}x em {codigo_operado}")
except Exception as e:
    print(f"Erro ao configurar alavancagem: {e}")

def pegando_dados_futuros(codigo, intervalo):
    """Obtém dados de candles do mercado futuro"""
    candles = cliente_binance.futures_klines(symbol=codigo, interval=intervalo, limit=1000)
    precos = pd.DataFrame(candles)
    precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", 
                     "tempo_fechamento", "volume_em_ativos", "numero_trades",
                     "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"]
    precos = precos[["fechamento", "tempo_fechamento"]]
    precos["fechamento"] = precos["fechamento"].astype(float)
    precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC")
    precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")
    return precos

def estrategia_futuros(dados, codigo_ativo, quantidade, posicao_aberta):
    """Executa estratégia de trading para futuros"""
    dados["media_rapida"] = dados["fechamento"].rolling(window=7).mean()
    dados["media_devagar"] = dados["fechamento"].rolling(window=40).mean()

    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]

    print(f"Última Média Rápida: {ultima_media_rapida:.4f} | Última Média Devagar: {ultima_media_devagar:.4f}")

    # Verificar posições abertas em futuros
    try:
        posicoes = cliente_binance.futures_position_information(symbol=codigo_ativo)
        posicao_atual = next((p for p in posicoes if p['symbol'] == codigo_ativo), None)
        
        if posicao_atual and float(posicao_atual['positionAmt']) != 0:
            posicao_aberta = True
            print(f"Posição aberta encontrada: {posicao_atual['positionAmt']} contratos")
        else:
            posicao_aberta = False
    except Exception as e:
        print(f"Erro ao verificar posições: {e}")
        return posicao_aberta

    # Lógica de trading para futuros
    if ultima_media_rapida > ultima_media_devagar:
        if not posicao_aberta:
            try:
                # Abrir posição LONG
                order = cliente_binance.futures_create_order(
                    symbol=codigo_ativo,
                    side='BUY',
                    type='MARKET',
                    quantity=quantidade
                )
                print("POSIÇÃO LONG ABERTA - COMPROU FUTUROS")
                posicao_aberta = True
            except Exception as e:
                print(f"Erro ao abrir posição long: {e}")

    elif ultima_media_rapida < ultima_media_devagar:
        if posicao_aberta:
            try:
                # Fechar posição LONG (vender para fechar)
                order = cliente_binance.futures_create_order(
                    symbol=codigo_ativo,
                    side='SELL',
                    type='MARKET',
                    quantity=quantidade,
                    reduceOnly='true'  # Garante que é apenas para reduzir posição
                )
                print("POSIÇÃO LONG FECHADA - VENDEU FUTUROS")
                posicao_aberta = False
            except Exception as e:
                print(f"Erro ao fechar posição: {e}")

    return posicao_aberta

# Loop principal de operação
posicao_aberta = False
while True:
    try:
        dados_atualizados = pegando_dados_futuros(codigo=codigo_operado, intervalo=periodo_candle)
        posicao_aberta = estrategia_futuros(dados_atualizados, codigo_ativo=codigo_operado, 
                                           quantidade=quantidade_contratos, posicao_aberta=posicao_aberta)
        time.sleep(60 * 60)  # Espera 1 hora
    except Exception as e:
        print(f"Erro no loop principal: {e}")
        time.sleep(60 * 5)  # Espera 5 minutos em caso de erro