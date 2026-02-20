from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from config import API_KEY, API_SECRET


# Use Testnet safely
def get_binance_client():
    """
    Create a Binance client for futures testnet and verify authentication.
    Returns:
        client (Client) if authenticated, else None
    """
    client = Client(API_KEY, API_SECRET)
    # Set futures testnet URL
    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

    try:
        # Test authentication by calling account info
        client.get_exchange_info()
        return client
    except BinanceAPIException as e:
        print("Authentication failed: API error", e)
    except BinanceRequestException as e:
        print("Authentication failed: Request error", e)
    except Exception as e:
        print("Authentication failed: Other error", e)

    return None


# ==========================================

