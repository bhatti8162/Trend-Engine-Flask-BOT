from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from config import SYMBOL_DEFAULT

from services.binance_service import get_binance_client
from services.trend_engine import tf_map_on_trend_values
from services.indicator_counter import get_indicator_counts
from services.prediction_h1 import forecast_1h_demand_supply_color
from services.market_state import get_market_state
from services.last_change import get_change
from services.color_detection import get_candle_colors


# -----------------------------
# Binance Client
# -----------------------------
client = get_binance_client()

if client:
    print("Binance client authenticated successfully!")
else:
    print("Failed to authenticate Binance client.")


# -----------------------------
# Symbol Validation
# -----------------------------
def is_symbol_available(client, symbol: str):
    try:
        info = client.futures_exchange_info()
        symbols = [s["symbol"] for s in info["symbols"]]
        return symbol.upper() in symbols
    except Exception as e:
        print("Symbol check error:", e)
        return False


# -----------------------------
# Trend Engine Wrapper
# -----------------------------
def check_trend_engine(symbol):

        (
            times,
            symbol,
            price_cache,
            trend_map,
            ema_trend_map,
            atr_strength_map,
            adx_strength_map,
            rsi_strength_map,
            tf_match,
            new_trend
        ) = tf_map_on_trend_values(client, symbol)

        trade_decision = get_indicator_counts(
            trend_map,
            ema_trend_map,
            atr_strength_map,
            adx_strength_map,
            rsi_strength_map
        )

        # change Chakcer
        h1_change, d1_change = get_change(symbol[:-4])
        btc_h1_change, btc_d1_change = get_change()

        # candle color detection 
        colors = get_candle_colors(client)
        predicted_color_h1 = forecast_1h_demand_supply_color(client)
        market_state = get_market_state(client)

        return {
            "times": times,
            "symbol": symbol,
            "market_state": str(market_state).upper(),
            "predicted_color_h1": str(predicted_color_h1).upper(),
            "btc_h1_change": f"{btc_h1_change}%",
            "btc_d1_change": f"{btc_d1_change}%",
            "price": round(price_cache, 6) if price_cache else None,
            "trends": trend_map,
            "colors" : colors,
            "atr_strength": atr_strength_map,
            "adx_strength": adx_strength_map,
            "rsi_strength": rsi_strength_map,
            "ema25_strength": ema_trend_map,
            "trade_decision": f"{trade_decision}",
            "tf_match": tf_match
        }
        

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)


# -----------------------------
# API Route
# -----------------------------
@app.route("/api/trend")
def trend_api():
    symbol = request.args.get("symbol", SYMBOL_DEFAULT).upper()

    # Validate client first
    if not client:
        return jsonify({
            "error": "Binance client not connected"
        })

    # Validate symbol
    if not is_symbol_available(client, symbol):
        return jsonify({
            "symbol": symbol,
            "error": "Symbol not available",
            "values": None
        })

    data = check_trend_engine(symbol)

    # If engine failed, return early
    if "error" in data:
        return jsonify(data)

    return jsonify(data)


# -----------------------------
# Home Route
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)