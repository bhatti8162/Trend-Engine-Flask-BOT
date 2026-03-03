import os
import pandas as pd
import numpy as np

def get_market_state(Client, symbol="BTCUSDT",
                     ema_period=9,
                     atr_period=14,
                     atr_threshold_15m=0.004,
                     limit_5m=200,
                     limit_15m=200):
    """
    Returns 'trending' or 'choppy' for 15–30 min BTC scalp.
    
    Logic:
    - 5m EMA‑9 slope and price vs VWAP → short-term direction
    - 15m ATR → detect actual choppiness
    """

    client = Client
    # -------------------------------
    # Helper to fetch candles
    # -------------------------------
    def fetch_klines(interval, limit):
        raw = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw, columns=[
            "timestamp","open","high","low","close","volume",
            "close_time","quote_asset_volume","trades",
            "taker_buy_base","taker_buy_quote","ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        return df[["timestamp","open","high","low","close","volume"]]

    # -------------------------------
    # Indicators
    # -------------------------------
    def atr_ratio(df):
        df["tr"] = df[["high","low","close"]].apply(
            lambda r: max(r["high"]-r["low"], abs(r["high"]-r["close"]), abs(r["low"]-r["close"])),
            axis=1
        )
        df["atr"] = df["tr"].rolling(atr_period).mean()
        ratio = df["atr"].iloc[-1] / df["close"].iloc[-1]
        df.drop(["tr","atr"], axis=1, inplace=True)
        return ratio

    def ema_slope(df):
        df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()
        slope = df["ema"].iloc[-1] - df["ema"].iloc[-2]
        df.drop(["ema"], axis=1, inplace=True)
        return slope

    def vwap_position(df):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date  # intraday grouping

        vwap = df.groupby('date').apply(
            lambda x: (x['close'] * x['volume']).cumsum() / x['volume'].cumsum()
        ).reset_index(level=0, drop=True)

        pos = 'above' if df['close'].iloc[-1] > vwap.iloc[-1] else 'below'
        return pos

    # -------------------------------
    # Fetch data
    # -------------------------------
    df_5m = fetch_klines(Client.KLINE_INTERVAL_5MINUTE, limit_5m)
    df_15m = fetch_klines(Client.KLINE_INTERVAL_15MINUTE, limit_15m)

    # 5m micro trend
    ema_slope_5m = ema_slope(df_5m.copy())
    price_vs_vwap_5m = vwap_position(df_5m.copy())

    # 15m choppiness
    atr_ratio_15m = atr_ratio(df_15m.copy())

    # -------------------------------
    # Decision logic
    # -------------------------------
    if atr_ratio_15m > atr_threshold_15m and ema_slope_5m > 0 and price_vs_vwap_5m == "above":
        return "trending"
    else:
        return "choppy"

# -------------------------------
# Example usage
# -------------------------------
# print(btc_market_state())