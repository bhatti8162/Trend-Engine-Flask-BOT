def get_indicator_counts(
    trend_map,
    ema_trend_map,
    vwap_trend_map,
    atr_map,
    adx_map,
    rsi_map
):
    """
    Counts bullish and bearish indicators and returns a single summary string.
    """

    tf_weights = {"1h": 2.0, "15m": 1.0, "5m": 0.5, "1m": 0.2}

    bullish_count = 0
    bearish_count = 0

    # ---------- STRUCTURE: Trend + EMA + VWAP ----------
    for tf in tf_weights:
        t = trend_map.get(tf)
        e = ema_trend_map.get(tf)
        v = vwap_trend_map.get(tf)

        bullish_count += sum([
            t == "BULLISH",
            e == "UP",
            v == "ABOVE"
        ])

        bearish_count += sum([
            t == "BEARISH",
            e == "DOWN",
            v == "BELOW"
        ])

    # # ---------- TREND STRENGTH: ADX ----------
    # for tf, (_, val) in adx_map.items():
    #     if val >= 30:
    #         bullish_count += 1
    #     elif val < 20:
    #         bearish_count += 1

    # # ---------- VOLATILITY: ATR ----------
    # for tf, (state, _) in atr_map.items():
    #     if state == "HIGH":
    #         bullish_count += 1
    #     elif state == "LOW":
    #         bearish_count += 1

    # ---------- MOMENTUM EXTREME: RSI ----------
    for tf, (_, val) in rsi_map.items():
        if val >= 70:
            bearish_count += 1
        elif val <= 30:
            bullish_count += 1

    return f"Bullish Indicators: <span class='green' > {bullish_count}</span> | Bearish Indicators:  <span class='red'> {bearish_count} </span>"