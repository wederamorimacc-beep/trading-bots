# -*- coding: utf-8 -*-
import os
import time
import logging
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
import pandas as pd

from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

# =========================
# Configurações do Robô
# =========================
PAR                   = "SOLUSDT"                         # Par USDT-M de Futuros
PERIODO               = Client.KLINE_INTERVAL_1HOUR       # H1
MEDIA_RAPIDA          = 7                                 # MM curta
MEDIA_LENTA           = 40                                # MM longa (original)
ALAVANCAGEM           = 2                                 # Alavancagem
TIPO_MARGEM           = 'ISOLATED'                        # 'ISOLATED' ou 'CROSSED'
PCT_SALDO             = 0.90                              # 90% do saldo em USDT por operação
RECV_WINDOW_MS        = 60000                             # 60s para robustez de rede
ESPERA_ERRO_SEG       = 60                                # Re-tentativa em erro transitório
LIMITE_CANDLES        = 1000                              # histórico para análise/testes

# ===== Logging estruturado =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("robo_futuros")

# Telemetria simples em memória
registro_operacoes = []
def registrar_operacao(acao: str, quantidade: float, preco: float, forca_sinal: float, saldo_usdt: float):
    registro_operacoes.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acao": acao, "quantidade": quantidade, "preco": preco,
        "forca_sinal": forca_sinal, "saldo_usdt": saldo_usdt
    })

# =========================
# Credenciais / Cliente
# =========================
load_dotenv()
api_key    = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")
if not api_key or not secret_key:
    raise RuntimeError("Chaves de API não encontradas. Defina KEY_BINANCE e SECRET_BINANCE no .env")

# Timeout documentado via requests_params
cliente = Client(api_key, secret_key, requests_params={'timeout': 30})

# =========================
# Utilidades de Tempo
# =========================
def tempo_servidor_ms() -> int:
    """Tempo do servidor de Futuros em ms (mais preciso para agendamento)."""
    return cliente.futures_time()['serverTime']

def aguardar_proxima_hora():
    """Alinha execução ao fechamento da próxima vela H1 usando o tempo do servidor de Futuros."""
    try:
        agora_ms = tempo_servidor_ms()
    except Exception:
        agora_ms = int(time.time() * 1000)  # fallback local
    agora_s = agora_ms // 1000
    restante = 3600 - (agora_s % 3600)
    if restante < 10:  # margem para evitar corrida no fechamento
        restante += 3600
    # Auditoria de horários
    hora_server = datetime.utcfromtimestamp(agora_s).strftime("%Y-%m-%d %H:%M:%S UTC")
    try:
        # Exibição no fuso de São Paulo para leitura
        hora_sp = pd.to_datetime(agora_s, unit="s", utc=True).tz_convert("America/Sao_Paulo").strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        hora_sp = "indisp."
    logger.info(f"[Timing] server={hora_server} | SP={hora_sp} | aguardando {restante}s até próxima H1")
    time.sleep(restante)

# =========================
# Exchange Info / Filtros
# =========================
def arredondar_passo(qtd: float, passo: float) -> float:
    d = (Decimal(str(qtd)) / Decimal(str(passo))).to_integral_value(rounding=ROUND_DOWN) * Decimal(str(passo))
    return float(d)

def cachear_filtros(par: str):
    info = cliente.futures_exchange_info()
    simb = next(x for x in info['symbols'] if x['symbol'] == par)
    def filtro(t):
        return next(f for f in simb['filters'] if f['filterType'] == t)
    return {
        "MARKET_LOT_SIZE": filtro("MARKET_LOT_SIZE"),
        "MIN_NOTIONAL":   filtro("MIN_NOTIONAL"),
        "PRICE_FILTER":   filtro("PRICE_FILTER"),
    }

FILTROS = cachear_filtros(PAR)
PASSO_QTD    = float(FILTROS["MARKET_LOT_SIZE"]["stepSize"])
NOTIONAL_MIN = float(FILTROS["MIN_NOTIONAL"]["notional"])

# =========================
# Consulta de Conta/Posição
# =========================
def saldo_usdt() -> float:
    bal = cliente.futures_account_balance(recvWindow=RECV_WINDOW_MS)
    return next((float(x['balance']) for x in bal if x['asset'] == 'USDT'), 0.0)

def preco_atual(par: str) -> float:
    return float(cliente.futures_symbol_ticker(symbol=par, recvWindow=RECV_WINDOW_MS)['price'])

def posicao_aberta(par: str) -> float:
    """Tamanho (contracts) da posição (positivo=LONG, negativo=SHORT). One-way mode."""
    pos = cliente.futures_position_information(symbol=par, recvWindow=RECV_WINDOW_MS)
    p = next((x for x in pos if x['symbol'] == par), None)
    if not p:
        return 0.0
    return float(p['positionAmt'])

def fechar_posicao_se_existir(par: str):
    amt = posicao_aberta(par)
    if amt == 0:
        return
    lado = 'SELL' if amt > 0 else 'BUY'
    logger.info(f"[Fechamento] Fechando {par}: qty={abs(amt)} side={lado}")
    cliente.futures_create_order(
        symbol=par, side=lado, type='MARKET',
        quantity=abs(amt), reduceOnly=True, recvWindow=RECV_WINDOW_MS
    )

# =========================
# Modos da Conta (One-way/Margem/Alavancagem)
# =========================
def garantir_modos_conta(par: str):
    # One-way (sem Hedge)
    try:
        cliente.futures_change_position_mode(dualSidePosition='false', recvWindow=RECV_WINDOW_MS)
    except BinanceAPIException as e:
        if "No need to change position side" not in str(e):
            logger.warning(f"[Modo Posição] {e}")
    # Tipo de Margem
    try:
        cliente.futures_change_margin_type(symbol=par, marginType=TIPO_MARGEM, recvWindow=RECV_WINDOW_MS)
    except BinanceAPIException as e:
        if "No need to change margin type" not in str(e):
            logger.warning(f"[Tipo Margem] {e}")
    # Alavancagem
    try:
        cliente.futures_change_leverage(symbol=par, leverage=ALAVANCAGEM, recvWindow=RECV_WINDOW_MS)
    except BinanceAPIException as e:
        logger.warning(f"[Alavancagem] {e}")

# =========================
# Cálculo de Quantidade
# =========================
def calcular_quantidade(par: str, pct_saldo: float, alavancagem: int) -> float:
    usdt = saldo_usdt()
    if usdt <= 0:
        logger.warning("[Qtd] Saldo USDT insuficiente.")
        return 0.0
    px = preco_atual(par)
    notional_alvo = usdt * pct_saldo * alavancagem   # 90% do saldo * leverage
    qtd_bruta = notional_alvo / px

    # Respeitar MARKET_LOT_SIZE
    qtd = arredondar_passo(qtd_bruta, PASSO_QTD)
    # Garantir notional mínimo
    if qtd * px < NOTIONAL_MIN:
        qtd = arredondar_passo(NOTIONAL_MIN / px, PASSO_QTD)

    return max(qtd, 0.0)

# =========================
# Dados de Mercado
# =========================
def buscar_klines_fechados(par: str, periodo: str, limite: int = LIMITE_CANDLES) -> pd.DataFrame:
    kl = cliente.futures_klines(symbol=par, interval=periodo, limit=limite)
    df = pd.DataFrame(kl, columns=[
        "t_open","open","high","low","close","volume","t_close","quote_vol",
        "trades","taker_base","taker_quote","ignore"
    ])
    df = df[["t_close", "close"]].copy()
    df["close"] = df["close"].astype(float)
    df["t_close"] = pd.to_datetime(df["t_close"], unit="ms", utc=True).dt.tz_convert("America/Sao_Paulo")
    return df

# =========================
# Estratégia (7 x 40)
# =========================
def sinal_media_movel(df: pd.DataFrame) -> str:
    """Retorna 'COMPRA', 'VENDA' ou 'MANTER' com base no estado da **penúltima vela**."""
    if len(df) < max(MEDIA_RAPIDA, MEDIA_LENTA) + 2:
        return "MANTER"
    fechamento = df["close"].astype(float)
    mm_r = fechamento.rolling(window=MEDIA_RAPIDA).mean()
    mm_l = fechamento.rolling(window=MEDIA_LENTA).mean()

    # penúltima vela fechada
    r_prev = mm_r.iloc[-2]
    l_prev = mm_l.iloc[-2]

    logger.info(f"[MM] Rápida({MEDIA_RAPIDA})={r_prev:.6f} | Lenta({MEDIA_LENTA})={l_prev:.6f} (base: vela fechada)")
    if pd.isna(r_prev) or pd.isna(l_prev):
        return "MANTER"
    if r_prev > l_prev:
        return "COMPRA"
    if r_prev < l_prev:
        return "VENDA"
    return "MANTER"

# =========================
# Utilidades opcionais (não alteram a lógica)
# =========================
def mercado_volatil(par: str, desvio_limite: float = 0.05) -> bool:
    """Consulta 20 velas de 15min e calcula desvio-padrão dos retornos. Apenas informativo."""
    try:
        kl = cliente.futures_klines(symbol=par, interval=Client.KLINE_INTERVAL_15MINUTE, limit=20)
        df = pd.DataFrame(kl, columns=[
            "t_open","open","high","low","close","volume","t_close","quote_vol",
            "trades","taker_base","taker_quote","ignore"
        ])
        df["close"] = df["close"].astype(float)
        vol = df["close"].pct_change().dropna().std()
        logger.info(f"[Vol] σ(returns 15m)={vol:.4f} | limite={desvio_limite}")
        return vol > desvio_limite
    except Exception as e:
        logger.warning(f"[Vol] Falha ao medir volatilidade: {e}")
        return False

# Placeholder de circuit breaker (não aplicado à lógica)
MAX_PERDAS_SEGUIDAS = 3
perdas_seguidas = 0

# =========================
# Loop Principal
# =========================
def loop_principal():
    logger.info(f"Iniciando Futuros USDT-M | {PAR} | MM {MEDIA_RAPIDA}x{MEDIA_LENTA} | Lvg {ALAVANCAGEM} | {TIPO_MARGEM}")
    garantir_modos_conta(PAR)

    while True:
        try:
            dados = buscar_klines_fechados(PAR, PERIODO, limite=LIMITE_CANDLES)
            if dados.empty:
                logger.warning("[Dados] Sem dados. Aguardando...")
                time.sleep(ESPERA_ERRO_SEG)
                continue

            sinal = sinal_media_movel(dados)
            tamanho_pos = posicao_aberta(PAR)

            if sinal == "COMPRA" and tamanho_pos == 0:
                qtd = calcular_quantidade(PAR, PCT_SALDO, ALAVANCAGEM)
                if qtd > 0:
                    px = preco_atual(PAR)
                    logger.info(f"[Entrada] LONG qty={qtd} @ ~{px}")
                    cliente.futures_create_order(
                        symbol=PAR, side='BUY', type='MARKET',
                        quantity=qtd, recvWindow=RECV_WINDOW_MS
                    )
                    registrar_operacao("COMPRA", qtd, px, forca_sinal=1.0, saldo_usdt=saldo_usdt())

            elif sinal == "VENDA" and tamanho_pos > 0:
                qtd_saida = abs(tamanho_pos)
                px = preco_atual(PAR)
                logger.info(f"[Saída] Fechando LONG qty={qtd_saida} @ ~{px}")
                cliente.futures_create_order(
                    symbol=PAR, side='SELL', type='MARKET',
                    quantity=qtd_saida, reduceOnly=True, recvWindow=RECV_WINDOW_MS
                )
                registrar_operacao("VENDA", qtd_saida, px, forca_sinal=-1.0, saldo_usdt=saldo_usdt())

            else:
                logger.info(f"[Manter] sinal={sinal} | pos={tamanho_pos}")

            # Informativo (não bloqueia): volatilidade
            mercado_volatil(PAR)

            # Espera até próxima H1 fechar
            aguardar_proxima_hora()

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"[Erro API] {e}. Repetindo em {ESPERA_ERRO_SEG}s...")
            time.sleep(ESPERA_ERRO_SEG)
        except Exception as e:
            logger.error(f"[Erro Geral] {e}. Repetindo em {ESPERA_ERRO_SEG}s...")
            time.sleep(ESPERA_ERRO_SEG)

if __name__ == "__main__":
    loop_principal()
