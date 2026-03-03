import os
import pandas as pd
import numpy as np

def get_market_state(Client, symbol="BTCUSDT",
                            ema_period=9,
                            volume_period=14,
                            volume_threshold=1.0,
                            limit_5m=200,
                            limit_15m=200):
    """
    Returns 'trending' or 'choppy' for 15–30 min BTC scalp using volume instead of ATR.
    
    Logic:
    - 5m EMA‑9 slope + price vs VWAP → short-term direction
    - 15m volume spike → trending move detection
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

    def volume_spike(df, period):
        df["vol_ma"] = df["volume"].rolling(period).mean()
        ratio = df["volume"].iloc[-1] / df["vol_ma"].iloc[-1]
        df.drop("vol_ma", axis=1, inplace=True)
        return ratio

    # -------------------------------
    # Fetch data
    # -------------------------------
    df_5m = fetch_klines(Client.KLINE_INTERVAL_5MINUTE, limit_5m)
    df_15m = fetch_klines(Client.KLINE_INTERVAL_15MINUTE, limit_15m)

    # 5m micro trend
    ema_slope_5m = ema_slope(df_5m.copy())
    price_vs_vwap_5m = vwap_position(df_5m.copy())

    # 15m volume spike
    vol_ratio_15m = volume_spike(df_15m.copy(), volume_period)

    # -------------------------------
    # Decision logic
    # -------------------------------
    if vol_ratio_15m > volume_threshold and ema_slope_5m > 0 and price_vs_vwap_5m == "above":
        return "trending"
    else:
        return "choppy"

# -------------------------------
# Example usage
# -------------------------------
# print(btc_market_state_volume())