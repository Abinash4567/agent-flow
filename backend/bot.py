import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
import ccxt
import pandas as pd
import requests
from dotenv import load_dotenv

# Search and load .env from current directory or monorepo root
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent

load_dotenv(dotenv_path=current_dir / ".env")
load_dotenv(dotenv_path=repo_root / ".env")

API_KEY = os.getenv("BINANCE_TEST_API") or os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY") or os.getenv("BINANCE_API_SECRET")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

if not API_KEY or not SECRET_KEY:
    print(
        "ERROR: Binance credentials not found in environment.\n"
        "Please ensure BINANCE_TEST_API and BINANCE_SECRET_KEY are set in your .env file.",
        file=sys.stderr,
    )
    sys.exit(1)


# ==========================================
# LEVEL 3: STATE & RISK PARAMETERS
# ==========================================
STATE_FILE = repo_root / ".state.json"

# Risk Management Parameters
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))  # 2% Stop-Loss below entry
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.06"))  # 6% Take-Profit above entry
TRADE_SIZE_BTC = float(os.getenv("TRADE_SIZE_BTC", "0.01"))  # Trade size: 0.01 BTC
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "900"))  # Default: 15 minutes (900s)

# Position Memory
in_position: bool = False
entry_price: float = 0.0
position_size: float = 0.0


def load_position_state():
    """Restores open trade positions across daemon restarts."""
    global in_position, entry_price, position_size
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                in_position = data.get("in_position", False)
                entry_price = float(data.get("entry_price", 0.0))
                position_size = float(data.get("position_size", 0.0))
                if in_position:
                    print(
                        f"[STATE RESTORED] Open Position: {position_size} BTC @ ${entry_price:,.2f}"
                    )
        except Exception as e:
            print(f"[STATE NOTICE] Could not read state file: {e}")


def save_position_state():
    """Persists open trade positions to disk."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "in_position": in_position,
                    "entry_price": entry_price,
                    "position_size": position_size,
                    "updated_at": pd.Timestamp.now().isoformat(),
                },
                f,
                indent=2,
            )
    except Exception as e:
        print(f"[STATE WARNING] Could not persist state: {e}")


load_position_state()


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


def fetch_latest_news(asset="BTC") -> List[str]:
    """
    Fetches the latest headlines for the specified asset from CryptoPanic API,
    falling back automatically to live CoinTelegraph RSS or curated headlines.
    """
    print(f"\n--- Fetching Latest Crypto News ({asset}) ---")
    auth_token = CRYPTOPANIC_API_KEY

    # 1. Attempt CryptoPanic API
    if auth_token and auth_token != "YOUR_API_KEY":
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={auth_token}&currencies={asset}&kind=news"
        try:
            headers = {"User-Agent": "agent-flow/1.0 (TradingBot)"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "results" in data and data["results"]:
                    headlines = [post["title"] for post in data["results"][:5]]
                    print(f"Retrieved {len(headlines)} live headlines from CryptoPanic API.")
                    return headlines
            elif response.status_code == 403:
                print("CryptoPanic returned 403. Auto-switching to real-time CoinTelegraph feed...")
        except Exception as e:
            print(f"CryptoPanic API notice: {e}")

    # 2. Live RSS Feed Fallback (CoinTelegraph)
    try:
        rss_url = "https://cointelegraph.com/rss"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; agent-flow/1.0)"}
        resp = requests.get(rss_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            asset_headlines = []
            for item in items:
                title = item.find("title").text if item.find("title") is not None else ""
                if title:
                    asset_headlines.append(title)
                if len(asset_headlines) >= 5:
                    break

            if asset_headlines:
                print(f"Retrieved {len(asset_headlines)} live headlines from CoinTelegraph real-time feed:")
                for i, h in enumerate(asset_headlines, 1):
                    print(f"  {i}. \"{h}\"")
                return asset_headlines
    except Exception as e:
        print(f"Live RSS fetch notice: {e}")

    # 3. High-signal fallback headlines
    print("Using representative market headlines for sentiment analysis:")
    fallback_headlines = [
        "Bitcoin adoption accelerates as institutional spot ETF inflows surge",
        "Global regulators signal clearer compliance frameworks for crypto assets",
        "BTC hash rate achieves new all-time high amid network upgrades",
        "Major payments network integrates Bitcoin lightning settlement layer",
        "Central banks review digital asset reserve frameworks amid market expansion",
    ]
    for i, h in enumerate(fallback_headlines, 1):
        print(f"  {i}. \"{h}\"")
    return fallback_headlines


_sentiment_pipeline = None


def get_sentiment_analyzer():
    """Lazy loader for FinBERT pipeline to optimize execution speed."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        print("\nLoading FinBERT NLP Model (ProsusAI/finbert)...")
        from transformers import pipeline

        _sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    return _sentiment_pipeline


def analyze_news_sentiment(headlines: List[str]) -> str:
    """
    Uses FinBERT to score news headlines as 'positive', 'negative', or 'neutral'.
    Returns aggregated overall sentiment string.
    """
    print("\n--- Running FinBERT NLP Sentiment Analysis ---")
    if not headlines:
        print("No headlines to analyze. Defaulting to neutral.")
        return "neutral"

    analyzer = get_sentiment_analyzer()
    results = analyzer(headlines)

    score = 0
    print("\nDetailed Headline Sentiment Scoring:")
    for headline, res in zip(headlines, results):
        label = res["label"].lower()
        confidence = res["score"]
        print(f"  [{label.upper()} | {confidence:.1%}] {headline}")

        if label == "positive":
            score += 1
        elif label == "negative":
            score -= 1

    print(f"\nAggregated Sentiment Score: {score:+d} (Positive > 0, Negative < 0, Neutral = 0)")

    if score > 0:
        return "positive"
    elif score < 0:
        return "negative"
    return "neutral"


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


# ==========================================
# LEVEL 3: RISK MANAGEMENT & EXIT ENGINE
# ==========================================
def check_exit_conditions(current_price: float, symbol: str = "BTC/USDT") -> bool:
    """
    Evaluates whether an active position has breached Stop-Loss or reached Take-Profit.
    Closes the position if triggered and updates persistent state.
    """
    global in_position, entry_price, position_size

    if not in_position or entry_price <= 0:
        return False

    price_change_pct = (current_price - entry_price) / entry_price
    print(
        f"\n[POSITION MONITOR] Open: {position_size} BTC | Entry: ${entry_price:,.2f} | Current: ${current_price:,.2f} | PnL: {price_change_pct:+.2%}"
    )

    # Condition A: Stop-Loss Triggered
    if current_price <= entry_price * (1 - STOP_LOSS_PCT):
        print(
            f"[EXIT ALERT] Stop-Loss breached at ${current_price:,.2f} ({price_change_pct:.2%}). Selling position to cap risk."
        )
        test_market_sell(symbol, order_size=position_size or TRADE_SIZE_BTC)
        in_position = False
        entry_price = 0.0
        position_size = 0.0
        save_position_state()
        return True

    # Condition B: Take-Profit Triggered
    elif current_price >= entry_price * (1 + TAKE_PROFIT_PCT):
        print(
            f"[EXIT ALERT] Take-Profit reached at ${current_price:,.2f} ({price_change_pct:+.2%}). Selling position to lock gains."
        )
        test_market_sell(symbol, order_size=position_size or TRADE_SIZE_BTC)
        in_position = False
        entry_price = 0.0
        position_size = 0.0
        save_position_state()
        return True

    print(f"[RISK GUARD] Position within safety tolerances (Stop: -{STOP_LOSS_PCT:.1%}, Target: +{TAKE_PROFIT_PCT:.1%}). Maintaining position.")
    return False


def run_single_cycle(symbol: str = "BTC/USDT", timeframe: str = "1h") -> Dict[str, Any]:
    """Runs a complete evaluation cycle (risk check, indicators, news, decision)."""
    global in_position, entry_price, position_size

    # 1. Fetch current market data
    df = fetch_historical_data(symbol, timeframe=timeframe, limit=50)
    current_price = float(df.iloc[-1]["close"])

    # 2. Manage existing open positions first (Risk Management)
    if in_position:
        exited = check_exit_conditions(current_price, symbol=symbol)
        if exited:
            return {"action": "EXIT", "price": current_price}

    # 3. Look for new entries if cash is available
    if not in_position:
        df = add_technical_indicators(df)
        tech_signal = generate_signal(df)
        print(f"\n[TECHNICAL SIGNAL] EMA Crossover: {tech_signal}")

        headlines = fetch_latest_news("BTC")
        news_sentiment = analyze_news_sentiment(headlines)
        print(f"\n[FUNDAMENTAL SENTIMENT] FinBERT Result: {news_sentiment.upper()}")

        print("\n===============================")
        print("      FINAL TRADE DECISION     ")
        print("===============================")
        if tech_signal == "BUY" and news_sentiment == "positive":
            print(f"[ACTION] Golden Setup: Trend is UP and News is POSITIVE. Executing BUY at ${current_price:,.2f}")
            test_market_buy(symbol, order_size=TRADE_SIZE_BTC)
            in_position = True
            entry_price = current_price
            position_size = TRADE_SIZE_BTC
            save_position_state()
            return {"action": "BUY", "price": current_price}
        elif tech_signal == "SELL" or news_sentiment == "negative":
            print(
                f"[ACTION] Defensive Setup: Trend is {tech_signal} and News is {news_sentiment.upper()}."
            )
            return {"action": "DEFENSIVE_HOLD", "price": current_price}
        else:
            print(f"[ACTION] Mixed/Neutral Signals (Tech: {tech_signal}, News: {news_sentiment}). Holding cash.")
            return {"action": "HOLD_CASH", "price": current_price}

    return {"action": "HOLD_POSITION", "price": current_price}


def run_daemon_loop(symbol: str = "BTC/USDT", timeframe: str = "1h", max_iterations: Optional[int] = None):
    """
    Autonomous continuous daemon loop.
    Executes cycle, monitors risk, sleeps for POLL_INTERVAL_SECONDS, and repeats.
    """
    verify_connection()
    print(f"\n--- Starting Autonomous Continuous Trading Daemon ({symbol}) ---")
    print(f"Risk Rules: Stop-Loss: -{STOP_LOSS_PCT:.1%} | Take-Profit: +{TAKE_PROFIT_PCT:.1%} | Position Size: {TRADE_SIZE_BTC} BTC")
    print(f"Poll Interval: {POLL_INTERVAL_SECONDS} seconds | State Persistence: {STATE_FILE.name}")

    iterations = 0
    while True:
        try:
            iterations += 1
            print(f"\n>>> [CYCLE {iterations} START: {pd.Timestamp.now()}] <<<")
            run_single_cycle(symbol=symbol, timeframe=timeframe)
            print(f">>> [CYCLE {iterations} END: {pd.Timestamp.now()}] Sleeping for {POLL_INTERVAL_SECONDS}s...")

            if max_iterations and iterations >= max_iterations:
                print(f"Completed requested {max_iterations} iteration(s). Daemon exiting cleanly.")
                break

            time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n[DAEMON STOPPED] User interruption received. Exiting gracefully...")
            break
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Daemon loop encountered error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    # Check if run as a single test cycle or continuous daemon
    # If DAEMON_MODE=true in env or --daemon in sys.argv, runs forever; else single cycle
    is_daemon = os.getenv("DAEMON_MODE", "false").lower() == "true" or "--daemon" in sys.argv
    max_iter = None if is_daemon else 1
    run_daemon_loop(max_iterations=max_iter)
