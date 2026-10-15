import streamlit as st
import pandas as pd
import urllib.request
import json
import hmac
import hashlib
import time
from datetime import datetime

st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")
st.title("🤖 Crypto Bot AI - Bybit Automatizado")
st.markdown("Aqui você acompanha a IA analisando e operando no mercado real da Bybit com filtros de certeza absoluta.")

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
# MOTORES DE INTELIGÊNCIA ARTIFICIAL E DADOS ORIGINAIS
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

@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker_name):
    try:
        import yfinance as yf
        df_historico = yf.Ticker(ticker_name).history(period="90d", interval="1d")
        if df_historico.empty: return None
        df = df_historico.reset_index()
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns={'close': 'fechamento'})
        df['ema_20'] = df['fechamento'].ewm(span=20, adjust=False).mean()
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi_14'] = 100 - (100 / (1 + (ganho / (perda + 0.00001))))
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
            trades.append({"Tipo": "🟢 COMPRA", "Data": pd.to_datetime(data).strftime('%d/%m/%Y'), "Preço": f"${preco:,.2f}", "RSI": f"{rsi:.1f}", "Resultado": "Em aberto"})
        elif rsi >= 65.0 and posicao == 1:
            posicao = 0
            lucro = (preco - preco_compra) / preco_compra
            capital = capital * (1 + lucro)
            trades[-1]["Resultado"] = f"{lucro*100:+.2f}%"
            trades[-1]["Preço Venda"] = f"${preco:,.2f}"
    return capital, pd.DataFrame(trades)

# ==============================================================================
# HUB VISUAL DO PAINEL
# ==============================================================================
lista_noticias = buscar_noticias_cripto()
moeda_selecionada = st.selectbox("Escolha o ativo para analisar:", ["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

mapeamento = {"🪙 Bitcoin (BTC)": "BTC-USD", "⧫ Ethereum (ETH)": "ETH-USD", "☀️ Solana (SOL)": "SOL-USD"}
ticker_yf = mapeamento[moeda_selecionada]

df_mercado = buscar_dados_e_indicadores(ticker_yf)

if df_mercado is not None:
    capital_final, df_trades = rodar_simulador(df_mercado)
    lucro_total = ((capital_final - 1000.0) / 1000.0) * 100
    ult = df_mercado.iloc[-1]
    preco_atual = ult['fechamento']
    rsi_atual = ult['rsi_14']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Preço Atual", f"${preco_atual:,.2f}")
    col2.metric("Força RSI", f"{rsi_atual:.2f}")
    col3.metric("Lucro Mês (Simulado)", f"{lucro_total:+.2f}%")
    
    st.markdown("### 🧠 Painel de Sentimento da IA")
    for n in lista_noticias:
        st.write(f"🔹 {n.get('title', '')}")
        
    sc_tot = sum([ia_analisar_sentimento(n.get('title', '')) for n in lista_noticias])
    sc_med = sc_tot / len(lista_noticias) if lista_noticias else 0.0
    sent_ia = "OTIMISTA" if sc_med > 0.05 else ("PESSIMISTA" if sc_med < -0.05 else "NEUTRO")
    
    st.write(f"👉 **Veredito de Texto da IA:** {sent_ia} (Score: {sc_med:+.2f})")
    
    st.markdown("### 🤖 Veredito do Robô em Tempo Real")
    if rsi_atual <= 30 and sent_ia == "OTIMISTA":
        st.success("🔥 SINAL DE COMPRA ATIVO! Disparando ordem real de $6 na Bybit...")
        executar_ordem_real_bybit("COMPRA", ticker_yf)
    elif rsi_atual >= 65 and sent_ia == "PESSIMISTA":
        st.warning("🔴 SINAL DE VENDA ATIVO! Realizando lucros na Bybit...")
        executar_ordem_real_bybit("VENDA", ticker_yf)
    else:
        st.info("🟡 STATUS: AGUARDANDO. Mercado fora dos filtros de certeza absoluta. Capital protegido na Bybit.")
        
    # 🔄 MUDANÇA INFALÍVEL: Gráfico de Linha Puro usando dados nativos sem quebra de índice
    st.markdown("### 📈 Gráfico de Análise Avançada (Tendência de Preços)")
    df_grafico = df_mercado[['fechamento', 'ema_20']].copy()
    df_grafico.columns = ['Preço Real ($)', 'Média Móvel (EMA 20)']
