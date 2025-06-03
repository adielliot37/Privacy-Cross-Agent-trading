
import ccxt
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, TRADE_USD_SIZE, LEVERAGE

def create_futures_client() -> ccxt.binance:
    """
    Returns a CCXT Binance client configured for USDT-M futures with your API keys.
    """
    client = ccxt.binance({
        "apiKey": BINANCE_API_KEY,
        "secret": BINANCE_SECRET_KEY,
        "enableRateLimit": True,
        "options": {
            "defaultType": "future" 
        }
    })
    return client

def open_position(symbol: str, side: str) -> dict:
    """
    Places a $10 market order with 5× leverage on Binance Futures.
    - symbol: e.g. "ETH/USDT"
    - side:   "Long" or "Short"
    Returns the CCXT order response dict on success; raises on failure.
    """
    client = create_futures_client()

    # 1) Set 5× leverage
    try:
        client.set_leverage(LEVERAGE, symbol)
    except Exception as e:
       
        params = {"symbol": symbol.replace("/", ""), "leverage": LEVERAGE}
        client.fapiPrivate_post_leverage(params) 

    
    ticker = client.fetch_ticker(symbol)
    price = float(ticker["last"])
    if price <= 0:
        raise Exception(f"Invalid price {price} for {symbol}")

  
    nominal = TRADE_USD_SIZE * LEVERAGE
    quantity = nominal / price

   
    if side == "Long":
        order = client.create_order(
            symbol=symbol,
            type="market",
            side="buy",
            amount=quantity,
            params={"reduceOnly": False}
        )
    else:  # "Short"
        order = client.create_order(
            symbol=symbol,
            type="market",
            side="sell",
            amount=quantity,
            params={"reduceOnly": False}
        )

    return order
