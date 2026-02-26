import requests

def get_1h_change(symbol="BTC", api_key="YOUR_API_KEY"):
    """
    Returns 1-hour percent change for a given symbol from CoinMarketCap.

    Args:
        symbol (str): Crypto symbol like 'BTC', 'ETH'.
        api_key (str): Your CoinMarketCap API key.

    Returns:
        float: 1-hour percent change, or None if failed.
    """
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": "7777a8f48a2f404ea957acb2f00af503"
    }
    params = {
        "symbol": symbol.upper(),
        "convert": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        percent_1h = data["data"][symbol.upper()]["quote"]["USD"]["percent_change_1h"]
        return round(percent_1h, 2)

    except Exception as e:
        print(f"Error fetching 1h change for {symbol}: {e}")
        return None