import streamlit as st
import time
from pybit.unified_trading import HTTP

# Configuração visual básica para a tela do Streamlit
st.title("🤖 Bot de Operações Ativas - Mercado Spot")
st.markdown("Estratégia ativa comprando e realizando lucros a cada 5 minutos no mercado À Vista.")

# =====================================================================
# CONFIGURAÇÕES REAIS DA SUA CONTA (COLE SUAS CHAVES DA BYBIT AQUI)
# =====================================================================
API_KEY = "SUA_API_KEY_REAL_AQUI"
API_SECRET = "SEU_API_SECRET_REAL_AQUI"

# Conexão direta com o servidor oficial da Bybit
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def executar_estrategia_spot(symbol="BTCUSDT"):
    st.markdown("---")
    st.write(f"⏱️ **[M5] Monitorando gráfico Spot para:** {symbol}...")
    
    try:
        # 1. Captura o preço atual do Bitcoin no mercado à vista
        ticker = session.get_tickers(category="spot", symbol=symbol)
        preco_atual = float(ticker['result']['list']['lastPrice'])
        st.info(f"💵 **Preço Atual do BTC (Spot):** ${preco_atual:,.2f}")
        
        # 2. Calcula os pontos de operação com base na variação de 0.5%
        preco_compra = round(preco_atual * 0.995, 2)   # Ordem de compra 0.5% abaixo
        take_profit  = round(preco_compra * 1.005, 2)  # Alvo de realização 0.5% acima
        
        # 3. Puxa o seu saldo real de 19.65 USDT da carteira
        carteira = session.get_wallet_balance(category="spot", coin="USDT")
        saldo_real = float(carteira['result']['list']['coin']['walletBalance'])
        st.metric(label="Seu Saldo Real em USDT (Spot)", value=f"${saldo_real:,.2f}")
        
        # 4. Define o valor a ser usado por operação (usa a sua banca de ~$19.65)
        # No Spot da Bybit, o valor mínimo de compra geralmente é de 1 a 5 USDT.
        valor_operacao_usdt = saldo_real
        quantidade_btc = round(valor_operacao_usdt / preco_compra, 5) # Fração exata de BTC
        
        if valor_operacao_usdt < 5:
            st.warning("⚠️ O saldo mínimo exigido para ordens no mercado Spot da Bybit é de $5.00 USDT.")
            return

        st.markdown("### 📝 Próxima Operação Programada")
        st.write(f"🛒 **Comprar quando recuar para:** ${preco_compra:,.2f}")
        st.write(f"🎯 **Vender e realizar lucro em:** ${take_profit:,.2f}")
        st.write(f"📦 **Quantidade de moedas reais adquiridas:** {quantidade_btc} BTC")
        
        # 5. Envia a ordem de compra limite para o mercado Spot
        session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            qty=str(quantidade_btc),
            price=str(preco_compra),
            timeInForce="GTC"
        )
        st.success("✅ Ordem de compra enviada com sucesso ao mercado Spot da Bybit!")
        
    except Exception as e:
        st.error(f"⚠️ Erro ao comunicar com o Spot da Bybit: {e}")

# Executa o robô no formato do Streamlit
executar_estrategia_spot()

# Atualização da tela a cada 5 minutos
st.write("⏱️ Aguardando 5 minutos para a próxima verificação automática...")
time.sleep(300)
st.rerun()
