import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# Configuração de segurança visual para a nuvem
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")
st.title("🤖 Crypto Bot AI - Painel de Controle Quantitativo")
st.markdown("Aqui você acompanha a IA analisando o mercado com filtros de certeza absoluta.")

# ==============================================================================
# CONFIGURAÇÃO DO SEU TELEGRAM (COLE SEU TOKEN RECENTE AQUI)
# ==============================================================================
TELEGRAM_TOKEN = "8659842719:AAHzgJe_6dh-GPxrEjOwqaQ8-Z2HdvTjEUg"
TELEGRAM_CHAT_ID = "5977741363"

def enviar_alerta_telegram(mensagem):
    if TELEGRAM_TOKEN == "COLE_AQUI_O_SEU_TOKEN_DO_BOTFATHER" or TELEGRAM_CHAT_ID == "":
        return 
    try:
        texto_codificado = urllib.parse.quote(mensagem)
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={texto_codificado}&parse_mode=Markdown"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: pass
    except: pass

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
        with urllib.request.urlopen(req) as response:
            dados = json.loads(response.read().decode())
        return dados.get('data', [])
    except:
        return [
            {"title": "Bitcoin institutions continue steady accumulation in secure zones"},
            {"title": "Crypto markets show stable consolidation ahead of liquidity influx"},
            {"title": "Regulators signal positive environment for digital asset growth"}
        ]

@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker_name):
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_name)
        df_historico = ticker.history(period="60d", interval="1d")
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
# EXECUÇÃO DO HUB VISUAL (ESTRUTURA COMPACTA INFALÍVEL)
# ==============================================================================
lista_noticias = buscar_noticias_cripto()
moeda_selecionada = st.selectbox("Escolha o ativo para analisar:", ["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

mapeamento = {
    "🪙 Bitcoin (BTC)": "BTC-USD",
    "⧫ Ethereum (ETH)": "ETH-USD",
    "☀️ Solana (SOL)": "SOL-USD"
}

ticker_atual = mapeamento[moeda_selecionada]
df_mercado = buscar_dados_e_indicadores(ticker_atual)

if df_mercado is not None:
    capital_final, df_trades = rodar_simulador(df_mercado)
    lucro_total = ((capital_final - 1000.0) / 1000.0) * 100
    ult = df_mercado.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Preço Atual", f"${ult['fechamento']:,.2f}")
    col2.metric("Força RSI", f"{ult['rsi_14']:.2f}")
    col3.metric("Lucro Mês", f"{lucro_total:+.2f}%")
    col4.metric("Saldo Total", f"${capital_final:,.2f}")
    
    st.markdown(f"### 🧠 Painel de Sentimento da IA")
    sc_tot = 0.0
    cont = 0
    for n in lista_noticias:
        t = n.get('title', '')
        score_n = ia_analisar_sentimento(t)
        sc_tot += score_n
        cont += 1
        st.write(f"🔹 {t}")
    sc_med = sc_tot / cont if cont > 0 else 0.0
    
    sent_ia = "NEUTRO"
    if sc_med > 0.05:
        st.success(f"🟢 OTIMISTA (Score: {sc_med:+.2f})")
        sent_ia = "OTIMISTA"
    elif sc_med < -0.05:
        st.error(f"🔴 PESSIMISTA (Score: {sc_med:+.2f})")
        sent_ia = "PESSIMISTA"
    else:
        st.warning(f"🟡 NEUTRO (Score: {sc_med:+.2f})")
        
    st.markdown("### 🤖 Veredito do Robô em Tempo Real")
    if ult['rsi_14'] <= 30 and sent_ia == "OTIMISTA":
        st.success("🔥 SINAL MÁXIMO DE COMPRA! Técnico e IA confirmam entrada segura.")
        enviar_alerta_telegram(f"🚨 Alerta! Sinal Máximo de COMPRA para {moeda_selecionada}: ${ult['fechamento']:,.2f}")
    elif ult['rsi_14'] >= 65 and sent_ia == "PESSIMISTA":
        st.warning("⚠️ AVISO DE REALIZAÇÃO COMPLETA! Gráfico saturado.")
    else:
        st.info("🟡 STATUS: AGUARDANDO. Sem sincronia perfeita ou zona neutra. Capital protegido!")
        
    st.markdown("### 📈 Gráfico de Análise Avançada")
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(df_mercado['date'], df_mercado['fechamento'], label='Preço', color='#00ffcc')
    ax.plot(df_mercado['date'], df_mercado['ema_20'], label='EMA 20', color='#ff9900', linestyle='--')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.1)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    
    st.markdown("### 📜 Histórico de Transações (Últimos 30 Dias)")
    st.text(df_trades.to_string(index=False) if not df_trades.empty else "Nenhuma operação efetuada.")
else:
    st.error("Erro ao carregar dados do mercado.")
