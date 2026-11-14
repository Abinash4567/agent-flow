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
        "ERROR: Binance credentials not found in environment.\n"
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

# 2. Enable Binance Demo Trading (demo.binance.com)
# CCXT routes to https://demo-api.binance.com for keys created at demo.binance.com/en/my/settings/api-management
USE_LEGACY_SANDBOX = os.getenv("BINANCE_USE_LEGACY_SANDBOX", "false").lower() == "true"

if USE_LEGACY_SANDBOX:
    exchange.set_sandbox_mode(True)
else:
    exchange.enable_demo_trading(True)


def verify_connection():
    endpoint = exchange.urls.get("api", {}).get("public", "demo")
    mode_name = "Legacy Sandbox (testnet.binance.vision)" if USE_LEGACY_SANDBOX else "Binance Demo Trading (demo.binance.com)"
    print(f"1. Exchange Initialized: {exchange.id.upper()}")
    print(f"   Mode: {mode_name}")
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
    print("4. Fetching demo account balances...")
    balance = exchange.fetch_balance()
    
    # Extract non-zero free balances
    active_funds = {
        asset: data.get("free", 0.0)
        for asset, data in balance.items()
        if isinstance(data, dict) and data.get("free", 0.0) > 0
    }
    
    if active_funds:
        print("   [SUCCESS] Available Simulated Funds:")
        for asset, amount in sorted(active_funds.items()):
            print(f"     - {asset}: {amount:,.2f}")
    else:
        usdt_balance = balance.get("USDT", {}).get("free", 0.0)
        print(f"   [SUCCESS] Available Demo Funds: {usdt_balance:,.2f} USDT")

    print("\n--> Level 0 Verified: Authenticated connection established with live simulated paper funds.")


if __name__ == "__main__":
    verify_connection()
