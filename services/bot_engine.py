from services.trend_engine import tf_map_on_trend_values
from services.df_klines import fetch_df_klines
from config import QTY_DEFAULT, TRADE_BOT

# -------- Helper: get current position --------
def get_current_position(client, symbol):
    """
    Returns the current open position amount for a symbol.
    Positive = LONG, Negative = SHORT, 0 = No position
    """

def execute_single_trade(client,symbol, quantity=QTY_DEFAULT):
    """
    Executes one trade per symbol:
    - Uses global tf_match and atr_strength
    - Only trade if ATR is not low
    - Only one active position at a time
    - Adds trailing stop
    """
   