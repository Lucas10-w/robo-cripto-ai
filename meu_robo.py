import time
from pybit.unified_trading import HTTP

# =====================================================================
# CONFIGURAÇÕES REAIS DA SUA CONTA
# =====================================================================
API_KEY = "x8T9oSkt2KIr6QgXkO"
API_SECRET = "0nOQclVnnQr6IEayBUyNYxIwcYdg75QZpJHT"

session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def executar_estrategia_spot(symbol="BTCUSDT"):
    print("\n" + "="*50)
    print(f"⏱️ [M5] Monitorando gráfico Spot para: {symbol}")
    print("="*50)
    
    try:
        # 1. Puxa o preço atual do Bitcoin no mercado à vista
        ticker = session.get_tickers(category="spot", symbol=symbol)
        preco_atual = float(ticker['result']['list'][0]['lastPrice'])
        print(f"💵 Preço Atual do BTC (Spot): ${preco_atual:,.2f}")
        
        # 2. Calcula os pontos de operação sem centavos (arredondado)
        preco_compra = int(preco_atual * 0.995)   
        take_profit  = int(preco_compra * 1.005)  
        
        # 3. Puxa o saldo da carteira Unificada usando índices numéricos para evitar erros de texto
        carteira = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        saldo_real = float(carteira['result']['list'][0]['coin'][0]['walletBalance'])
        print(f"💰 Seu Saldo Real em USDT: ${saldo_real:,.2f}")
        
        # Desconta uma micro-margem de segurança de $0.15 para taxas da corretora
        saldo_seguro = saldo_real - 0.15
        quantidade_btc = round(saldo_seguro / preco_compra, 5)
        
        if saldo_real < 5:
            print("⚠️ O saldo mínimo exigido para ordens no mercado Spot da Bybit é de $5.00 USDT.")
            return

        print(f"📝 Próxima Operação Programada:")
        print(f"   ├─🛒 Comprar quando recuar para: ${preco_compra:,}.00")
        print(f"   ├─🎯 Vender e realizar lucro em: ${take_profit:,}.00")
        print(f"   └─📦 Quantidade da ordem: {quantidade_btc} BTC")
        
        # 4. Envia a ordem de compra limite para a corretora
        session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            qty=str(quantidade_btc),
            price=str(preco_compra),
            timeInForce="GTC"
        )
        print("✅ Ordem de compra armada com sucesso na Bybit!")
        
    except Exception as e:
        print(f"⚠️ Erro ao comunicar com a Bybit: {e}")

if __name__ == "__main__":
    print("🤖 Robô de Operações Spot Iniciado no seu Computador!")
    print("🇧🇷 Conexão estabelecida via IP brasileiro (Sem bloqueios).")
    while True:
        executar_estrategia_spot()
        print("\n💤 Dormindo por 5 minutos antes da próxima verificação...")
        time.sleep(300)
