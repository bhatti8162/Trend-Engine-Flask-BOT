import pandas as pd
import numpy as np

def scalp_demand_supply_momentum(
    client,
    symbol="BTCUSDT",
    interval="5m",
    higher_tf="1h",
    ema_period=25
):
    """
    5m momentum-based demand/supply detector.
    Designed for trades lasting ~15–30 minutes.
    - Uses last closed candle as impulse
    - EMA slope confirmation
    - 1H trend alignment
    - ATR adaptive buffer
    Returns: (demand: bool, supply: bool)
    """

    # =========================
    # Fetch 5m candles
    # =========================
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])
    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)

    current_price = df["close"].iloc[-1]

    # =========================
    # EMA & Slope
    # =========================
    df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()
    ema_now = df["ema"].iloc[-1]
    ema_prev = df["ema"].iloc[-2]
    ema_slope_up = ema_now > ema_prev
    ema_slope_down = ema_now < ema_prev

    # =========================
    # ATR for adaptive threshold
    # =========================
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(abs(df["high"] - df["close"].shift()), abs(df["low"] - df["close"].shift()))
    )
    df["atr"] = df["tr"].rolling(14).mean()
    atr = df["atr"].iloc[-1]

    # =========================
    # Detect last impulse candle
    # =========================
    last = df.iloc[-2]  # last closed candle
    body = abs(last["close"] - last["open"])
    avg_vol = df["volume"].rolling(20).mean().iloc[-2]

    strong_bull = last["close"] > last["open"] and body > atr and last["volume"] > avg_vol
    strong_bear = last["close"] < last["open"] and body > atr and last["volume"] > avg_vol
    midpoint = (last["high"] + last["low"]) / 2

    # =========================
    # 1H Trend Filter
    # =========================
    htf_klines = client.get_klines(symbol=symbol, interval=higher_tf, limit=ema_period + 5)
    df_htf = pd.DataFrame(htf_klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])
    df_htf["close"] = df_htf["close"].astype(float)
    df_htf["ema"] = df_htf["close"].ewm(span=ema_period, adjust=False).mean()
    htf_price = df_htf["close"].iloc[-1]
    htf_ema = df_htf["ema"].iloc[-1]
    htf_bullish = htf_price > htf_ema
    htf_bearish = htf_price < htf_ema

    # =========================
    # Final Demand/Supply Logic
    # =========================
    demand = strong_bull and current_price > midpoint and current_price > ema_now and ema_slope_up and htf_bullish
    supply = strong_bear and current_price < midpoint and current_price < ema_now and ema_slope_down and htf_bearish

    return bool(demand), bool(supply)