from binance.exceptions import BinanceAPIException, BinanceRequestException
import pandas as pd
from config import LIMIT

def fetch_df_klines(client, symbol, interval):
    try:
        klines = client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=LIMIT
        )

        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'trades',
            'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])

        # FIX: convert all needed columns to float
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype(float)

        df['close_time'] = pd.to_datetime(
            df['close_time'], unit='ms', utc=True
        )

        return df

    except BinanceAPIException as e:
        print("Binance API Error:", e)
        return None
    except Exception as e:
        print("Unexpected Error:", e)
        return None


