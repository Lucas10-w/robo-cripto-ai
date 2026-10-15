
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf
from pybit.unified_trading import HTTP
from streamlit_autorefresh import st_autorefresh


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto Bot AI | Bybit",
    page_icon="🤖",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crypto_bot.db"

ASSETS = {
    "Bitcoin (BTC)": {"symbol": "BTCUSDT", "ticker": "BTC-USD"},
    "Ethereum (ETH)": {"symbol": "ETHUSDT", "ticker": "ETH-USD"},
    "Solana (SOL)": {"symbol": "SOLUSDT", "ticker": "SOL-USD"},
}

BUY_AMOUNT_USDT = Decimal("6")
RSI_BUY = 30.0
RSI_SELL = 65.0
INTERVAL_SECONDS = 60


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


TESTNET = str(secret("BYBIT_TESTNET", "true")).lower() == "true"
LIVE_ENABLED = str(
    secret("LIVE_TRADING_ENABLED", "false")
).lower() == "true"

API_KEY = secret("BYBIT_API_KEY", "")
API_SECRET = secret("BYBIT_SECRET_KEY", "")
TG_TOKEN = secret("TELEGRAM_TOKEN", "")
TG_CHAT_ID = secret("TELEGRAM_CHAT_ID", "")

# O ambiente principal só pode ser usado com duas
# configurações explícitas e uma confirmação na interface.
ENVIRONMENT = "TESTNET" if TESTNET else "PRODUÇÃO"


# ============================================================
# BANCO DE DADOS
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_link_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty TEXT NOT NULL,
                status TEXT NOT NULL,
                order_id TEXT,
                created_at TEXT NOT NULL,
                details TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                qty TEXT NOT NULL,
                avg_price TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                candle_time TEXT NOT NULL,
                rsi REAL NOT NULL,
                ema REAL NOT NULL,
                price REAL NOT NULL,
                signal TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, candle_time)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)


def log_event(message, level="INFO"):
    with db() as conn:
        conn.execute(
            "INSERT INTO events(created_at, level, message) VALUES(?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(),
                level,
                message,
            ),
        )


def get_events(limit=100):
    with db() as conn:
        return pd.read_sql_query(
            "SELECT created_at, level, message FROM events "
            "ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def get_orders(limit=100):
    with db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def get_position(symbol):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE symbol = ?",
            (symbol,),
        ).fetchone()
    return dict(row) if row else None


def save_position(symbol, qty, avg_price):
    with db() as conn:
        conn.execute("""
            INSERT INTO positions(symbol, qty, avg_price, updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(symbol) DO UPDATE SET
                qty=excluded.qty,
                avg_price=excluded.avg_price,
                updated_at=excluded.updated_at
        """, (
            symbol,
            str(qty),
            str(avg_price),
            datetime.now(timezone.utc).isoformat(),
        ))


init_db()


# ============================================================
# TELEGRAM
# ============================================================

def telegram(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        return False

    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": TG_CHAT_ID,
        "text": message,
    }).encode()

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode())
        return result.get("ok", False)
    except Exception as exc:
        log_event(f"Telegram indisponível: {exc}", "ERROR")
        return False


# ============================================================
# BYBIT V5
# ============================================================

@st.cache_resource
def get_client(api_key, api_secret, testnet):
    if not api_key or not api_secret:
        return None

    return HTTP(
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret,
        recv_window=5000,
    )


client = get_client(API_KEY, API_SECRET, TESTNET)


def bybit_call(method, **kwargs):
    if client is None:
        raise RuntimeError("Credenciais da Bybit não configuradas.")

    response = method(**kwargs)

    if response.get("retCode") != 0:
        raise RuntimeError(
            f"Bybit {response.get('retCode')}: "
            f"{response.get('retMsg')}"
        )

    return response.get("result", {})


def get_balance(coin):
    result = bybit_call(
        client.get_wallet_balance,
        accountType="UNIFIED",
        coin=coin,
    )

    for account in result.get("list", []):
        for item in account.get("coin", []):
            if item.get("coin") == coin:
                return {
                    "wallet": Decimal(item.get("walletBalance", "0")),
                    "available": Decimal(
                        item.get("availableToWithdraw") or "0"
                    ),
                    "equity": Decimal(item.get("equity", "0")),
                }

    return {
        "wallet": Decimal("0"),
        "available": Decimal("0"),
        "equity": Decimal("0"),
    }


def get_instrument(symbol):
    result = bybit_call(
        client.get_instruments_info,
        category="spot",
        symbol=symbol,
    )

    instruments = result.get("list", [])
    if not instruments:
        raise RuntimeError(f"Instrumento não encontrado: {symbol}")

    info = instruments[0]
    lot = info["lotSizeFilter"]

    return {
        "status": info.get("status"),
        "base": info.get("baseCoin"),
        "quote": info.get("quoteCoin"),
        "min_qty": Decimal(lot["minOrderQty"]),
        "qty_step": Decimal(lot["qtyStep"]),
        "min_amount": Decimal(lot.get("minOrderAmt", "0")),
    }


def round_down(value, step):
    if step <= 0:
        raise ValueError("Incremento inválido.")
    return (value / step).to_integral_value(
        rounding=ROUND_DOWN
    ) * step


def order_exists(order_link_id):
    with db() as conn:
        return conn.execute(
            "SELECT 1 FROM orders WHERE order_link_id = ?",
            (order_link_id,),
        ).fetchone() is not None


def register_order(link_id, symbol, side, qty, status, details=""):
    with db() as conn:
        conn.execute("""
            INSERT INTO orders(
                order_link_id, symbol, side, qty, status,
                created_at, details
            ) VALUES(?,?,?,?,?,?,?)
        """, (
            link_id,
            symbol,
            side,
            str(qty),
            status,
            datetime.now(timezone.utc).isoformat(),
            details,
        ))


def update_order(link_id, status, order_id=None, details=""):
    with db() as conn:
        conn.execute("""
            UPDATE orders
            SET status = ?,
                order_id = COALESCE(?, order_id),
                details = ?
            WHERE order_link_id = ?
        """, (status, order_id, details, link_id))


def submit_spot_order(symbol, side, quantity, quote_amount=False):
    """
    Envia uma ordem Spot e registra o estado inicial.
    A aceitação da ordem não significa execução confirmada.
    """

    link_id = uuid.uuid4().hex[:32]

    if order_exists(link_id):
        raise RuntimeError("Identificador de ordem duplicado.")

    params = {
        "category": "spot",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(quantity),
        "orderLinkId": link_id,
    }

    if quote_amount and side == "Buy":
        params["marketUnit"] = "quoteCoin"

    # Registra a tentativa antes da chamada externa.
    register_order(
        link_id,
        symbol,
        side,
        quantity,
        "SUBMITTING",
        json.dumps(params),
    )

    try:
        result = bybit_call(client.place_order, **params)

        order_id = result.get("orderId")
        update_order(
            link_id,
            "SUBMITTED",
            order_id,
            json.dumps(result),
        )

        telegram(
            f"Crypto Bot AI: ordem enviada à Bybit.\n"
            f"Ativo: {symbol}\nLado: {side}\n"
            f"Identificador: {link_id}"
        )

        return link_id, order_id

    except Exception as exc:
        # Não repetir automaticamente: pode haver timeout
        # após a exchange já ter aceitado a ordem.
        update_order(
            link_id,
            "UNKNOWN",
            details=str(exc),
        )
        log_event(
            f"Resultado da ordem desconhecido: {symbol} {side}. "
            "Consultar a exchange antes de reenviar.",
            "ERROR",
        )
        raise


def get_order_status(symbol, order_id=None, order_link_id=None):
    params = {
        "category": "spot",
        "symbol": symbol,
    }

    if order_id:
        params["orderId"] = order_id
    elif order_link_id:
        params["orderLinkId"] = order_link_id
    else:
        raise ValueError("Informe orderId ou orderLinkId.")

    result = bybit_call(client.get_open_orders, **params)
    rows = result.get("list", [])

    if not rows:
        result = bybit_call(client.get_order_history, **params)
        rows = result.get("list", [])

    if not rows:
        return None

    return rows[0]


# ============================================================
# MERCADO E INDICADORES
# ============================================================

@st.cache_data(ttl=60)
def get_market_data(ticker):
    df = yf.Ticker(ticker).history(
        period="6mo",
        interval="1d",
        auto_adjust=True,
    )

    if df.empty:
        return None

    df = df[["Close"]].rename(
        columns={"Close": "price"}
    ).dropna()

    delta = df["price"].diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    avg_loss = losses.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    df.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100
    df.loc[(avg_loss == 0) & (avg_gain == 0), "rsi"] = 50

    df["rsi"] = df["rsi"].fillna(50)
    df["ema20"] = df["price"].ewm(
        span=20,
        adjust=False,
    ).mean()

    return df.dropna()


# ============================================================
# MOTOR DE SINAIS
# ============================================================

def save_signal(symbol, candle_time, rsi, ema, price, signal):
    with db() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO signals(
                symbol, candle_time, rsi, ema, price,
                signal, created_at
            ) VALUES(?,?,?,?,?,?,?)
        """, (
            symbol,
            str(candle_time),
            float(rsi),
            float(ema),
            float(price),
            signal,
            datetime.now(timezone.utc).isoformat(),
        ))
        return cursor.rowcount == 1


def get_recent_signals(limit=100):
    with db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def run_strategy_cycle(symbol, ticker, allow_real_orders):
    """
    Avalia o último candle diário disponível.
    Yahoo Finance é usado para indicadores; antes de negociar,
    os dados precisam ser verificados e reconciliados com a Bybit.
    """

    df = get_market_data(ticker)

    if df is None or len(df) < 30:
        log_event(f"Dados insuficientes para {symbol}", "WARNING")
        return

    # Exclui o candle diário mais recente, que pode estar aberto.
    candle = df.iloc[-2]
    candle_time = df.index[-2].isoformat()

    price = float(candle["price"])
    rsi = float(candle["rsi"])
    ema = float(candle["ema20"])

    position = get_position(symbol)
    qty = Decimal(position["qty"]) if position else Decimal("0")

    signal = "HOLD"

    if qty == 0 and rsi <= RSI_BUY and price > ema:
        signal = "BUY"
    elif qty > 0 and rsi >= RSI_SELL:
        signal = "SELL"

    inserted = save_signal(
        symbol, candle_time, rsi, ema, price, signal
    )

    # Não processa novamente o mesmo candle.
    if not inserted:
        return

    log_event(
        f"{symbol}: sinal {signal}; RSI={rsi:.2f}; "
        f"EMA20={ema:.4f}; preço={price:.4f}"
    )

    if signal == "HOLD":
        return

    telegram(
        f"Crypto Bot AI — Sinal {signal}\n"
        f"Ativo: {symbol}\nRSI: {rsi:.2f}\n"
        f"EMA20: {ema:.4f}\nPreço de referência: {price:.4f}"
    )

    # Modo seguro por padrão.
    if not allow_real_orders:
        return

    if TESTNET is False and not LIVE_ENABLED:
        raise RuntimeError(
            "Negociação real não habilitada em secrets.toml."
        )

    if client is None:
        raise RuntimeError("Cliente da Bybit não configurado.")

    instrument = get_instrument(symbol)

    if instrument["status"] != "Trading":
        raise RuntimeError(f"{symbol} não está disponível para negociação.")

    if signal == "BUY":
        usdt = get_balance("USDT")

        if usdt["available"] < BUY_AMOUNT_USDT:
            raise RuntimeError("Saldo USDT insuficiente.")

        if BUY_AMOUNT_USDT < instrument["min_amount"]:
            raise RuntimeError(
                f"Compra de 6 USDT inferior ao mínimo de "
                f"{instrument['min_amount']} USDT."
            )

        # Compra usando 6 USDT como moeda de cotação.
        submit_spot_order(
            symbol,
            "Buy",
            BUY_AMOUNT_USDT,
            quote_amount=True,
        )

    elif signal == "SELL":
        if not position or qty <= 0:
            return

        base_balance = get_balance(instrument["base"])
        sell_qty = round_down(qty, instrument["qty_step"])

        if sell_qty < instrument["min_qty"]:
            raise RuntimeError(
                "Quantidade controlada pelo robô abaixo do mínimo."
            )

        if base_balance["available"] < sell_qty:
            raise RuntimeError(
                "Saldo disponível inferior à quantidade controlada. "
                "Reconciliação manual necessária."
            )

        submit_spot_order(
            symbol,
            "Sell",
            sell_qty,
            quote_amount=False,
        )


# ============================================================
# INTERFACE
# ============================================================

st.title("🤖 Crypto Bot AI")
st.caption("Bybit Spot | BTC • ETH • SOL")

if TESTNET:
    st.info("Ambiente: TESTNET — ordens de teste.")
else:
    st.warning("Ambiente: PRODUÇÃO — conta real da Bybit.")

if not API_KEY or not API_SECRET:
    st.warning(
        "Configure BYBIT_API_KEY e BYBIT_SECRET_KEY em "
        ".streamlit/secrets.toml para consultar a conta."
    )

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Ambiente", ENVIRONMENT)

with col_b:
    st.metric(
        "Negociação real",
        "Habilitada na configuração" if LIVE_ENABLED else "Desativada",
    )

with col_c:
    st.metric("Compra padrão", "6 USDT")

st.divider()

allow_real = False

if not TESTNET and LIVE_ENABLED:
    allow_real = st.checkbox(
        "Confirmo que desejo permitir ordens reais automáticas "
        "quando todos os controles forem aprovados.",
        value=False,
    )

if st.button("Executar um ciclo de análise", type="primary"):
    for name, item in ASSETS.items():
        try:
            run_strategy_cycle(
                item["symbol"],
                item["ticker"],
                allow_real_orders=allow_real,
            )
        except Exception as exc:
            log_event(
                f"Falha em {item['symbol']}: {exc}",
                "ERROR",
            )
            st.error(f"{name}: {exc}")

    st.success("Ciclo de análise concluído. Consulte os registros abaixo.")

tabs = st.tabs([
    "Bitcoin (BTC)",
    "Ethereum (ETH)",
    "Solana (SOL)",
])

for (name, item), tab in zip(ASSETS.items(), tabs):
    with tab:
        st.subheader(name)

        try:
            df = get_market_data(item["ticker"])

            if df is None or df.empty:
                st.warning("Dados de mercado indisponíveis.")
                continue

            last = df.iloc[-1]
            previous = df.iloc[-2]

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Preço de referência",
                f"${last['price']:,.2f}",
                f"{(last['price'] / previous['price'] - 1) * 100:+.2f}%",
            )

            col2.metric("RSI 14", f"{last['rsi']:.2f}")
            col3.metric("EMA 20", f"${last['ema20']:,.2f}")

            st.line_chart(df[["price", "ema20"]])

            if client is not None:
                try:
                    base = item["symbol"].replace("USDT", "")
                    usdt = get_balance("USDT")
                    asset = get_balance(base)

                    b1, b2 = st.columns(2)
                    b1.metric("Saldo disponível USDT", f"{usdt['available']}")
                    b2.metric(
                        f"Saldo disponível {base}",
                        f"{asset['available']}",
                    )
                except Exception as exc:
                    st.warning(f"Não foi possível consultar saldo: {exc}")

        except Exception as exc:
            st.error(f"Falha ao carregar painel: {exc}")

st.divider()

st.subheader("📋 Sinais recentes")
signals = get_recent_signals()
if signals.empty:
    st.info("Nenhum sinal registrado.")
else:
    st.dataframe(signals, use_container_width=True, hide_index=True)

st.subheader("📑 Ordens registradas")
orders = get_orders()
if orders.empty:
    st.info("Nenhuma ordem registrada.")
else:
    st.dataframe(orders, use_container_width=True, hide_index=True)

st.subheader("🛠️ Eventos do sistema")
events = get_events()
if events.empty:
    st.info("Nenhum evento registrado.")
else:
    st.dataframe(events, use_container_width=True, hide_index=True)

st.caption(
    "Dados do Yahoo Finance são referências externas. "
    "Uma ordem enviada não equivale a uma ordem executada. "
    "Confirme execuções e reconcilie posições antes de habilitar "
    "a negociação real."
)
