def get_candle_colors(client, symbol="BTCUSDT", timeframes=["1d","1h"], limit=1):
    """
    Returns the latest candle color for each timeframe.
    'green' = bullish, 'red' = bearish, 'doji' = neutral
    """
    candle_colors = {}
    
    for tf in timeframes:
        # fetch klines: [open_time, open, high, low, close, volume, ...]
        klines = client.get_klines(symbol=symbol, interval=tf, limit=limit)
        if not klines:
            candle_colors[tf] = None
            continue
        
        last_candle = klines[-1]
        open_price = float(last_candle[1])
        close_price = float(last_candle[4])
        
        if close_price > open_price:
            candle_colors[tf] = "GREEN"
        elif close_price < open_price:
            candle_colors[tf] = "RED"
        else:
            candle_colors[tf] = "DOJI"
    
    return candle_colors

