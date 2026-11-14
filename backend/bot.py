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


def test_market_buy(symbol="BTC/USDT", order_size=0.01):
    """
    Executes a simulated market buy order on the connected testnet exchange.
    """
    print(f"\n--- Executing Test Trade ---")
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


if __name__ == "__main__":
    verify_connection()

    # 1. Fetch historical data (50 daily candles)
    historical_df = fetch_historical_data("BTC/USDT", timeframe="1d", limit=50)

    # 2. Execute test market buy order
    test_market_buy()
