
import hashlib
import hmac
import json
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# CONFIGURAÇÃO DA APLICAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto Bot AI",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Crypto Bot AI")
st.caption("Monitoramento de criptomoedas | Bybit | Simulador")

st.warning(
    "Modo de simulação: os resultados são históricos e não garantem "
    "lucros futuros. Nenhuma ordem real é enviada por esta versão."
)


# ============================================================
# CONFIGURAÇÕES SECRETAS
# ============================================================

def obter_secret(nome, padrao=""):
    try:
        return st.secrets.get(nome, padrao)
    except Exception:
        return padrao


TELEGRAM_TOKEN = obter_secret("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = obter_secret("TELEGRAM_CHAT_ID")

# Mantidas para uma futura integração com a Bybit.
# Esta versão não utiliza essas chaves para operar.
BYBIT_API_KEY = obter_secret("BYBIT_API_KEY")
BYBIT_SECRET_KEY = obter_secret("BYBIT_SECRET_KEY")


# ============================================================
# TELEGRAM
# ============================================================

def enviar_alerta_telegram(mensagem):
    """Envia uma mensagem para o Telegram, se configurado."""

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    )

    dados = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            resultado = json.loads(resposta.read().decode("utf-8"))

        return resultado.get("ok", False)

    except Exception as erro:
        st.error(f"Não foi possível enviar o alerta ao Telegram: {erro}")
        return False


# ============================================================
# ANÁLISE SIMPLES DE SENTIMENTO
# ============================================================

def analisar_sentimento(texto):
    """Retorna uma pontuação lexical aproximada, não uma previsão."""

    positivas = {
        "bullish", "surge", "rise", "buy", "accumulate",
        "gain", "growth", "positive", "green", "support",
        "alta", "valorização", "compra", "crescimento",
    }

    negativas = {
        "bearish", "drop", "fall", "sell", "crash",
        "loss", "negative", "risk", "panic", "resistance",
        "queda", "perda", "venda", "risco",
    }

    palavras = (
        texto.lower()
        .replace(",", " ")
        .replace(".", " ")
        .replace("!", " ")
        .replace("?", " ")
        .split()
    )

    pontuacao = sum(
        1 for palavra in palavras if palavra in positivas
    ) - sum(
        1 for palavra in palavras if palavra in negativas
    )

    return max(-1.0, min(1.0, pontuacao * 0.2))


# ============================================================
# DADOS DE MERCADO E INDICADORES
# ============================================================

MOEDAS = {
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD",
    "Solana (SOL)": "SOL-USD",
}


@st.cache_data(ttl=60)
def buscar_dados_e_indicadores(ticker):
    """Obtém candles diários e calcula EMA 20 e RSI 14."""

    try:
        df = yf.Ticker(ticker).history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )

        if df.empty or "Close" not in df.columns:
            return None

        df = df[["Close"]].copy()
        df = df.rename(columns={"Close": "fechamento"})
        df = df.dropna(subset=["fechamento"])

        df["ema_20"] = df["fechamento"].ewm(
            span=20,
            adjust=False,
        ).mean()

        delta = df["fechamento"].diff()

        ganho = delta.clip(lower=0)
        perda = -delta.clip(upper=0)

        media_ganho = ganho.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()

        media_perda = perda.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()

        rs = media_ganho / media_perda.replace(0, float("nan"))

        df["rsi_14"] = 100 - (100 / (1 + rs))

        # Trata casos em que o preço só subiu ou só caiu.
        df.loc[
            (media_perda == 0) & (media_ganho > 0),
            "rsi_14",
        ] = 100

        df.loc[
            (media_perda == 0) & (media_ganho == 0),
            "rsi_14",
        ] = 50

        df["rsi_14"] = df["rsi_14"].fillna(50)
        df.index.name = "data"

        return df.dropna(subset=["ema_20", "rsi_14"])

    except Exception:
        return None


# ============================================================
# SIMULADOR HISTÓRICO
# ============================================================

def rodar_simulador(df, capital_inicial=1000.0):
    """
    Estratégia demonstrativa:
    - Compra quando RSI <= 30 e não existe posição.
    - Vende quando RSI >= 65 e existe posição.
    - Utiliza o capital disponível em cada compra.
    - Não inclui taxas, slippage ou impostos.
    """

    capital = float(capital_inicial)
    quantidade = 0.0
    preco_compra = 0.0
    data_compra = None
    trades = []

    for data, linha in df.iterrows():
        preco = float(linha["fechamento"])
        rsi = float(linha["rsi_14"])

        if rsi <= 30 and quantidade == 0 and capital > 0:
            quantidade = capital / preco
            preco_compra = preco
            data_compra = data

            trades.append({
                "Compra": data.strftime("%d/%m/%Y"),
                "Venda": "Em aberto",
                "Preço compra": preco_compra,
                "Preço venda": None,
                "Resultado (%)": None,
                "Resultado ($)": None,
                "Status": "Em aberto",
            })

        elif rsi >= 65 and quantidade > 0:
            valor_venda = quantidade * preco
            lucro = valor_venda - (quantidade * preco_compra)
            retorno = (preco / preco_compra - 1) * 100

            capital = valor_venda
            quantidade = 0.0

            trades[-1].update({
                "Venda": data.strftime("%d/%m/%Y"),
                "Preço venda": preco,
                "Resultado (%)": round(retorno, 2),
                "Resultado ($)": round(lucro, 2),
                "Status": "Fechada",
            })

    # Valoriza a posição aberta pelo último preço disponível.
    ultimo_preco = float(df["fechamento"].iloc[-1])

    if quantidade > 0:
        capital_final = quantidade * ultimo_preco

        trades[-1].update({
            "Preço venda": ultimo_preco,
            "Resultado (%)": round(
                (ultimo_preco / preco_compra - 1) * 100, 2
            ),
            "Resultado ($)": round(
                quantidade * (ultimo_preco - preco_compra), 2
            ),
            "Status": "Em aberto",
        })
    else:
        capital_final = capital

    historico = pd.DataFrame(trades)

    return capital_final, historico


# ============================================================
# INTERFACE PRINCIPAL
# ============================================================

aba_btc, aba_eth, aba_sol = st.tabs([
    "🪙 Bitcoin (BTC)",
    "⧫ Ethereum (ETH)",
    "☀️ Solana (SOL)",
])

abas = [aba_btc, aba_eth, aba_sol]

for (nome, ticker), aba in zip(MOEDAS.items(), abas):
    with aba:
        st.subheader(nome)

        with st.spinner(f"Buscando dados de {ticker}..."):
            df = buscar_dados_e_indicadores(ticker)

        if df is None or df.empty:
            st.error(
                "Não foi possível carregar os dados do mercado. "
                "Verifique sua conexão e tente novamente."
            )
            continue

        preco_atual = float(df["fechamento"].iloc[-1])
        rsi_atual = float(df["rsi_14"].iloc[-1])
        ema_atual = float(df["ema_20"].iloc[-1])

        capital_final, trades = rodar_simulador(df)

        lucro_percentual = (capital_final / 1000.0 - 1) * 100

        # Métricas
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "💲 Último fechamento",
            f"${preco_atual:,.2f}",
        )

        col2.metric(
            "📈 RSI 14",
            f"{rsi_atual:.2f}",
            help="Abaixo de 30: região frequentemente considerada sobrevendida. "
                 "Acima de 70: região frequentemente considerada sobrecomprada.",
        )

        col3.metric(
            "📊 Resultado simulado",
            f"{lucro_percentual:+.2f}%",
        )

        col4.metric(
            "💰 Patrimônio simulado",
            f"${capital_final:,.2f}",
            delta=f"{capital_final - 1000.0:+,.2f} USD",
        )

        # Interpretação dos indicadores
        st.markdown("### Análise dos indicadores")

        ind1, ind2 = st.columns(2)

        with ind1:
            st.write(f"**EMA 20:** ${ema_atual:,.2f}")

            if preco_atual > ema_atual:
                st.info("Preço acima da EMA 20.")
            elif preco_atual < ema_atual:
                st.info("Preço abaixo da EMA 20.")
            else:
                st.info("Preço próximo da EMA 20.")

        with ind2:
            st.write(f"**RSI atual:** {rsi_atual:.2f}")

            if rsi_atual <= 30:
                st.warning(
                    "RSI em região frequentemente considerada sobrevendida. "
                    "Isso não confirma uma compra."
                )
            elif rsi_atual >= 70:
                st.warning(
                    "RSI em região frequentemente considerada sobrecomprada. "
                    "Isso não confirma uma venda."
                )
            else:
                st.info("RSI fora das regiões extremas de 30 e 70.")

        # Gráfico
        st.markdown("### Histórico de preços")

        st.line_chart(
            df[["fechamento", "ema_20"]].rename(
                columns={
                    "fechamento": "Preço",
                    "ema_20": "EMA 20",
                }
            )
        )

        st.markdown("### Histórico do simulador")

        if trades.empty:
            st.info(
                "Nenhuma operação foi identificada pela estratégia "
                "no período analisado."
            )
        else:
            st.dataframe(
                trades,
                use_container_width=True,
                hide_index=True,
            )

        st.caption(
            "Período: aproximadamente 6 meses de candles diários. "
            "O último candle pode ainda estar em formação. "
            "Resultados passados não garantem resultados futuros."
        )


# ============================================================
# ALERTA MANUAL PELO TELEGRAM
# ============================================================

st.divider()
st.subheader("📨 Teste do Telegram")

mensagem = st.text_input(
    "Mensagem de teste",
    value="Crypto Bot AI: teste de notificação.",
)

if st.button("Enviar mensagem de teste"):
    if enviar_alerta_telegram(mensagem):
        st.success("Mensagem enviada ao Telegram.")
    else:
        st.error(
            "Não foi possível enviar. Confira o token, o chat ID "
            "e se o bot já pode enviar mensagens para esse chat."
        )

st.caption(
    f"Última atualização da interface: "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)
