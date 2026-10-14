import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime

# Configuração da Página Web ORIGINAL
st.set_page_config(page_title="Crypto Bot AI", page_icon="🤖", layout="wide")

st.title("🤖 Crypto Bot AI - Painel de Controle Quantitativo")
st.markdown("Aqui você acompanha a IA analisando o mercado com filtros de certeza absoluta.")

# ==============================================================================
# 1. CRIAÇÃO DAS ABAS INTERATIVAS (BTC, ETH, SOL)
# ==============================================================================
aba_btc, aba_eth, aba_sol = st.tabs(["🪙 Bitcoin (BTC)", "⧫ Ethereum (ETH)", "☀️ Solana (SOL)"])

# Configurações de cada moeda para a busca no Yahoo Finance
config_moedas = {
    "Bitcoin (BTC)": {"ticker": "BTC-USD", "aba": aba_btc},
    "Ethereum (ETH)": {"ticker": "ETH-USD", "aba": aba_eth},
    "Solana (SOL)": {"ticker": "SOL-USD", "aba": aba_sol}
}

# ==============================================================================
# FUNÇÃO DE CAPTURA ORIGINAL ADAPTADA PARA MULTIMOEDAS
# ==============================================================================
@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker_name):
    try:
        # Puxa os dados diários da moeda selecionada dos últimos 60 dias
        ticker = yf.Ticker(ticker_name)
        df_historico = ticker.history(period="60d", interval="1d")
        
        if df_historico.empty:
            return None
            
        df = df_historico.reset_index()
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns={'close': 'fechamento'})
        
        # 1. Cálculo matemático nativo da EMA 20
        df['ema_20'] = df['fechamento'].ewm(span=20, adjust=False).mean()
        
        # 2. Cálculo matemático nativo do RSI 14
        delta = df['fechamento'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / (perda + 0.00001)
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        return df.dropna()
    except Exception as e:
        return None

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
# RENDERIZAÇÃO DAS ABAS DE FORMA INDEPENDENTE
# ==============================================================================
for nome_moeda, info in config_moedas.items():
    with info["aba"]:
        df_mercado = buscar_dados_e_indicadores(info["ticker"])
        
        if df_mercado is not None:
            capital_final, df_trades = rodar_simulador(df_mercado)
            lucro_total = ((capital_final - 1000.0) / 1000.0) * 100
            
            ultima_linha = df_mercado.iloc[-1]
            preco_atual = ultima_linha['fechamento']
            rsi_atual = ultima_linha['rsi_14']
            
            # BLOCOS SUPERIORES DE MÉTRICAS (MANTIDO IDÊNTICO)
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
            
            st.markdown(f"### 🤖 Veredito para {nome_moeda} em Tempo Real")
            if rsi_atual <= 30:
                st.success(f"🟢 SINAL DE COMPRA ATIVO! {nome_moeda} está em região de barganha absoluta.")
            elif rsi_atual >= 65:
                st.warning(f"🔴 SINAL DE REALIZAÇÃO / VENDA! {nome_moeda} atingiu o topo de exaustão.")
            else:
                st.info(f"🟡 STATUS: AGUARDANDO. {nome_moeda} está em zona neutra. Protegendo seu patrimônio fora de risco.")

            # GRÁFICO BLINDADO EM MATPLOTLIB REPLICADO POR MOEDA
            st.markdown("### 📈 Gráfico de Análise Avançada")
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(df_mercado['date'], df_mercado['fechamento'], label=f'Preço {nome_moeda}', color='#00ffcc', linewidth=1.5)
            ax.plot(df_mercado['date'], df_mercado['ema_20'], label='Tendência (EMA 20)', color='#ff9900', linestyle='--')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.1)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig) # Fecha a figura para não misturar dados na memória

            # TABELA EM TEXTO LEVE
            st.markdown("### 📜 Histórico de Transações Efetuadas (Últimos 30 Dias)")
            if not df_trades.empty:
                st.text(df_trades.to_string(index=False))
            else:
                st.write(f"Nenhuma operação aberta para {nome_moeda} nesta região de filtro extremo de segurança.")
        else:
            st.error(f"Sincronizando dados de {nome_moeda}... Dê F5 na página em alguns segundos para carregar.")
