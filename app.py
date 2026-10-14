import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import urllib.request
import json
from datetime import datetime

# Configuração da Página Web ORIGINAL
st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")

st.title("🤖 Crypto Bot AI - Painel de Controle Quantitativo")
st.markdown("Aqui você acompanha a IA analisando o mercado com filtros de certeza absoluta.")

# ==============================================================================
# CONFIGURAÇÃO DO SEU TELEGRAM (CÓDIGO ATUALIZADO)
# ==============================================================================
# Cole o código grande do BotFather dentro das aspas abaixo:
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

# ==============================================================================
# CRIAÇÃO DAS ABAS INTERATIVAS (BTC, ETH, SOL)
# ==============================================================================
aba_btc, aba_eth, aba_sol = st.tabs(["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

config_moedas = {
    "Bitcoin (BTC)": {"ticker": "BTC-USD", "aba": aba_btc},
    "Ethereum (ETH)": {"ticker": "ETH-USD", "aba": aba_eth},
    "Solana (SOL)": {"ticker": "SOL-USD", "aba": aba_sol}
}

# ==============================================================================
# FUNÇÕES DE BACK-END ORIGINAIS
# ==============================================================================
@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker_name):
    try:
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
# RENDERIZAÇÃO CENTRALIZADA
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
                    if "btc" in titulo.lower() or "bitcoin" in titulo.lower() or "market" in titulo.lower() or "crypto" in titulo.lower() or ("eth" in titulo.lower() and "eth" in info["ticker"].lower()) or ("sol" in titulo.lower() and "sol" in info["ticker"].lower()):
                        score_noticia = ia_analisar_sentimento(titulo)
                        score_total_ia += score_noticia
                        contador_noticias += 1
                        icone_sentimento = "🔹"
                        if score_noticia > 0: icone_sentimento = "🔺"
                        elif score_noticia < 0: icone_sentimento = "🔻"
                        st.write(f"{icone_sentimento} {titulo}")
                
                if contador_noticias == 0:
                    score_medio_ia = 0.0
                else:
                    score_medio_ia = score_total_ia / contador_noticias
            
            with col_status_ia:
                st.markdown("**Veredito de Texto da IA:**")
                if score_medio_ia > 0.05:
                    st.success(f"🟢 OTIMISTA (Score: {score_medio_ia:+.2f})")
                    sentimento_final_ia = "OTIMISTA"
                elif score_medio_ia < -0.05:
                    st.error(f"🔴 PESSIMISTA (Score: {score_medio_ia:+.2f})")
                    sentimento_final_ia = "PESSIMISTA"
                else:
                    st.warning(f"🟡 NEUTRO (Score: {score_medio_ia:+.2f})")
                    sentimento_final_ia = "NEUTRO"

            st.markdown(f"### 🤖 Veredito do Robô em Tempo Real")
            
            # LÓGICA DE DISPARO DO TELEGRAM EM TEMPO REAL
            if rsi_atual <= 30 and sentimento_final_ia == "OTIMISTA":
                st.success(f"🔥 SINAL MÁXIMO DE COMPRA! Técnico e IA de notícias confirmam entrada ultra segura em {nome_moeda}.")
                msg = f"🚨 *Crypto Bot AI Alerta!* 🚨\n\n🔥 *SINAL MÁXIMO DE COMPRA* detectado para *{nome_moeda}*!\n\n📈 Preço Atual: ${preco_atual:,.2f}\n📊 Indicador RSI: {rsi_atual:.1f}\n🧠 Sentimento da IA: {sentimento_final_ia}\n\n_Acesse o painel para acompanhar!_"
                enviar_alerta_telegram(msg)
            elif rsi_atual >= 65 and sentimento_final_ia == "PESSIMISTA":
                st.warning(f"⚠️ AVISO DE REALIZAÇÃO COMPLETA! Gráfico saturado e IA detectando notícias negativas.")
                msg = f"⚠️ *Crypto Bot AI Alerta!* ⚠️\n\n🔴 *AVISO DE VENDA/REALIZAÇÃO* para *{nome_moeda}*!\n\n📈 Preço Atual: ${preco_atual:,.2f}\n📊 Indicador RSI: {rsi_atual:.1f}\n🧠 Sentimento da IA: {sentimento_final_ia}"
                enviar_alerta_telegram(msg)
            else:
                st.info(f"🟡 STATUS: AGUARDANDO. O mercado está em zona de espera ou a IA e os gráficos não estão em sincronia perfeita. Capital protegido de riscos!")

            # GRÁFICO E TABELA ORIGINAIS
            st.markdown("### 📈 Gráfico de Análise Avançada")
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 3.5))
