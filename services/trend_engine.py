from services.indicator_calculator import calculate_indicators
from services.df_klines import fetch_df_klines
from config import TIMEFRAMES, MA_SLOW,MA_FAST, LIMIT

import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import OrderedDict
import os

LAST_TF_MATCH = None

LONG_TRAIL_STOP = None
SHORT_TRAIL_STOP = None

# -------- Helper Functions --------
def utc_now():
    return datetime.now(timezone.utc)


def format_time(dt, tz_name):
    local_time = dt.astimezone(ZoneInfo(tz_name))

    if tz_name.upper() == "UTC":
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return local_time.strftime("%I:%M:%S %p")

def trend_values_of_indicators(df):

    if df is None or len(df) < MA_SLOW:
        return None, "UNKNOWN", "UNKNOWN", None, None

    df = calculate_indicators(df)
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
def tf_map_on_trend_values(client,symbol):
    trend_map = OrderedDict()
    atr_strength_map = OrderedDict()
    adx_strength_map= OrderedDict()
    rsi_strength_map= OrderedDict()

    price_cache = None

    for tf in TIMEFRAMES:
        df = fetch_df_klines(client,symbol, tf)

        if df is None:
            trend_map[tf] = None
            atr_strength_map[tf] = "ERROR"
            continue

        trend, atr, adx, rsi = trend_values_of_indicators(df)
        trend_map[tf] = trend
        atr_strength_map[tf] = atr
        adx_strength_map[tf] = adx
        rsi_strength_map[tf] = rsi

        # Cache 1m price
        if tf == "1m":
            price_cache = float(df.iloc[-1]['close'])

    # Multi-TF Alignment
    if all(v == "BULLISH" for v in trend_map.values()):
        tf_match = "BULLISH"
    elif all(v == "BEARISH" for v in trend_map.values()):
        tf_match = "BEARISH"
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