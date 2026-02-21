from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from config import SYMBOL_DEFAULT


from services.binance_service import get_binance_client
from services.bot_engine import execute_single_trade, trade_summary_single
from services.trend_engine import tf_map_on_trend_values, get_decision_on_signal
from services.h_l_sessions import get_all_session_high_low
from services.trailing_engine import long_trailing_atr, short_trailing_atr


client = get_binance_client()
if client:
    print("Binance client authenticated successfully!")
else:
    print(client)
    print("Failed to authenticate Binance client.")


def check_trend_engine(symbol):

    # TimeFrames Mappings
    times, symbol, price_cache, trend_map, ema_trend_map, vwap_trend_map, atr_strength_map, adx_strength_map, rsi_strength_map, tf_match, new_trend= tf_map_on_trend_values(client,symbol)

    # Final Trade Decisions
    trade_decision = get_decision_on_signal(trend_map, atr_strength_map, adx_strength_map, rsi_strength_map)

    # Example usage
    btc_sessions = get_all_session_high_low(client,"BTCUSDT")

    # ATR TRAIL Values
    LONG_TRAIL_STOP, is_hit_LONG = long_trailing_atr(atr_strength_map["1m"],round(price_cache))
    SHORT_TRAIL_STOP, is_hit_SHORT = short_trailing_atr(atr_strength_map["1m"],round(price_cache))

    return {
        "times": times,
        "symbol": symbol,
        "price": round(price_cache) if price_cache else None,
        "trends": trend_map,
        "atr_strength": atr_strength_map,
        "adx_strength": adx_strength_map,
        "rsi_strength": rsi_strength_map,
        "ema_strength": ema_trend_map,
        "vwap_strength": vwap_trend_map,
        "trade_decision": trade_decision,
        "ATR_TRAIL_LONG": [LONG_TRAIL_STOP, is_hit_LONG],
        "ATR_TRAIL_SHORT": [SHORT_TRAIL_STOP, is_hit_SHORT],
        "btc_sessions": btc_sessions,
        "tf_match": tf_match
    }
app = Flask(__name__)
CORS(app)

# -------- API Routes --------
@app.route("/api/trend")
def trend_api():
    symbol = request.args.get("symbol", SYMBOL_DEFAULT)

    data = check_trend_engine(symbol)

    trade_action = execute_single_trade(client, symbol, data["tf_match"])
    summary = trade_summary_single(client, symbol, data["tf_match"])

    data["trade_action"] = trade_action
    data["summary"] = summary

    return jsonify(data)


@app.route("/")
def home():
    return render_template("index.html")


# -------- Run App --------
if __name__ == "__main__":
    app.run(debug=True)
