import numpy as np

def calculate_indicators(
    df,
    atr_period=14,
    adx_period=14,
    rsi_period=14,
    ma50_period=50,
    ma100_period=100
):

    # ===== ATR =====
    df['high-low'] = df['high'] - df['low']
    df['high-close'] = (df['high'] - df['close'].shift()).abs()
    df['low-close'] = (df['low'] - df['close'].shift()).abs()

    df['tr'] = df[['high-low', 'high-close', 'low-close']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=atr_period).mean()

    # ===== ADX =====
    df['up_move'] = df['high'].diff()
    df['down_move'] = -df['low'].diff()

    df['+dm'] = df['up_move'].where(
        (df['up_move'] > df['down_move']) & (df['up_move'] > 0), 0.0
    )

    df['-dm'] = df['down_move'].where(
        (df['down_move'] > df['up_move']) & (df['down_move'] > 0), 0.0
    )

    plus_di = 100 * (df['+dm'].rolling(window=adx_period).mean() / df['atr'])
    minus_di = 100 * (df['-dm'].rolling(window=adx_period).mean() / df['atr'])

    df['dx'] = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    df['adx'] = df['dx'].rolling(window=adx_period).mean()

    # ===== RSI =====
    df['change'] = df['close'].diff()
    df['gain'] = df['change'].where(df['change'] > 0, 0.0)
    df['loss'] = -df['change'].where(df['change'] < 0, 0.0)

    avg_gain = df['gain'].rolling(window=rsi_period).mean()
    avg_loss = df['loss'].rolling(window=rsi_period).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ===== Moving Averages =====
    df['ma50'] = df['close'].rolling(window=ma50_period).mean()
    df['ma100'] = df['close'].rolling(window=ma100_period).mean()

    return df

    """
    Returns:
    - sl_hunt_long_level  -> strongest liquidity BELOW price
    - sl_hunt_short_level -> strongest liquidity ABOVE price
    """

    book = client.get_order_book(symbol=symbol, limit=depth)

    bids = np.array(book['bids'], dtype=float)
    asks = np.array(book['asks'], dtype=float)

    if len(bids) == 0 or len(asks) == 0:
        return None, None

    bid_price = bids[0][0]
    ask_price = asks[0][0]
    mid_price = (bid_price + ask_price) / 2

    # ----- FILTER BELOW PRICE (long stops) -----
    bid_zone = bids[
        (bids[:,0] < mid_price * (1 - min_distance_pct)) &
        (bids[:,0] > mid_price * (1 - max_distance_pct))
    ]

    # ----- FILTER ABOVE PRICE (short stops) -----
    ask_zone = asks[
        (asks[:,0] > mid_price * (1 + min_distance_pct)) &
        (asks[:,0] < mid_price * (1 + max_distance_pct))
    ]

    # If no liquidity in zone, expand search automatically
    if len(bid_zone) == 0:
        bid_zone = bids[bids[:,0] < mid_price]

    if len(ask_zone) == 0:
        ask_zone = asks[asks[:,0] > mid_price]

    # Pick strongest liquidity level (max quantity)
    strongest_bid = bid_zone[np.argmax(bid_zone[:,1])]
    strongest_ask = ask_zone[np.argmax(ask_zone[:,1])]

    sl_hunt_long_level = float(strongest_bid[0])
    sl_hunt_short_level = float(strongest_ask[0])

    return sl_hunt_long_level, sl_hunt_short_level