import os
import sys
from pathlib import Path
import ccxt
import pandas as pd
from dotenv import load_dotenv

# Search and load .env from current directory or monorepo root
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent

load_dotenv(dotenv_path=current_dir / ".env")
load_dotenv(dotenv_path=repo_root / ".env")

API_KEY = os.getenv("BINANCE_TEST_API") or os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY") or os.getenv("BINANCE_API_SECRET")

if not API_KEY or not SECRET_KEY:
    print(
        "ERROR: Binance credentials not found in environment.\n"
        "Please ensure BINANCE_TEST_API and BINANCE_SECRET_KEY are set in your .env file.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_authenticated_exchange(api_key: str, secret_key: str):
    """
    Auto-detects whether the API credentials belong to:
    1. Binance Spot Testnet Sandbox (https://testnet.binance.vision)
    2. Binance Demo Trading (https://demo.binance.com)
    """
    # Attempt 1: Spot Testnet Sandbox
    ex_sandbox = ccxt.binance({
        "apiKey": api_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })
    ex_sandbox.set_sandbox_mode(True)
    try:
        ex_sandbox.fetch_balance()
        return ex_sandbox, "Binance Spot Testnet Sandbox (testnet.binance.vision)"
    except ccxt.AuthenticationError:
        pass

    # Attempt 2: Binance Demo Trading
    ex_demo = ccxt.binance({
        "apiKey": api_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })
    ex_demo.enable_demo_trading(True)
    try:
        ex_demo.fetch_balance()
        return ex_demo, "Binance Demo Trading (demo.binance.com)"
    except ccxt.AuthenticationError:
        pass

    # Fallback to sandbox instance if both fail
    return ex_sandbox, "Binance Spot Testnet Sandbox (Unverified Auth)"


exchange, active_mode = get_authenticated_exchange(API_KEY, SECRET_KEY)


def verify_connection():
    endpoint = exchange.urls.get("api", {}).get("public", "unknown")
    print(f"1. Exchange Initialized: {exchange.id.upper()}")
    print(f"   Detected Environment: {active_mode}")
    print(f"   API Endpoint: {endpoint}")

    # Step A: Download exchange rules, limits, and tradable symbols
    print("2. Downloading market data rules and tradable symbols...")
    exchange.load_markets()
    print(f"   [SUCCESS] Loaded {len(exchange.markets)} tradable pairs.")

    # Step B: Read live market price for Bitcoin
    print("3. Fetching latest BTC/USDT ticker...")
    ticker = exchange.fetch_ticker("BTC/USDT")
    last_price = ticker.get("last", 0.0)
    print(f"   [SUCCESS] Latest BTC/USDT Price: ${last_price:,.2f}")

    # Step C: Read simulated account balance
    print("4. Fetching testnet account balances...")
    try:
        balance = exchange.fetch_balance()

        # Primary simulated assets to display
        primary_assets = ["USDT", "USDC", "BTC", "ETH", "BNB"]
        print("   [SUCCESS] Verified Simulated Funds:")
        for asset in primary_assets:
            free_amt = balance.get(asset, {}).get("free", 0.0)
            if free_amt > 0:
                print(f"     - {asset}: {free_amt:,.4f}")

        print("\n--> Level 0 Verified: Authenticated connection established with live simulated paper funds.")
    except Exception as e:
        print(f"\n   [ERROR] Could not fetch balances: {type(e).__name__}: {e}")


def fetch_historical_data(symbol="BTC/USDT", timeframe="1h", limit=100) -> pd.DataFrame:
    """
    Downloads historical OHLCV candlestick data and formats it into a Pandas DataFrame.
    """
    print(f"\n--- Fetching Historical Data ---")
    print(f"Downloading last {limit} {timeframe} candles for {symbol}...")

    # Fetch OHLCV data
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    # Convert to Pandas DataFrame
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Format timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    print(f"Data sample (last 5 {timeframe} candles):")
    print(df.tail())
    return df


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates 9-period and 21-period Exponential Moving Averages (EMA).
    """
    print("\n--- Calculating Technical Indicators (EMA 9 & EMA 21) ---")

    # Calculate Exponential Moving Averages
    df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()

    # Drop early NaN periods if any
    df.dropna(inplace=True)

    print("Indicator summary (last 5 bars):")
    print(df[["close", "ema_9", "ema_21"]].tail())
    return df


def generate_signal(df: pd.DataFrame) -> str:
    """
    Evaluates the last two completed candles to detect EMA 9 / EMA 21 crossovers.
    Returns: 'BUY', 'SELL', or 'HOLD'.
    """
    if len(df) < 2:
        return "HOLD"

    current_candle = df.iloc[-1]
    previous_candle = df.iloc[-2]

    # Condition 1: 9 EMA crosses ABOVE 21 EMA (Bullish Crossover)
    if (
        previous_candle["ema_9"] <= previous_candle["ema_21"]
        and current_candle["ema_9"] > current_candle["ema_21"]
    ):
        return "BUY"

    # Condition 2: 9 EMA crosses BELOW 21 EMA (Bearish Crossover)
    elif (
        previous_candle["ema_9"] >= previous_candle["ema_21"]
        and current_candle["ema_9"] < current_candle["ema_21"]
    ):
        return "SELL"

    # Default state
    return "HOLD"


def test_market_buy(symbol="BTC/USDT", order_size=0.01):
    """
    Executes a simulated market buy order on the connected testnet exchange.
    """
    print(f"\n--- Executing Test Trade (Market Buy) ---")
    print(f"Attempting to buy {order_size} {symbol}...")

    try:
        order = exchange.create_market_buy_order(symbol, order_size)
        print("[SUCCESS] Order filled!")
        print(f"Order ID: {order['id']}")
        exec_price = order.get("average") or order.get("price") or "Market Filled"
        print(f"Execution Price: ${exec_price}")
        print(f"Status: {order['status']}")
        return order
    except ccxt.InsufficientFunds as e:
        print(f"[ERROR] Insufficient simulated funds: {e}")
    except ccxt.ExchangeError as e:
        print(f"[ERROR] Exchange rejected the order: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected order error: {type(e).__name__}: {e}")


def test_market_sell(symbol="BTC/USDT", order_size=0.01):
    """
    Executes a simulated market sell order on the connected testnet exchange.
    """
    print(f"\n--- Executing Test Trade (Market Sell) ---")
    print(f"Attempting to sell {order_size} {symbol}...")

    try:
        order = exchange.create_market_sell_order(symbol, order_size)
        print("[SUCCESS] Sell Order filled!")
        print(f"Order ID: {order['id']}")
        exec_price = order.get("average") or order.get("price") or "Market Filled"
        print(f"Execution Price: ${exec_price}")
        print(f"Status: {order['status']}")
        return order
    except ccxt.InsufficientFunds as e:
        print(f"[ERROR] Insufficient simulated holdings to sell: {e}")
    except ccxt.ExchangeError as e:
        print(f"[ERROR] Exchange rejected the sell order: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected sell error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    verify_connection()

    # 1. Fetch historical data (Using 1h candles for more frequent signals)
    df = fetch_historical_data("BTC/USDT", timeframe="1h", limit=50)

    # 2. Add indicators
    df = add_technical_indicators(df)

    # 3. Generate Signal
    signal = generate_signal(df)
    print(f"\n[TRIGGER] Current Signal for BTC/USDT: {signal}")

    # 4. Execute based on the trigger
    if signal == "BUY":
        print("Executing Buy Strategy...")
        test_market_buy("BTC/USDT", order_size=0.01)
    elif signal == "SELL":
        print("Executing Sell Strategy...")
        test_market_sell("BTC/USDT", order_size=0.01)
    else:
        print("Market is ranging or maintaining existing trend. Holding position.")
