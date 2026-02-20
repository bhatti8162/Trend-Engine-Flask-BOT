from services.trend_engine import tf_map_on_trend_values
from services.df_klines import fetch_df_klines
from config import QTY_DEFAULT, TRADE_BOT

# -------- Helper: get current position --------
def get_current_position(client, symbol):
    """
    Returns the current open position amount for a symbol.
    Positive = LONG, Negative = SHORT, 0 = No position
    """
    try:
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            amt = float(pos["positionAmt"])
            if amt != 0:
                return amt
        return 0.0
    except Exception as e:
        print(f"Error fetching position for {symbol}: {e}")
        return 0.0


def execute_single_trade(client,symbol, quantity=QTY_DEFAULT):
    """
    Executes one trade per symbol:
    - Uses global tf_match and atr_strength
    - Only trade if ATR is not low
    - Only one active position at a time
    - Adds trailing stop
    """
    times, symbol, price_cache,trend_map,atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend = tf_map_on_trend_values(client,symbol)

    # print(f"TRADE_BOT:{TRADE_BOT} tf_match:{tf_match} new_trend:{new_trend} ATR:{atr_strength_map['15m']} ADX:{adx_strength_map['15m']}  xxxxxxXXXXXXXXXXXXXXxxxxx")
    
    if TRADE_BOT != "on":
        return "TRADEBOT = Off"

# -------- Summary Engine: single trade only --------

def trade_summary_single(client, symbol, tf_match):
    """
    Returns a detailed summary of current position and PnL for the symbol.
    """
    try:
        # Current Position
        position_amt = get_current_position(symbol)
        position_type = "NONE"
        entry_price = 0.0

        if position_amt > 0:
            position_type = "LONG"
        elif position_amt < 0:
            position_type = "SHORT"

        # Position Details
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            amt = float(pos["positionAmt"])
            if amt != 0:
                entry_price = float(pos["entryPrice"])
                break

        # Current Price
        df_1m = fetch_df_klines(client, symbol, "1m")
        current_price = float(df_1m['close'].iloc[-1]) if df_1m is not None else 0.0

        # PnL Calculation
        pnl = 0.0
        if position_amt != 0:
            if position_type == "LONG":
                pnl = (current_price - entry_price) * abs(position_amt)
            elif position_type == "SHORT":
                pnl = (entry_price - current_price) * abs(position_amt)

        # Account Balance
        balance_info = client.futures_account_balance()
        wallet_balance = 0.0
        for b in balance_info:
            if b['asset'] == 'USDT':
                wallet_balance = float(b['balance'])
                break

        # Return Summary
        return {
            "symbol": symbol,
            "signal": tf_match,
            "current_position": position_type,
            "position_size": abs(position_amt),
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(pnl, 2),
            "wallet_balance": round(wallet_balance, 2)
        }

    except Exception as e:
        return {"error": str(e)}

