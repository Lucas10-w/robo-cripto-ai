import time
from pybit.unified_trading import HTTP

# =====================================================================
# CONFIGURAÇÕES REAIS DA SUA CONTA (COLE SUAS CHAVES DA BYBIT AQUI)
# =====================================================================
API_KEY = " KoLkJ0mYiGZJeMll6w"
API_SECRET = "QpVFiWNHcb43lfb04qEZpjgIHzKtRUi2w9OY"

# Conexão direta com o servidor de produção real da Bybit (testnet=False)
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def executar_grid_rapido(symbol="BTCUSDT", leverage=10):
    print("\n--------------------------------------------------")
    print(f"⏱️ [M5] Verificando mercado para: {symbol}...")
    
    try:
        # 1. Configura a alavancagem de 10x na sua conta de trading
        session.set_leverage(
            category="linear", symbol=symbol, 
            buyLeverage=str(leverage), sellLeverage=str(leverage)
        )
    except:
        # Se a alavancagem já estiver em 10x, o servidor pode dar um aviso, apenas ignoramos
        pass
        
    try:
        # 2. Captura o preço atual do Bitcoin
        ticker = session.get_tickers(category="linear", symbol=symbol)
        preco_atual = float(ticker['result']['list']['lastPrice'])
        print(f"💵 Preço Atual: ${preco_atual:,.2f}")
        
        # 3. Calcula os pontos da grade (0.5% de distância)
        preco_compra = round(preco_atual * 0.995, 2)   # Compra 0.5% abaixo
        take_profit  = round(preco_compra * 1.005, 2)  # Vende 0.5% acima da compra
        stop_loss    = round(preco_compra * 0.992, 2)  # Proteção de perda em 0.8%
        
        # 4. Puxa o seu saldo real de 19.65 USDT automaticamente da conta Unificada
        carteira = session.get_wallet_balance(category="linear", coin="USDT")
        saldo_real = float(carteira['result']['list']['coin']['walletBalance'])
        print(f"💰 Seu Saldo Real: ${saldo_real:,.2f}")
        
        # 5. Aplica os Juros Compostos (calcula o lote com base no saldo total)
        poder_compra = saldo_real * leverage
        quantidade_btc = round(poder_compra / preco_compra, 3)
        
        if quantidade_btc <= 0:
            print("⚠️ Saldo insuficiente para lote mínimo.")
            return

        print(f"📝 Armanda Ordem de Grade Inteligente:")
        print(f"   ├─🛒 Compra em: ${preco_compra:,.2f}")
        print(f"   ├─🎯 Realizar Lucro em: ${take_profit:,.2f}")
        print(f"   └─🛡️ Stop Loss em: ${stop_loss:,.2f}")
        
        # 6. Envia a ordem para a Bybit
        session.place_order(
            category="linear", symbol=symbol, side="Buy", orderType="Limit",
            qty=str(quantidade_btc), price=str(preco_compra),
            takeProfit=str(take_profit), stopLoss=str(stop_loss),
            tpTriggerBy="LastPrice", slTriggerBy="LastPrice", timeInForce="GTC"
        )
        print("✅ Armadilha de grade enviada com sucesso para a Bybit!")
        
    except Exception as e:
        print(f"⚠️ Erro ao processar dados da Bybit: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando Bot de Alavancagem em Modo Real...")
    while True:
        executar_grid_rapido()
        
        # Espera 5 minutos (300 segundos) antes da próxima rodada
        print("💤 Dormindo por 5 minutos antes da próxima checagem...")
        time.sleep(300)
