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

    # ===== 25 EMA =====
    df['ema21'] = df['close'].ewm(span=25, adjust=False).mean()
    df['ema_slope'] = df['ema21'].diff()

    return df

