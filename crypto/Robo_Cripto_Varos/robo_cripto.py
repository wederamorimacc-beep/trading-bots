import pandas as pd
import os 
import time 
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (onde chaves API devem estar armazenadas)
load_dotenv()

# Obtém as chaves API das variáveis de ambiente
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

# Inicializa o cliente da Binance com as chaves
cliente_binance = Client(api_key, secret_key)

# Configurações para correção de problemas de tempo/sincronização
cliente_binance.REQUEST_TIMEOUT = 10  # correção de erro
cliente_binance.timestamp_offset = cliente_binance.get_server_time()['serverTime'] - int(time.time() * 1000) # correção de erro

# symbol_info = cliente_binance.get_symbol_info('BTCUSDT')
# lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
# min_qty = float(lot_size_filter['minQty'])
# max_qty = float(lot_size_filter['maxQty'])
# step_size = float(lot_size_filter['stepSize'])

# print(lot_size_filter, min_qty, max_qty, step_size)

# Parâmetros para operação
codigo_operado = "SOLBRL"   # Par de negociação
ativo_operado = "SOL"       # Moeda base
periodo_candle = Client.KLINE_INTERVAL_1HOUR # Intervalo dos candles (1 hora)
quantidade = 0.055 # Quantidade fixa para compra

def pegando_dados(codigo, intervalo):
   """Obtém dados históricos de candles da Binance"""
    
    # Busca últimos 1000 candles
    candles = cliente_binance.get_klines(symbol = codigo, interval = intervalo, limit = 1000)
    # Converte para DataFrame e nomeia coluna
    precos = pd.DataFrame(candles)
    precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento", "moedas_negociadas", "numero_trades",
                    "volume_ativo_base_compra", "volume_ativo_cotação", "-"]

    # Mantém apenas colunas relevantes
    precos = precos[["fechamento", "tempo_fechamento"]]

    # Converte timestamp para datetime com fuso horário
    precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit = "ms").dt.tz_localize("UTC")
    precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")

    return precos


def estrategia_trade(dados, codigo_ativo, ativo_operado, quantidade, posicao):
    """Executa estratégia de trading baseada em médias móveis"""
    # Calcula médias móveis
    dados["media_rapida"] = dados["fechamento"].rolling(window = 7).mean()   # MMA de 7 períodos
    dados["media_devagar"] = dados["fechamento"].rolling(window = 40).mean() # MMA de 40 períodos

    # Obtém últimos valores das médias
    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]
    print(f"Última Média Rápida: {ultima_media_rapida} | Última Média Devagar: {ultima_media_devagar}")

    # Verifica saldo disponível do ativo
    conta = cliente_binance.get_account()

    for ativo in conta["balances"]:
        if ativo["asset"] == ativo_operado:
            quantidade_atual = float(ativo["free"]) # Saldo disponível

# Lógica de trading:
    if ultima_media_rapida > ultima_media_devagar: # Tendência de alta

        if posicao == False: # Se não está posicionado
            # Executa ordem de compra
            order = cliente_binance.create_order(symbol = codigo_ativo,
                side = SIDE_BUY,
                type = ORDER_TYPE_MARKET,
                quantity = quantidade
                )
            
            print("COMPROU O ATIVO")
            posicao = True # Atualiza estado para posicionado

    elif ultima_media_rapida < ultima_media_devagar:  # Tendência de baixa

        if posicao == True:  # Se está posicionado
            # Executa ordem de venda com quantidade disponível (ajustada para 3 casas decimais)
            order = cliente_binance.create_order(symbol = codigo_ativo,
                side = SIDE_SELL,
                type = ORDER_TYPE_MARKET,
                quantity = int(quantidade_atual * 1000)/1000)
            
            print("VENDER O ATIVO")
            posicao = False # Atualiza estado para não posicionado

    return posicao

# Loop principal de operação
posicao_atual = False # Controla se está com posição aberta
while True:
    # Atualiza dados e executa estratégia
    dados_atualizados = pegando_dados(codigo=codigo_operado, intervalo=periodo_candle)
    posicao_atual = estrategia_trade(
        dados_atualizados, 
        codigo_ativo=codigo_operado, 
        ativo_operado=ativo_operado, 
        quantidade=quantidade, posicao=posicao_atual)
        
    # Espera 1 hora até próxima verificação
    time.sleep(60 * 60)



