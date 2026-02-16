from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from binance.client import Client
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import OrderedDict

app = Flask(__name__)
CORS(app)  # Enable CORS

# ================= CONFIG =================
API_KEY = "RMjOPL4EjT8v8dEJPtmpdQbUloPpMreOSQt1eqiH6KIFqJ2IYT5g0Kypxehpjie1"
API_SECRET = "H1ZLDQQR6nD5QI4F8z11PryhfMV8wIRmJdRYFwtbdChVFAr7eq3xxxCRPf0H6yKT"

SYMBOL_DEFAULT = "BTCUSDT"
TRADE_BOT = "on" 
QTY_DEFAULT = 0.001
MA_FAST = 50
MA_SLOW = 100
LIMIT = 200
TIMEFRAMES = ["15m", "5m", "1m"]

LOG_FILE = "trend_log.txt"

client = Client(API_KEY, API_SECRET)
# client.FUTURES_URL = 'https://fapi.binance.com/fapi'
client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'

last_cross_time = None
# ==========================================

# -------- Helper Functions --------
def utc_now():
    return datetime.now(timezone.utc)

def format_time(dt, tz_name):
    local_time = dt.astimezone(ZoneInfo(tz_name))
    
    if tz_name.upper() == "UTC":
        return local_time.strftime("%Y-%m-%d %H:%M:%S")   # 24-hour
    else:
        return local_time.strftime("%I:%M:%S %p")  # 12-hour with AM/PM

def fetch_klines(symbol, interval):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=LIMIT)
    df = pd.DataFrame(klines, columns=[
        'time','open','high','low','close','volume',
        'close_time','qav','trades','taker_base_vol',
        'taker_quote_vol','ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
    df['ma50'] = df['close'].rolling(MA_FAST).mean()
    df['ma100'] = df['close'].rolling(MA_SLOW).mean()
    return df

def get_trend_strength(df):
    last = df.iloc[-1]
    if pd.isna(last['ma50']) or pd.isna(last['ma100']):
        return None, 0
    distance = abs(last['ma50'] - last['ma100'])
    if last['ma50'] > last['ma100']:
        return "BULLISH", round(distance, 2)
    elif last['ma50'] < last['ma100']:
        return "BEARISH", round(distance, 2)
    return None, 0

def detect_recent_cross(df):
    global last_cross_time
    prev = df.iloc[-2]
    last = df.iloc[-1]
    if pd.isna(prev['ma50']) or pd.isna(prev['ma100']):
        return None, None
    cross_time = last['close_time']
    # Bullish Cross
    if prev['ma50'] < prev['ma100'] and last['ma50'] > last['ma100']:
        if last_cross_time != cross_time:
            last_cross_time = cross_time
            return "BULLISH_CROSS", cross_time
    # Bearish Cross
    if prev['ma50'] > prev['ma100'] and last['ma50'] < last['ma100']:
        if last_cross_time != cross_time:
            last_cross_time = cross_time
            return "BEARISH_CROSS", cross_time
    return None, None

# -------- Core Engine --------
def check_trend_engine(symbol):
    trend_map = OrderedDict((tf, None) for tf in TIMEFRAMES)
    strength_map = OrderedDict((tf, 0) for tf in TIMEFRAMES)

    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)
        trend, strength = get_trend_strength(df)
        trend_map[tf] = trend
        strength_map[tf] = strength

    # Multi-TF Alignment
    if all(v == "BULLISH" for v in trend_map.values()):
        tf_match = "STRONG_BULLISH"
    elif all(v == "BEARISH" for v in trend_map.values()):
        tf_match = "STRONG_BEARISH"
    else:
        tf_match = None

    # 1m Recent Cross
    df_1m = fetch_klines(symbol, "1m")
    cross_signal, cross_time = detect_recent_cross(df_1m)
    # Get current price (last close)
    current_price = float(df_1m.iloc[-1]['close'])

    now = utc_now()
    times = OrderedDict([
        ("UTC", format_time(now, "UTC")),
        ("PK", format_time(now, "Asia/Karachi")),
        ("London", format_time(now, "Europe/London")),
        ("New_York", format_time(now, "America/New_York")),
        ("Tokyo", format_time(now, "Asia/Tokyo"))
    ])


    return {
    "times": times,
    "symbol": symbol,
    "price": round(current_price),
    "trends": trend_map,
    "strength": strength_map,
    "tf_match": tf_match,
    "recent_cross": cross_signal,
    "cross_time": str(cross_time)
    }   


# -------- Trading Engine --------
def get_current_position(symbol):
    positions = client.futures_position_information(symbol=symbol)
    for pos in positions:
        amt = float(pos["positionAmt"])
        if amt != 0:
            return amt
    return 0.0

def execute_single_trade(symbol, tf_match, quantity=QTY_DEFAULT):
    """
    Executes one trade per symbol:
    - STRONG_BULLISH -> long
    - STRONG_BEARISH -> short
    - None or mismatch -> close any open trade
    """
    if(TRADE_BOT == "on"): 
        try:
            position_amt = get_current_position(symbol)

            # ===== STRONG BULLISH =====
            if tf_match == "STRONG_BULLISH":
                if position_amt > 0:
                    return "Already in LONG"
                if position_amt < 0:
                    # Close existing SHORT
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
                return "Opened LONG"

            # ===== STRONG BEARISH =====
            elif tf_match == "STRONG_BEARISH":
                if position_amt < 0:
                    return "Already in SHORT"
                if position_amt > 0:
                    # Close existing LONG
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
                return "Opened SHORT"

            # ===== NO ALIGNMENT =====
            else:
                if position_amt > 0:
                    client.futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        type="MARKET",
                        quantity=abs(position_amt)
                    )
                    return "Closed Position"
                elif position_amt < 0:
                    client.futures_create_order(
                        symbol=symbol,
                        side="BUY",
                        type="MARKET",
                        quantity=abs(position_amt)
                    )
                    return "Closed Position"
                else:
                    return "No position"

        except Exception as e:
            return f"Trade Error: {str(e)}"
    else:
        return "TRADE_BOT = OFF"

    
def trade_summary_single(symbol, tf_match):
    position_amt = get_current_position(symbol)
    
    if position_amt > 0:
        position_type = "LONG"
    elif position_amt < 0:
        position_type = "SHORT"
    else:
        position_type = "NONE"

    return {
        "symbol": symbol,
        "signal": tf_match,
        "current_position": position_type,
        "position_size": abs(position_amt)
    }


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
