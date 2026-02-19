from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import OrderedDict
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

TRADE_BOT = "off"

SYMBOL_DEFAULT = "BTCUSDT"
QTY_DEFAULT = 0.001
MA_FAST = 50
MA_SLOW = 100
LIMIT = 200
TIMEFRAMES = ["15m", "5m", "1m"]

LAST_TF_MATCH = None

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


def calculate_indicators(df, period=14):
    # ----- TRUE RANGE (ATR) -----
    df['high-low'] = df['high'] - df['low']
    df['high-close'] = (df['high'] - df['close'].shift()).abs()
    df['low-close'] = (df['low'] - df['close'].shift()).abs()

    df['tr'] = df[['high-low', 'high-close', 'low-close']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()

    # ----- DIRECTIONAL MOVEMENT -----
    df['up_move'] = df['high'].diff()
    df['down_move'] = -df['low'].diff()

    df['+dm'] = df['up_move'].where(
        (df['up_move'] > df['down_move']) & (df['up_move'] > 0), 0.0
    )

    df['-dm'] = df['down_move'].where(
        (df['down_move'] > df['up_move']) & (df['down_move'] > 0), 0.0
    )

    # ----- SMOOTHED DM -----
    df['+di'] = 100 * (df['+dm'].rolling(window=period).mean() / df['atr'])
    df['-di'] = 100 * (df['-dm'].rolling(window=period).mean() / df['atr'])

    # ----- DX & ADX -----
    df['dx'] = (
        (abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])) * 100
    )

    df['adx'] = df['dx'].rolling(window=period).mean()

    # ----- RSI -----
    df['change'] = df['close'].diff()

    df['gain'] = df['change'].where(df['change'] > 0, 0.0)
    df['loss'] = -df['change'].where(df['change'] < 0, 0.0)

    avg_gain = df['gain'].rolling(window=period).mean()
    avg_loss = df['loss'].rolling(window=period).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df




def get_trend(df, atr_period=14):

    if df is None or len(df) < MA_SLOW:
        return None, "UNKNOWN", "UNKNOWN", None, None

    df = calculate_indicators(df, period=atr_period)
    last = df.iloc[-1]

    if (
        pd.isna(last['ma50']) or 
        pd.isna(last['ma100']) or 
        pd.isna(last['atr']) or
        pd.isna(last['adx']) or
        pd.isna(last['rsi'])
    ):
        return None, "UNKNOWN", "UNKNOWN", None, None

    # ----- ATR LEVEL -----
    atx_value = last['atr']
    atr_percent = ( atx_value / last['close']) * 100

    if atr_percent < 1:
        atr = "LOW"
    elif atr_percent < 3:
        atr = "MEDIUM"
    else:
        atr = "HIGH"

    # ----- ADX LEVEL -----
    adx_value = last['adx']

    if adx_value < 20:
        adx = "WEAK"
    elif adx_value < 25:
        adx = "MODERATE"
    else:
        adx = "STRONG"

    # ----- RSI LEVEL -----
    rsi_value = last['rsi']

    if rsi_value < 30:
        rsi_level = "OVERSOLD"
    elif rsi_value > 70:
        rsi_level = "OVERBOUGHT"
    else:
        rsi_level = "NEUTRAL"

    # ----- TREND -----
    if last['ma50'] > last['ma100']:
        trend = "BULLISH"
    elif last['ma50'] < last['ma100']:
        trend = "BEARISH"
    else:
        trend = None

    return trend, [atr, round(atx_value)] , [adx, round(adx_value)] , [rsi_level, round(rsi_value)] 



# -------- Core Engine --------
def get_signals_on_trend(symbol):
    trend_map = OrderedDict()
    atr_strength_map = OrderedDict()
    adx_strength_map= OrderedDict()
    rsi_strength_map= OrderedDict()

    price_cache = None

    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)

        if df is None:
            trend_map[tf] = None
            atr_strength_map[tf] = "ERROR"
            continue

        trend, atr, adx, rsi = get_trend(df)
        trend_map[tf] = trend
        atr_strength_map[tf] = atr
        adx_strength_map[tf] = adx
        rsi_strength_map[tf] = rsi

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

    # --- Only consider as new trend if it changed ---
    global LAST_TF_MATCH
    new_trend = None
    if tf_match != LAST_TF_MATCH:
        new_trend = tf_match
        LAST_TF_MATCH = tf_match  # update last trend

    now = utc_now()
    times = OrderedDict([
        ("UTC", format_time(now, "UTC")),
        ("PK", format_time(now, "Asia/Karachi")),
        ("London", format_time(now, "Europe/London")),
        ("New_York", format_time(now, "America/New_York")),
        ("Tokyo", format_time(now, "Asia/Tokyo"))
    ])
    return times, symbol, price_cache, trend_map, atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend


def get_decision_on_signal(trend_map, atr_map, adx_map, rsi_map):
    """
    Pullback continuation logic
    """

    t15 = trend_map.get("15m")
    t5  = trend_map.get("5m")
    t1  = trend_map.get("1m")

    atr15 = atr_map.get("15m")
    adx15 = adx_map.get("15m")
    rsi1  = rsi_map.get("1m")

    if not all([t15, t5, t1, atr15, adx15, rsi1]):
        return "NONE"

    atr_state, atr_value = atr15
    adx_state, adx_value = adx15
    rsi_state, rsi_value = rsi1

    # === Market must be alive ===
    if atr_state == "LOW":
        return "NONE"

    if adx_state == "WEAK" or adx_value < 20:
        return "NONE"

    # ================= LONG =================
    if t15 == "BULLISH" and t5 == "BULLISH":

        # wait for 1m pullback
        if t1 == "BEARISH" or rsi_value < 40:
            return "LONG"

    # ================= SHORT =================
    if t15 == "BEARISH" and t5 == "BEARISH":

        # wait for 1m bounce
        if t1 == "BULLISH" or rsi_value > 60:
            return "SHORT"

    return "NONE"

def check_trend_engine(symbol):
    times, symbol, price_cache,trend_map,atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend= get_signals_on_trend(symbol)

    trade_decision = get_decision_on_signal(trend_map, atr_strength_map, adx_strength_map, rsi_strength_map)
    return {
        "times": times,
        "symbol": symbol,
        "price": round(price_cache) if price_cache else None,
        "trends": trend_map,
        "atr_strength": atr_strength_map,
        "adx_strength": adx_strength_map,
        "rsi_strength": rsi_strength_map,
        "trade_decision": trade_decision,
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
    times, symbol, price_cache,trend_map,atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend = get_signals_on_trend(symbol)

    # print(f"TRADE_BOT:{TRADE_BOT} tf_match:{tf_match} new_trend:{new_trend} ATR:{atr_strength_map['15m']} ADX:{adx_strength_map['15m']}  xxxxxxXXXXXXXXXXXXXXxxxxx")
    
    if TRADE_BOT != "on":
        return "TRADEBOT = Off"

    try:
        # Get current position
        position_amt = get_current_position(symbol)

        # ---- ATR AND ADXFilter ----
        atr_strength = atr_strength_map['15m']
        adx_strength = adx_strength_map['15m']
        if atr_strength.upper() == "LOW" or adx_strength.upper() == "weak":  # adjust threshold
            return f"ATR TOO ({atr_strength}), ADX TOO ({adx_strength}), skipping trade"
        
        if new_trend == None:
            return f"Trend is old, New Trend is ({new_trend})"

        # ---- STRONG BULLISH ----
        if new_trend == "STRONG_BULLISH" and tf_match == "STRONG_BULLISH":
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
        elif new_trend  == "STRONG_BEARISH" and tf_match == "STRONG_BEARISH":
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
