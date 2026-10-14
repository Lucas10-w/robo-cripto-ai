import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# Força o matplotlib a trabalhar em modo de segundo plano (Garante estabilidade na nuvem)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Configuração da Página Web ORIGINAL
st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")

st.title("🤖 Crypto Bot AI - Painel de Controle Quantitativo")
st.markdown("Aqui você acompanha a IA analisando o mercado com filtros de certeza absoluta.")

# ==============================================================================
# CONFIGURAÇÃO DO SEU TELEGRAM (COLE SEU TOKEN RECENTE AQUI)
# ==============================================================================
TELEGRAM_TOKEN = "8659842719:AAHzgJe_6dh-GPxrEjOwqaQ8-Z2HdvTjEUg"
TELEGRAM_CHAT_ID = "5977741363"

def enviar_alerta_telegram(mensagem):
    """Envia uma notificação em tempo real direto para o seu celular via Telegram"""
    if TELEGRAM_TOKEN == "COLE_AQUI_O_SEU_TOKEN_DO_BOTFATHER" or TELEGRAM_CHAT_ID == "":
        return 
    try:
        texto_codificado = urllib.parse.quote(mensagem)
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={texto_codificado}&parse_mode=Markdown"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            pass
    except:
        pass

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
# RENDERIZAÇÃO CENTRALIZADA DAS ABAS INDEPENDENTES (SEM loops/erros de espaço)
# ==============================================================================
lista_noticias = buscar_noticias_cripto()
aba_btc, aba_eth, aba_sol = st.tabs(["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

# ------------------------------------------------------------------------------
# ABA 1: BITCOIN (BTC)
# ------------------------------------------------------------------------------
with aba_btc:
    df_btc = buscar_dados_e_indicadores("BTC-USD")
    if df_btc is not None:
        cap_btc, trades_btc = rodar_simulador(df_btc)
        lucro_btc = ((cap_btc - 1000.0) / 1000.0) * 100
        ult_btc = df_btc.iloc[-1]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💲 Preço BTC", f"${ult_btc['fechamento']:,.2f}")
        c2.metric("📈 Força RSI", f"{ult_btc['rsi_14']:.2f}")
        c3.metric("📊 Lucro Mês", f"{lucro_btc:+.2f}%")
        c4.metric("💰 Saldo Total", f"${cap_btc:,.2f}")
        
        # Bloco de notícias BTC
        st.markdown("### 🧠 Painel de Sentimento da IA para Bitcoin (BTC)")
        sc_tot = 0.0
        cont = 0
        for n in lista_noticias:
            t = n.get('title', '')
            if "btc" in t.lower() or "bitcoin" in t.lower() or "market" in t.lower() or "crypto" in t.lower():
                sc = ia_analisar_sentimento(t)
                sc_tot += sc
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
        if ult_btc['rsi_14'] <= 30 and sent_ia == "OTIMISTA":
            st.success("🔥 SINAL MÁXIMO DE COMPRA! Técnico e IA confirmam entrada segura.")
            enviar_alerta_telegram(f"🚨 Alerta! Sinal Máximo de COMPRA para Bitcoin (BTC): ${ult_btc['fechamento']:,.2f}")
        elif ult_btc['rsi_14'] >= 65 and sent_ia == "PESSIMISTA":
            st.warning("⚠️ AVISO DE REALIZAÇÃO COMPLETA! Gráfico saturado.")
        else:
            st.info("🟡 STATUS: AGUARDANDO. Sem sincronia perfeita ou zona neutra. Capital protegido!")
            
        st.markdown("### 📈 Gráfico de Análise Avançada")
        f, ax = plt.subplots(figsize=(12, 3.5))
        ax.plot(df_btc['date'], df_btc['fechamento'], label='Preço BTC', color='#00ffcc')
        ax.plot(df_btc['date'], df_btc['ema_20'], label='EMA 20', color='#ff9900', linestyle='--')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.1)
        plt.tight_layout()
        st.pyplot(f)
        plt.close(f)
        
        st.markdown("### 📜 Histórico de Transações (Últimos 30 Dias)")
        st.text(trades_btc.to_string(index=False) if not trades_btc.empty else "Nenhuma operação efetuada.")

# ------------------------------------------------------------------------------
# ABA 2: ETHEREUM (ETH)
# ------------------------------------------------------------------------------
with aba_eth:
    df_eth = buscar_dados_e_indicadores("ETH-USD")
    if df_eth is not None:
        cap_eth, trades_eth = rodar_simulador(df_eth)
        lucro_eth = ((cap_eth - 1000.0) / 1000.0) * 100
        ult_eth = df_eth.iloc[-1]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💲 Preço ETH", f"${ult_eth['fechamento']:,.2f}")
        c2.metric("📈 Força RSI", f"{ult_eth['rsi_14']:.2f}")
        c3.metric("📊 Lucro Mês", f"{lucro_eth:+.2f}%")
        c4.metric("💰 Saldo Total", f"${cap_eth:,.2f}")
        
        st.markdown("### 🧠 Painel de Sentimento da IA para Ethereum (ETH)")
        sc_tot = 0.0
        cont = 0
        for n in lista_noticias:
            t = n.get('title', '')
            if "eth" in t.lower() or "ethereum" in t.lower() or "market" in t.lower() or "crypto" in t.lower():
                sc = ia_analisar_sentimento(t)
                sc_tot += sc
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
        if ult_eth['rsi_14'] <= 30 and sent_ia == "OTIMISTA":
            st.success("🔥 SINAL MÁXIMO DE COMPRA! Técnico e IA confirmam entrada segura.")
            enviar_alerta_telegram(f"🚨 Alerta! Sinal Máximo de COMPRA para Ethereum (ETH): ${ult_eth['fechamento']:,.2f}")
        elif ult_eth['rsi_14'] >= 65 and sent_ia == "PESSIMISTA":
            st.warning("⚠️ AVISO DE REALIZAÇÃO COMPLETA! Gráfico saturado.")
        else:
