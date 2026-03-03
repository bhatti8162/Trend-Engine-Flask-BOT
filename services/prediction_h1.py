import pandas as pd
import numpy as np

def forecast_1h_demand_supply_color(client, symbol="BTCUSDT", ema_period=25, atr_period=14, lookback=3):
    """
    Smarter 1H demand/supply + next candle color prediction
    - Uses last `lookback` candles for momentum buildup
    Returns:
    {
        '1h_demand': bool,
        '1h_supply': bool,
        '1h_predicted_color': str  # 'green' or 'red'
    }
    """

    # ----------------------------
    # Fetch 1H candles
    # ----------------------------
    klines = client.get_klines(symbol=symbol, interval="1h", limit=ema_period + 20)
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)

    # ----------------------------
    # EMA & ATR
    # ----------------------------
    df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(abs(df["high"] - df["close"].shift()), abs(df["low"] - df["close"].shift()))
    )
    df["atr"] = df["tr"].rolling(atr_period).mean()

    ema_now = df["ema"].iloc[-1]
    ema_prev = df["ema"].iloc[-2]
    ema_slope_up = ema_now > ema_prev
    ema_slope_down = ema_now < ema_prev
    price_now = df["close"].iloc[-1]

    # ----------------------------
    # Look at last `lookback` candles
    # ----------------------------
    recent = df.iloc[-lookback-1:-1]  # last `lookback` closed candles
    bullish_count = ((recent["close"] > recent["open"]) & ((recent["close"] - recent["open"]) > recent["atr"])).sum()
    bearish_count = ((recent["close"] < recent["open"]) & ((recent["open"] - recent["close"]) > recent["atr"])).sum()

    last = df.iloc[-2]
    midpoint = (last["high"] + last["low"]) / 2
    body = abs(last["close"] - last["open"])
    atr_last = last["atr"]

    # ----------------------------
    # Demand/Supply Logic
    # ----------------------------
    demand = bullish_count > bearish_count and last["close"] > midpoint and price_now > ema_now and ema_slope_up
    supply = bearish_count > bullish_count and last["close"] < midpoint and price_now < ema_now and ema_slope_down

    # ----------------------------
    # Predicted Candle Color
    # ----------------------------
    if demand:
        predicted_color = "green"
    elif supply:
        predicted_color = "red"
    else:
        # fallback: EMA slope
        predicted_color = "green" if ema_slope_up else "red"

    return predicted_color