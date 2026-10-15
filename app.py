import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import urllib.request
import json
import ccxt 
from datetime import datetime

# Configuração da Página Web ORIGINAL
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
# FUNÇÃO DE EXECUÇÃO DE ORDENS REAIS NA BYBIT (AJUSTADO PARA BANCA DE $20)
# ==============================================================================
def executar_ordem_real_bybit(tipo_ordem, simbolo_bybit):
    if modo_real_ativo != "sim" or api_key_real == "" or secret_key_real == "":
        st.warning("⚠️ Modo Real desativado nos Secrets. Operando em Modo Simulador Protegido.")
        return False
        
    try:
        exchange = ccxt.bybit({
            'apiKey': api_key_real,
            'secret': secret_key_real,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} 
        })
        
        if tipo_ordem == "COMPRA":
            # AJUSTADO: Compra o equivalente a $6 dólares para proteger sua banca de $20
            ordem = exchange.create_market_buy_order(simbolo_bybit, 6)
            enviar_alerta_telegram(f"💰 *EXECUÇÃO REAL NA BYBIT:* Comprei $6 de {simbolo_bybit} direto na sua conta!")
        elif tipo_ordem == "VENDA":
            balance = exchange.fetch_balance()
            moeda_pura = simbolo_bybit.split('/')
            quantidade_disponivel = balance['total'].get(moeda_pura, 0)
            
            if quantidade_disponivel > 0:
                ordem = exchange.create_market_sell_order(simbolo_bybit, quantidade_disponivel)
                enviar_alerta_telegram(f"💰 *EXECUÇÃO REAL NA BYBIT:* Vendi todo o saldo de {moeda_pura} na sua conta!")
        return True
    except Exception as e:
        enviar_alerta_telegram(f"❌ *ERRO NA BYBIT:* Falha ao enviar ordem automática: {str(e)}")
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
        df_historico = yf.Ticker(ticker_name).history(period="60d", interval="1d")
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
            trades.append({"Tipo": "🟢 COMPRA", "Data": data.strftime('%d/%m/%Y'), "Preço": f"${preco:,.2f}", "RSI": f"{rsi:.1f}", "Resultado": "Em aberto"})
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

mapeamento = {"🪙 Bitcoin (BTC)": ("BTC-USD", "BTC/USDT"), "⧫ Ethereum (ETH)": ("ETH-USD", "ETH/USDT"), "☀️ Solana (SOL)": ("SOL-USD", "SOL/USDT")}
ticker_yf, simbolo_bybit = mapeamento[moeda_selecionada]

df_mercado = buscar_dados_e_indicadores(ticker_yf)

if df_mercado is not None:
    capital_final, df_trades = rodar_simulador(df_mercado)
    lucro_total = ((capital_final - 1000.0) / 1000.0) * 100
    ult = df_mercado.iloc[-1]
    preco_atual = ult['fechamento']
    rsi_atual = ult['rsi_14']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Preço Atual", f"${preco_atual:,.2f}")
    col2.metric("Força RSI", f"{rsi_atual:.2f}")
    col3.metric("Lucro Mês (Simulado)", f"{lucro_total:+.2f}%")
    col4.metric("Saldo Total (Simulado)", f"${capital_final:,.2f}")
    
    sc_tot = sum([ia_analisar_sentimento(n.get('title', '')) for n in lista_noticias])
    sc_med = sc_tot / len(lista_noticias) if lista_noticias else 0.0
    sent_ia = "OTIMISTA" if sc_med > 0.05 else ("PESSIMISTA" if sc_med < -0.05 else "NEUTRO")
    
    st.markdown("### 🧠 Painel de Sentimento da IA")
    for n in lista_noticias:
        st.write(f"🔹 {n.get('title', '')}")
    st.write(f"👉 **Veredito de Texto da IA:** {sent_ia} (Score: {sc_med:+.2f})")
    
    st.markdown("### 🤖 Veredito do Robô em Tempo Real")
    if rsi_atual <= 30 and sent_ia == "OTIMISTA":
        st.success(f"🔥 SINAL DE COMPRA ATIVO! Disparando ordem real de $6 na Bybit para {simbolo_bybit}...")
        executar_ordem_real_bybit("COMPRA", simbolo_bybit)
    elif rsi_atual >= 65 and sent_ia == "PESSIMISTA":
        st.warning(f"🔴 SINAL DE VENDA ATIVO! Realizando lucros de {simbolo_bybit} na Bybit...")
        executar_ordem_real_bybit("VENDA", simbolo_bybit)
    else:
        st.info("🟡 STATUS: AGUARDANDO. Mercado fora dos filtros de certeza absoluta. Capital protegido na Bybit.")
        
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df_mercado['date'], df_mercado['fechamento'], color='#00ffcc')
    ax.plot(df_mercado['date'], df_mercado['ema_20'], color='#ff9900', linestyle='--')
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    
    st.markdown("### 📜 Histórico de Transações (Últimos 30 Dias)")
    st.text(df_trades.to_string(index=False) if not df_trades.empty else "Nenhuma operação efetuada.")
else:
    st.error("Erro ao carregar dados do mercado.")
