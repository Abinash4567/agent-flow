import os
import sys
from pathlib import Path
import ccxt
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
        "ERROR: Binance Testnet credentials not found in environment.\n"
        "Please ensure BINANCE_TEST_API and BINANCE_SECRET_KEY are set in your .env file.",
        file=sys.stderr,
    )
    sys.exit(1)

# 1. Initialize the exchange
exchange = ccxt.binance({
    "apiKey": API_KEY,
    "secret": SECRET_KEY,
    "enableRateLimit": True,  # Automatically spaces out requests to prevent rate-limit blocks
})

# 2. CRITICAL: Switch to sandbox/testnet before making any API calls
exchange.set_sandbox_mode(True)


def verify_connection():
    endpoint = exchange.urls.get("api", {}).get("public", "testnet")
    print(f"1. Exchange Initialized: {exchange.id.upper()} (Endpoint: {endpoint})")

    # Step A: Download exchange rules, limits, and tradable symbols
    print("2. Downloading market data rules and tradable symbols...")
    exchange.load_markets()
    print(f"   [SUCCESS] Loaded {len(exchange.markets)} tradable pairs from testnet.")

    # Step B: Read live market price for Bitcoin
    print("3. Fetching latest BTC/USDT ticker...")
    ticker = exchange.fetch_ticker("BTC/USDT")
    last_price = ticker.get("last", 0.0)
    print(f"   [SUCCESS] Latest BTC/USDT Price: ${last_price:,.2f}")

    # Step C: Read simulated account balance
    print("4. Fetching testnet simulated account balance...")
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance.get("USDT", {}).get("free", 0.0)
        print(f"   [SUCCESS] Available Testnet Funds: {usdt_balance:,.2f} USDT")
        print("\n--> Level 0 Verified: Connection established and authenticated with fake funds.")
    except ccxt.AuthenticationError as err:
        print(
            f"\n   [AUTH NOTICE] Public market data connected, but account authentication failed: {err}\n"
            "   Common causes for Binance Testnet code -2015:\n"
            "   a) The API key was generated on Binance Demo Trading or Futures rather than Binance Spot Testnet (https://testnet.binance.vision).\n"
            "   b) The keys on testnet.binance.vision expired or were regenerated (keys on testnet periodically reset).\n"
            "   c) IP restriction or permissions are enabled on the key."
        )
    except Exception as ex:
        print(f"\n   [NOTICE] Balance fetch encountered: {type(ex).__name__}: {ex}")


if __name__ == "__main__":
    verify_connection()
