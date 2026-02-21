# from binance.client import Client
import pandas as pd
import datetime
from zoneinfo import ZoneInfo
from collections import OrderedDict

# Binance client
# client = Client(api_key, api_secret)

# Session times in PKT for reference (used for Binance UTC klines)
SESSIONS = {
    "Tokyo": {"start": 5, "end": 14},      # PKT hours
    "London": {"start": 13, "end": 22},
    "New_York": {"start": 18, "end": 3}
}

# Format time using ZoneInfo
def format_time(dt, tz_name):
    local_time = dt.astimezone(ZoneInfo(tz_name))
    if tz_name.upper() == "UTC":
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return local_time.strftime("%I:%M:%S %p")

# Convert PKT hour to UTC datetime
def pkt_to_utc_datetime(pkt_hour, date=None):
    if date is None:
        date = datetime.date.today()
    # PKT = UTC+5
    utc_hour = (pkt_hour - 5) % 24
    return datetime.datetime.combine(date, datetime.time(utc_hour, 0, tzinfo=datetime.timezone.utc))

def get_all_session_high_low(client, symbol, interval='1h'):
    results = {}
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    # Current times with accurate timezones
    times = OrderedDict([
        ("UTC", format_time(now, "UTC")),
        ("PK", format_time(now, "Asia/Karachi")),
        ("London", format_time(now, "Europe/London")),
        ("New_York", format_time(now, "America/New_York")),
        ("Tokyo", format_time(now, "Asia/Tokyo"))
    ])

    for session, info in SESSIONS.items():
        start_hour = info["start"]
        end_hour = info["end"]
        
        # Session start/end in UTC
        session_start_utc = pkt_to_utc_datetime(start_hour)
        if start_hour < end_hour:
            session_end_utc = pkt_to_utc_datetime(end_hour)
        else:
            # crosses midnight
            session_end_utc = pkt_to_utc_datetime(end_hour) + datetime.timedelta(days=1)
        
        # Determine session status
        if now < session_start_utc:
            results[session] = "Session not started"
            continue
        elif now > session_end_utc:
            results[session] = "Session finished"
            continue
        
        # Session is active, fetch Binance klines
        try:
            klines = client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=int(session_start_utc.timestamp() * 1000),
                endTime=int(session_end_utc.timestamp() * 1000)
            )
            if not klines:
                results[session] = "No data yet"
                continue
            
            df = pd.DataFrame(klines, columns=[
                'open_time','open','high','low','close','volume',
                'close_time','quote_asset_volume','num_trades',
                'taker_buy_base','taker_buy_quote','ignore'
            ])
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            results[session] = {
                "status": "Active",
                "high": float(df['high'].max()),
                "low": float(df['low'].min())
            }
        except Exception as e:
            results[session] = f"Error: {e}"
    
    return {"current_times": times, "sessions": results}