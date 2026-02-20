from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from config import API_KEY, API_SECRET, LIMIT


# Use Testnet safely
client = Client(API_KEY, API_SECRET)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

# ==========================================


# -------- Helper Functions --------
def utc_now():
    return datetime.now(timezone.utc)


def format_time(dt, tz_name):
    local_time = dt.astimezone(ZoneInfo(tz_name))

    if tz_name.upper() == "UTC":
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return local_time.strftime("%I:%M:%S %p")


def fetch_df_klines(symbol, interval):
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


