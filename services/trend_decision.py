def get_decision_on_signal(
    trend_map,
    ema_trend_map,
    vwap_trend_map,
    atr_map,
    adx_map,
    rsi_map
):
    """
    Each indicator scored individually with weights.
    Returns: one-line description + float confidence 0-10
    """

    # Timeframe weights
    tf_weights = {"1h": 2.0, "15m": 1.0, "5m": 0.5}

    # Indicator-specific weights
    indicator_weights = {
        "trend": 1.0,
        "ema": 1.0,
        "vwap": 1.0,
        "adx": 1.5,
        "atr": 1.0,
        "rsi": 1.0
    }

    # -----------------------
    # 1️⃣ DIRECTION (structure)
    # -----------------------
    def score_structure(map_, weight):
        score = 0
        for tf, val in map_.items():
            w = tf_weights.get(tf, 0) * weight
            if val in ("BULLISH", "ABOVE", "UP"):
                score += w
            elif val in ("BEARISH", "BELOW", "DOWN"):
                score -= w
        return score

    direction_score = (
        score_structure(trend_map, indicator_weights["trend"]) +
        score_structure(ema_trend_map, indicator_weights["ema"]) +
        score_structure(vwap_trend_map, indicator_weights["vwap"])
    )

    if direction_score >= 3:
        bias = "Bullish"
    elif direction_score <= -3:
        bias = "Bearish"
    else:
        bias = "Sideways"

    # -----------------------
    # 2️⃣ ENVIRONMENT
    # -----------------------
    environment_score = 0
    for tf, (state, val) in adx_map.items():
        w = tf_weights.get(tf, 0) * indicator_weights["adx"]
        environment_score += w if val >= 30 else -w if val < 20 else 0

    for tf, (state, _) in atr_map.items():
        w = tf_weights.get(tf, 0) * indicator_weights["atr"]
        environment_score += w if state == "HIGH" else -w if state == "LOW" else 0

    # -----------------------
    # 3️⃣ TIMING
    # -----------------------
    timing_score = 0
    for tf, (_, val) in rsi_map.items():
        w = tf_weights.get(tf, 0) * indicator_weights["rsi"]
        if 45 <= val <= 60:
            timing_score += w
        elif val < 30 or val > 70:
            timing_score -= w

    # -----------------------
    # FINAL FLOAT CONFIDENCE
    # -----------------------
    total_strength = abs(direction_score) + environment_score + timing_score
    # scale to 0-10 if needed
    confidence = max(0.0, min(10.0, total_strength / 2.0))  # simple scaling

    # Description
    if environment_score < 0:
        desc = f"{bias} but Low Quality Environment"
    elif bias == "Sideways":
        desc = "Sideways – mixed structure"
    elif confidence >= 8:
        desc = f"Strong {bias} Continuation"
    elif confidence >= 5:
        desc = f"Moderate {bias}"
    else:
        desc = f"Weak {bias}"

    return f"{desc} | Confidence: {confidence:.2f}/10"