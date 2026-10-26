import streamlit as st
import time
from pybit.unified_trading import HTTP

# Configuração visual básica para a tela não ficar vazia
st.title("🤖 Bot de Alavancagem - Grid M5")
st.markdown("Estratégia ativa seguindo o gráfico a cada 5 minutos.")

# =====================================================================
# CONFIGURAÇÕES REAIS DA SUA CONTA (COLE SUAS CHAVES DA BYBIT AQUI)
# =====================================================================
API_KEY = "KoLkJ0mYiGZJeMll6w"
API_SECRET = "QpVFiWNHcb43lfb04qEZpjgIHzKtRUi2w9OY"

# Conexão direta com o servidor de produção real da Bybit (testnet=False)
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def executar_grid_rapido(symbol="BTCUSDT", leverage=10):
    st.markdown("---")
    st.write(f"⏱️ **[M5] Verificando mercado para:** {symbol}...")
    
    try:
        # 1. Configura a alavancagem de 10x na sua conta de trading
        session.set_leverage(
            category="linear", symbol=symbol, 
            buyLeverage=str(leverage), sellLeverage=str(leverage)
        )
    except:
        pass
        
    try:
        # 2. Captura o preço atual do Bitcoin
        ticker = session.get_tickers(category="linear", symbol=symbol)
        preco_atual = float(ticker['result']['list']['lastPrice'])
        st.info(f"💵 **Preço Atual do BTC:** ${preco_atual:,.2f}")
        
        # 3. Calcula os pontos da grade (0.5% de distância)
        preco_compra = round(preco_atual * 0.995, 2)   # Compra 0.5% abaixo
        take_profit  = round(preco_compra * 1.005, 2)  # Vende 0.5% acima da compra
        stop_loss    = round(preco_compra * 0.992, 2)  # Proteção de perda em 0.8%
        
        # 4. Puxa o seu saldo real de 19.65 USDT automaticamente da conta Unificada
        carteira = session.get_wallet_balance(category="linear", coin="USDT")
        saldo_real = float(carteira['result']['list']['coin']['walletBalance'])
        st.metric(label="Seu Saldo Real na Bybit", value=f"${saldo_real:,.2f}")
        
        # 5. Aplica os Juros Compostos (calcula o lote com base no saldo total)
        poder_compra = saldo_real * leverage
        quantidade_btc = round(poder_compra / preco_compra, 3)
        
        if quantidade_btc <= 0:
            st.warning("⚠️ Saldo insuficiente para lote mínimo.")
            return

        st.markdown("### 📝 Ordem de Grade Inteligente Planejada")
        st.write(f"🛒 **Preço de Entrada (Compra):** ${preco_compra:,.2f}")
        st.write(f"🎯 **Alvo (Take Profit):** ${take_profit:,.2f}")
        st.write(f"🛡️ **Proteção (Stop Loss):** ${stop_loss:,.2f}")
        st.write(f"📦 **Tamanho do Lote:** {quantidade_btc} BTC")
        
        # 6. Envia a ordem para a Bybit
        session.place_order(
            category="linear", symbol=symbol, side="Buy", orderType="Limit",
            qty=str(quantidade_btc), price=str(preco_compra),
            takeProfit=str(take_profit), stopLoss=str(stop_loss),
            tpTriggerBy="LastPrice", slTriggerBy="LastPrice", timeInForce="GTC"
        )
        st.success("✅ Armadilha de grade enviada com sucesso para a Bybit!")
        
    except Exception as e:
        st.error(f"⚠️ Erro ao processar dados da Bybit: {e}")

# Executa a estratégia de forma compatível com a interface do Streamlit
executar_grid_rapido()

# Faz o papel do loop: espera o tempo e manda a página se atualizar sozinha
st.write("⏱️ Aguardando 5 minutos para a próxima verificação automática...")
time.sleep(300)
st.rerun()
