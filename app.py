import streamlit as st
import pandas as pd
import yfinance as yf
import urllib.request
import json
import hmac
import hashlib
import time
from datetime import datetime

# Configuração da Página Web ORIGINAL
st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")

st.title("🤖 Crypto Bot AI - Bybit Automatizado")
st.markdown("Aqui você acompanha a IA analisando o mercado com filtros de certeza absoluta.")

# ==============================================================================
# CONFIGURAÇÕES DE SEGURANÇA E TELEGRAM
# ==============================================================================
TELEGRAM_TOKEN = "8659842719:AAHzgJe_6dh-GPxrEjOwqaQ8-Z2HdvTjEUg"
TELEGRAM_CHAT_ID = "5977741363"

api_key_real = st.secrets.get("BYBIT_API_KEY", "")
secret_key_real = st.secrets.get("BYBIT_SECRET_KEY", "")
modo_real_ativo = st.secrets.get("modo_real", "nao")

def enviar_alerta_telegram(mensagem):
    try:
        texto_codificado = urllib.parse.quote(mensagem)
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={texto_codificado}&parse_mode=Markdown"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: pass
    except: pass

# ==============================================================================
# FUNÇÃO DE EXECUÇÃO DIRETA NA API DA BYBIT
# ==============================================================================
def executar_ordem_real_bybit(tipo_ordem, simbolo_yf):
    if modo_real_ativo != "sim" or api_key_real == "" or secret_key_real == "":
        st.warning("⚠️ Modo Real desativado nos Secrets. Operando em Modo Simulador Protegido.")
        return False
        
    try:
        moeda = "BTC" if "BTC" in simbolo_yf else ("ETH" if "ETH" in simbolo_yf else "SOL")
        symbol = f"{moeda}USDT"
        side = "Buy" if tipo_ordem == "COMPRA" else "Sell"
        
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        params = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": "6" if side == "Buy" else "0"
        }
        
        if side == "Sell":
            timestamp_bal = str(int(time.time() * 1000))
            param_str_bal = f"timestamp={timestamp_bal}&api_key={api_key_real}&recv_window={recv_window}&category=spot"
            sign_bal = hmac.new(bytes(secret_key_real, "utf-8"), param_str_bal.encode("utf-8"), hashlib.sha256).hexdigest()
            url_bal = f"https://bybit.com{timestamp_bal}&api_key={api_key_real}&recv_window={recv_window}&sign={sign_bal}"
            req_bal = urllib.request.Request(url_bal, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_bal) as r_bal:
                res_bal = json.loads(r_bal.read().decode())
                list_bal = res_bal.get("result", {}).get("list", [{}]).get("coin", [])
                for c in list_bal:
                    if c.get("coin") == moeda:
                        params["qty"] = str(c.get("walletBalance", "0"))
                        break
            if params["qty"] == "0" or params["qty"] == "0.0":
                return False

        req_body = json.dumps(params)
        param_str = timestamp + api_key_real + recv_window + req_body
        signature = hmac.new(bytes(secret_key_real, "utf-8"), param_str.encode("utf-8"), hashlib.sha256).hexdigest()
        
        headers = {
            "X-BAPI-API-KEY": api_key_real,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json"
        }
        
        url = "https://bybit.com"
        req = urllib.request.Request(url, data=req_body.encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get("retCode") == 0:
                if side == "Buy":
                    enviar_alerta_telegram(f"💰 *EXECUÇÃO REAL NA BYBIT:* Comprei $6 de {symbol} direto na sua conta!")
                else:
                    enviar_alerta_telegram(f"💰 *EXECUÇÃO REAL NA BYBIT:* Vendi todo o saldo de {moeda} na sua conta!")
                return True
            else:
                enviar_alerta_telegram(f"❌ *ERRO NA BYBIT:* Falha ao processar ordem: {res.get('retMsg')}")
                return False
    except Exception as e:
        enviar_alerta_telegram(f"❌ *ERRO DE CONEXÃO:* Falha ao enviar ordem para a Bybit: {str(e)}")
        return False

# ==============================================================================
# MOTOR DE INTELIGÊNCIA ARTIFICIAL: ANÁLISE DE SENTIMENTO NATIVA
# ==============================================================================
def ia_analisar_sentimento(texto):
    palavras_otimistas = ['bullish', 'surge', 'rise', 'buy', 'accumulate', 'gain', 'growth', 'positive', 'high', 'clear', 'green', 'support']
    palavras_pessimistas = ['bearish', 'drop', 'fall', 'sell', 'crash', 'loss', 'negative', 'low', 'risk', 'panic', 'crackdown', 'resistance']
    texto_minusculo = texto.lower()
    score = 0.0
    for word in palavras_otimistas:
        if word in texto_minusculo: score += 0.2
    for word in palavras_pessimistas:
        if word in texto_minusculo: score -= 0.2
    return max(min(score, 1.0), -1.0)

@st.cache_data(ttl=300)
def buscar_noticias_cripto():
    try:
        url = "https://cryptoquant.com"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: dados = json.loads(response.read().decode())
        return dados.get('data', [])
    except:
        return [{"title": "Bitcoin institutions continue steady accumulation in secure zones"}]

# ==============================================================================
# CRIAÇÃO DAS ABAS INTERATIVAS ORIGINAL BLINDADA (BTC, ETH, SOL)
# ==============================================================================
aba_btc, aba_eth, aba_sol = st.tabs(["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

config_moedas = {
    "Bitcoin (BTC)": {"ticker": "BTC-USD", "aba": aba_btc},
    "Ethereum (ETH)": {"ticker": "ETH-USD", "aba": aba_eth},
    "Solana (SOL)": {"ticker": "SOL-USD", "aba": aba_sol}
}

@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker_name):
    try:
        df_historico = yf.Ticker(ticker_name).history(period="60d", interval="1d")
        if df_historico.empty: return None
        df = df_historico.reset_index()
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns={'close': 'fechamento'})
        
        df['ema_20'] = df['fechamento'].ewm(span=20, adjust=False).mean()
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / (perda + 0.00001)
        df['rsi_14'] = 100 - (100 / (1 + rs))
        return df.dropna()
    except: return None

def rodar_simulador(df):
    capital = 1000.0
    posicao = 0 
    preco_compra = 0
    trades = []
    for i in range(len(df)):
        linha = df.iloc[i]
        preco = linha['fechamento']
        rsi = linha['rsi_14']
        data = linha['date']
        if rsi <= 30.0 and posicao == 0:
            posicao = 1
            preco_compra = preco
            trades.append({"Tipo": "🟢 COMPRA", "Data": data.strftime('%d/%m/%Y'), "Preço": f"${preco:,.2f}", "RSI": f"{rsi:.1f}", "Resultado": "Em aberto"})
        elif rsi >= 65.0 and posicao == 1:
            posicao = 0
            lucro = (preco - preco_compra) / preco_compra
            capital = capital * (1 + lucro)
            trades[-1]["Resultado"] = f"{lucro*100:+.2f}%"
            trades[-1]["Preço Venda"] = f"${preco:,.2f}"
    return capital, pd.DataFrame(trades)

# ==============================================================================
# RENDERIZAÇÃO CENTRALIZADA ORIGINAL
# ==============================================================================
lista_noticias = buscar_noticias_cripto()

for nome_moeda, info in config_moedas.items():
    with info["aba"]:
        df_mercado = buscar_dados_e_indicadores(info["ticker"])
        
        if df_mercado is not None:
            capital_final, df_trades = rodar_simulador(df_mercado)
            lucro_total = ((capital_final - 1000.0) / 1000.0) * 100
            
            ultima_linha = df_mercado.iloc[-1]
            preco_atual = ultima_linha['fechamento']
            rsi_atual = ultima_linha['rsi_14']
            
            # BLOCOS SUPERIORES DE MÉTRICAS COMPLETO
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.subheader("💲 Preço Atual")
                st.info(f"${preco_atual:,.2f}")
            with col2:
                st.subheader("📈 Força RSI")
                st.info(f"{rsi_atual:.2f}")
            with col3:
                st.subheader("📊 Lucro Mês")
                st.success(f"{lucro_total:+.2f}%")
            with col4:
                st.subheader("💰 Saldo Total")
                st.success(f"${capital_final:,.2f}")
            
            # Painel de Análise de Notícias com IA
            st.markdown(f"### 🧠 Painel de Sentimento da IA para {nome_moeda}")
            col_noticias, col_status_ia = st.columns(2)
            
            with col_noticias:
                st.markdown("**Feed de Notícias Recentes Detectadas:**")
                score_total_ia = 0.0
                contador_noticias = 0
                
                for item in lista_noticias:
                    titulo = item.get('title', '')
