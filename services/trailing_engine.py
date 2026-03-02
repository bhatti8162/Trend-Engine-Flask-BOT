LONG_TRAIL_STOP = None
SHORT_TRAIL_STOP = None


# -------- ATR Tailing Sytem Engine  --------
def long_trailing_atr(atr_map, current_price):
    global LONG_TRAIL_STOP
    atr_strength, atr = atr_map

    if atr_strength == "LOW":
        ATR_MULTIPLIER = 3.0
    elif atr_strength == "MEDIUM":
        ATR_MULTIPLIER = 2.0
    elif atr_strength == "HIGH":
        ATR_MULTIPLIER = 1.5
    else:
        ATR_MULTIPLIER = 2.0  # safe default

    if atr is None or current_price is None:
        return LONG_TRAIL_STOP, "TRAIL"

    distance = atr * ATR_MULTIPLIER
    new_stop = current_price - distance

    if LONG_TRAIL_STOP is None:
        LONG_TRAIL_STOP = new_stop
        return LONG_TRAIL_STOP, "TRAIL"

    # Update trailing normally
    LONG_TRAIL_STOP = max(LONG_TRAIL_STOP, new_stop)

    # If hit → reset immediately
    if current_price <= LONG_TRAIL_STOP:
        hit_stop = LONG_TRAIL_STOP
        LONG_TRAIL_STOP = None
        return hit_stop, "HIT"

    return LONG_TRAIL_STOP, "TRAIL"


def short_trailing_atr(atr_map, current_price):
    global SHORT_TRAIL_STOP

    atr_strength, atr = atr_map

    if atr_strength == "LOW":
        ATR_MULTIPLIER = 3.0
    elif atr_strength == "MEDIUM":
        ATR_MULTIPLIER = 2.0
    elif atr_strength == "HIGH":
        ATR_MULTIPLIER = 1.5
    else:
        ATR_MULTIPLIER = 2.0  # safe default

    if atr is None or current_price is None:
        return SHORT_TRAIL_STOP, "TRAIL"

    distance = atr * ATR_MULTIPLIER
    new_stop = current_price + distance

    if SHORT_TRAIL_STOP is None:
        SHORT_TRAIL_STOP = new_stop
        return SHORT_TRAIL_STOP, "TRAIL"

    SHORT_TRAIL_STOP = min(SHORT_TRAIL_STOP, new_stop)

    if current_price >= SHORT_TRAIL_STOP:
        hit_stop = SHORT_TRAIL_STOP
        SHORT_TRAIL_STOP = None
        return hit_stop, "HIT"

    return SHORT_TRAIL_STOP, "TRAIL"
