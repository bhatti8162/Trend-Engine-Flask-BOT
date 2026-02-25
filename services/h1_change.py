def get_last_hour_strength(client,symbol="BTCUSDT"):
    # Current price (futures)
    ticker = client.futures_symbol_ticker(symbol=symbol)
    current_price = float(ticker["price"])

    # Get current 1H candle (active)
    klines = client.futures_klines(
        symbol=symbol,
        interval="1h",
        limit=1
    )

    open_price = float(klines[0][1])

    percent_change = ((current_price - open_price) / open_price) * 100

    return round(percent_change, 2)