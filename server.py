from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import OrderedDict
import os

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

TRADE_BOT = "on"

SYMBOL_DEFAULT = "BTCUSDT"
QTY_DEFAULT = 0.001
MA_FAST = 50
MA_SLOW = 100
LIMIT = 200
TIMEFRAMES = ["15m", "5m", "1m"]

# Use Testnet safely
client = Client(API_KEY, API_SECRET)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

# ==========================================


# -------- Helper Functions --------
def utc_now():
    return datetime.now(timezone.utc)


def format_time(dt, tz_name):
    local_time = dt.astimezone(ZoneInfo(tz_name))

    if tz_name.upper() == "UTC":
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return local_time.strftime("%I:%M:%S %p")


def fetch_klines(symbol, interval):
    try:
        klines = client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=LIMIT
        )

        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'trades',
            'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])

        # FIX: convert all needed columns to float
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype(float)

        df['close_time'] = pd.to_datetime(
            df['close_time'], unit='ms', utc=True
        )

        df['ma50'] = df['close'].rolling(MA_FAST).mean()
        df['ma100'] = df['close'].rolling(MA_SLOW).mean()

        return df

    except BinanceAPIException as e:
        print("Binance API Error:", e)
        return None
    except Exception as e:
        print("Unexpected Error:", e)
        return None


def calculate_atr(df, period=14):
    df['high-low'] = df['high'] - df['low']
    df['high-close'] = (df['high'] - df['close'].shift()).abs()
    df['low-close'] = (df['low'] - df['close'].shift()).abs()

    df['tr'] = df[['high-low', 'high-close', 'low-close']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()

    return df


def get_trend_strength(df, atr_period=14):

    if df is None or len(df) < MA_SLOW:
        return None, "UNKNOWN"

    df = calculate_atr(df, period=atr_period)
    last = df.iloc[-1]

    if pd.isna(last['ma50']) or pd.isna(last['ma100']) or pd.isna(last['atr']):
        return None, "UNKNOWN"

    atr_percent = (last['atr'] / last['close']) * 100

    if atr_percent < 1:
        volatility = "LOW"
    elif atr_percent < 3:
        volatility = "MEDIUM"
    else:
        volatility = "HIGH"

    if last['ma50'] > last['ma100']:
        return "BULLISH", volatility
    elif last['ma50'] < last['ma100']:
        return "BEARISH", volatility

    return None, volatility


# -------- Core Engine --------
def get_signal_values(symbol):
    trend_map = OrderedDict()
    strength_map = OrderedDict()

    price_cache = None

    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)

        if df is None:
            trend_map[tf] = None
            strength_map[tf] = "ERROR"
            continue

        trend, strength = get_trend_strength(df)
        trend_map[tf] = trend
        strength_map[tf] = strength

        # Cache 1m price
        if tf == "1m":
            price_cache = float(df.iloc[-1]['close'])

    # Multi-TF Alignment
    if all(v == "BULLISH" for v in trend_map.values()):
        tf_match = "STRONG_BULLISH"
    elif all(v == "BEARISH" for v in trend_map.values()):
        tf_match = "STRONG_BEARISH"
    else:
        tf_match = None

    now = utc_now()
    times = OrderedDict([
        ("UTC", format_time(now, "UTC")),
        ("PK", format_time(now, "Asia/Karachi")),
        ("London", format_time(now, "Europe/London")),
        ("New_York", format_time(now, "America/New_York")),
        ("Tokyo", format_time(now, "Asia/Tokyo"))
    ])
    return times, symbol, price_cache, trend_map, strength_map, tf_match


def check_trend_engine(symbol):
    times, symbol, price_cache,trend_map,strength_map, tf_match = get_signal_values(symbol)

    return {
        "times": times,
        "symbol": symbol,
        "price": round(price_cache, 2) if price_cache else None,
        "trends": trend_map,
        "atr_strength": strength_map,
        "tf_match": tf_match
    }

# -------- Trading Engine: single trade only --------
TRAILING_STOP_PERCENT = 0.5  # Trailing stop % for Binance

# -------- Helper: get current position --------
def get_current_position(symbol):
    """
    Returns the current open position amount for a symbol.
    Positive = LONG, Negative = SHORT, 0 = No position
    """
    try:
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            amt = float(pos["positionAmt"])
            if amt != 0:
                return amt
        return 0.0
    except Exception as e:
        print(f"Error fetching position for {symbol}: {e}")
        return 0.0


def execute_single_trade(symbol, quantity=QTY_DEFAULT):
    """
    Executes one trade per symbol:
    - Uses global tf_match and atr_strength
    - Only trade if ATR is not low
    - Only one active position at a time
    - Adds trailing stop
    """
    times, symbol, price_cache,trend_map,strength_map, tf_match = get_signal_values(symbol)

    print(f"{tf_match} {strength_map['1m']} xxxxxxxxxxxxxxx")
    if TRADE_BOT != "on":
        return "TRADE_BOT = OFF"

    try:
        # Get current position
        position_amt = get_current_position(symbol)

        # ---- ATR Filter ----
        atr_strength = strength_map['1m']
        if atr_strength == "LOW":  # adjust threshold
            return f"ATR too ({atr_strength}), skipping trade"

        # ---- STRONG BULLISH ----
        if tf_match == "STRONG_BULLISH":
            # Already in LONG? skip duplicate
            if position_amt > 0:
                return "Already in LONG, skipping duplicate"

            # Close SHORT if any
            if position_amt < 0:
                client.futures_create_order(
                    symbol=symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=abs(position_amt)
                )

            # Open LONG
            client.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quantity=quantity
            )

            # Add trailing stop
            client.futures_create_order(
                symbol=symbol,
                side="SELL",
                type="TRAILING_STOP_MARKET",
                quantity=quantity,
                callbackRate=TRAILING_STOP_PERCENT,
                reduceOnly=True
            )

            return "Opened LONG with trailing stop"

        # ---- STRONG BEARISH ----
        elif tf_match == "STRONG_BEARISH":
            # Already in SHORT? skip duplicate
            if position_amt < 0:
                return "Already in SHORT, skipping duplicate"

            # Close LONG if any
            if position_amt > 0:
                client.futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=abs(position_amt)
                )

            # Open SHORT
            client.futures_create_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=quantity
            )

            # Add trailing stop
            client.futures_create_order(
                symbol=symbol,
                side="BUY",
                type="TRAILING_STOP_MARKET",
                quantity=quantity,
                callbackRate=TRAILING_STOP_PERCENT,
                reduceOnly=True
            )

            return "Opened SHORT with trailing stop"

        # ---- NO ALIGNMENT / CLOSE POSITIONS ----
        else:
            if position_amt > 0:
                client.futures_create_order(
                    symbol=symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=abs(position_amt)
                )
                return "Closed LONG"

            elif position_amt < 0:
                client.futures_create_order(
                    symbol=symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=abs(position_amt)
                )
                return "Closed SHORT"

            else:
                return "No position, nothing to do"

    except Exception as e:
        return f"Trade Error: {str(e)}"

# -------- Summary Engine: single trade only --------

def trade_summary_single(symbol, tf_match):
    """
    Returns a detailed summary of current position and PnL for the symbol.
    """
    try:
        # ------------------------
        # 1️⃣ Current Position
        # ------------------------
        position_amt = get_current_position(symbol)
        position_type = "NONE"
        entry_price = 0.0

        if position_amt > 0:
            position_type = "LONG"
        elif position_amt < 0:
            position_type = "SHORT"

        # ------------------------
        # 2️⃣ Position Details
        # ------------------------
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            amt = float(pos["positionAmt"])
            if amt != 0:
                entry_price = float(pos["entryPrice"])
                break

        # ------------------------
        # 3️⃣ Current Price
        # ------------------------
        df_1m = fetch_klines(symbol, "1m")
        current_price = float(df_1m['close'].iloc[-1]) if df_1m is not None else 0.0

        # ------------------------
        # 4️⃣ PnL Calculation
        # ------------------------
        pnl = 0.0
        if position_amt != 0:
            if position_type == "LONG":
                pnl = (current_price - entry_price) * abs(position_amt)
            elif position_type == "SHORT":
                pnl = (entry_price - current_price) * abs(position_amt)

        # ------------------------
        # 5️⃣ Account Balance
        # ------------------------
        balance_info = client.futures_account_balance()
        wallet_balance = 0.0
        for b in balance_info:
            if b['asset'] == 'USDT':
                wallet_balance = float(b['balance'])
                break

        # ------------------------
        # 6️⃣ Return Summary
        # ------------------------
        return {
            "symbol": symbol,
            "signal": tf_match,
            "current_position": position_type,
            "position_size": abs(position_amt),
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(pnl, 2),
            "wallet_balance": round(wallet_balance, 2)
        }

    except Exception as e:
        return {"error": str(e)}



# -------- API Routes --------
@app.route("/api/trend")
def trend_api():
    symbol = request.args.get("symbol", SYMBOL_DEFAULT)

    data = check_trend_engine(symbol)

    trade_action = execute_single_trade(symbol, data["tf_match"])
    summary = trade_summary_single(symbol, data["tf_match"])

    data["trade_action"] = trade_action
    data["summary"] = summary

    return jsonify(data)


@app.route("/")
def home():
    return render_template("index.html")


# -------- Run App --------
if __name__ == "__main__":
    app.run(debug=True)
