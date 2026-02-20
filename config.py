import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL_DEFAULT = "BTCUSDT"
QTY_DEFAULT = 0.001
MA_FAST = 50
MA_SLOW = 100
LIMIT = 200
TIMEFRAMES = ["15m", "5m", "1m"]

TRADE_BOT = "off"