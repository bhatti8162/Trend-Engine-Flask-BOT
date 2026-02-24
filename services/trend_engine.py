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

    # ----- EMA TREND -----
    if last['ema_slope'] > 0:
        ema_trend = "UP"
    elif last['ema_slope'] < 0:
        ema_trend = "DOWN"
    else:
        ema_trend = "FLAT"

    # ----- VWAP TREND -----
    if last['close'] > last['vwap']:
        vwap_trend = "ABOVE"
    elif last['close'] < last['vwap']:
        vwap_trend = "BELOW"
    else:
        vwap_trend = "AT"

    # ----- TREND -----
    if last['ma50'] > last['ma100']:
        trend = "BULLISH"
    elif last['ma50'] < last['ma100']:
        trend = "BEARISH"
    else:
        trend = None

    return trend, ema_trend, vwap_trend, [atr, f"{round(atr_percent,2)}%"] , [adx, round(adx_value)] , [rsi_level, round(rsi_value)] 



# -------- Core Engine --------
def tf_map_on_trend_values(client,symbol):
    trend_map = OrderedDict()
    ema_trend_map = OrderedDict()
    vwap_trend_map = OrderedDict()
    atr_strength_map = OrderedDict()
    adx_strength_map= OrderedDict()
    rsi_strength_map= OrderedDict()

    price_cache = None

    for tf in TIMEFRAMES:
        df = fetch_df_klines(client,symbol, tf)

        if df is None:
            # trend_map[tf] = None
            # atr_strength_map[tf] = "ERROR"
            continue

        trend, ema_trend, vwap_trend, atr, adx, rsi = trend_values_of_indicators(df)
        trend_map[tf] = trend
        ema_trend_map[tf] = ema_trend
        vwap_trend_map[tf] = vwap_trend
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
        ("NewYork", format_time(now, "America/New_York")),
        ("Tokyo", format_time(now, "Asia/Tokyo"))
    ])
    return times, symbol, price_cache, trend_map, ema_trend_map, vwap_trend_map, atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend


def get_decision_on_signal(
        trend_map,
        ema_trend_map,
        vwap_trend_map,
        atr_map,
        adx_map,
        rsi_map):
    """
    Descriptive market tool with 1H ATR + ADX checks.
    Returns: one-liner description + confidence 0-10
    """

    t1h = trend_map.get("1h")
    t15 = trend_map.get("15m")
    t5  = trend_map.get("5m")

    ema1h = ema_trend_map.get("1h")
    ema15 = ema_trend_map.get("15m")

    vwap15 = vwap_trend_map.get("15m")

    atr1h = atr_map.get("1h")   # (state, value)
    adx1h = adx_map.get("1h")   # (state, value)
    rsi5  = rsi_map.get("5m")

    if not all([t1h, t15, t5, ema1h, ema15, vwap15, atr1h, adx1h, rsi5]):
        return "Insufficient data to make a decision"

    atr_state, atr_value = atr1h
    _, adx_value = adx1h
    _, rsi_value = rsi5

    description = ""
    confidence = 0

    # === 1H ATR soft filter ===
    if atr_state == "LOW":
        confidence -= 1
        atr_note = "1H Low Volatility – trade with caution"
    else:
        confidence += 1
        atr_note = ""

    # === 1H ADX trend check ===
    if adx_value < 25:
        confidence -= 2
        description = "Weak Trend – caution advised"
    else:
        confidence += 2

    # === STRONG BULLISH ===
    if (t1h == "BULLISH" and t15 == "BULLISH" and t5 == "BULLISH" and
        ema1h == "BULLISH" and ema15 == "BULLISH" and vwap15 == "ABOVE"):
        confidence += 3
        description = "Strong Bullish Continuation"

        if 40 <= rsi_value <= 55:
            confidence += 1
            description += " – Pullback Opportunity"
        elif rsi_value < 40:
            description += " – Early Pullback"
        elif rsi_value > 60:
            description += " – Late / Overextended"

        if atr_state == "LOW":
            description += f" ({atr_note})"

    # === WEAK BULLISH ===
    elif t1h == "BULLISH" and t15 == "BULLISH":
        confidence += 2
        description = "Weak Bullish – trend aligned but minor conflicts"

        if atr_state == "LOW":
            description += f" ({atr_note})"

    # === STRONG BEARISH ===
    if (t1h == "BEARISH" and t15 == "BEARISH" and t5 == "BEARISH" and
        ema1h == "BEARISH" and ema15 == "BEARISH" and vwap15 == "BELOW"):
        confidence += 3
        description = "Strong Bearish Continuation"

        if 45 <= rsi_value <= 60:
            confidence += 1
            description += " – Bounce Opportunity"
        elif rsi_value < 35:
            description += " – Early / Oversold"
        elif rsi_value > 65:
            description += " – Late / Overextended"

        if atr_state == "LOW":
            description += f" ({atr_note})"

    # === WEAK BEARISH ===
    elif t1h == "BEARISH" and t15 == "BEARISH":
        confidence += 2
        description = "Weak Bearish – trend aligned but minor conflicts"

        if atr_state == "LOW":
            description += f" ({atr_note})"

    # === SIDEWAYS / UNCLEAR ===
    if confidence <= 3:
        description = "Sideways / Unclear – avoid trading"

    return f"{description} | Confidence: {confidence}/10"