import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Search and load .env
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent

load_dotenv(dotenv_path=current_dir / ".env")
load_dotenv(dotenv_path=repo_root / ".env")

app = FastAPI(
    title="Agent Flow Trading Bot API",
    description="Bridge API connecting frontend monitoring dashboard to the autonomous trading bot daemon.",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE_FILE = repo_root / ".state.json"


@app.get("/api/status")
def get_bot_status() -> Dict[str, Any]:
    """Returns bot daemon status, position memory, live ticker price, and wallet balances."""
    from backend.bot import (
        ATR_MULTIPLIER,
        TRADE_SIZE_BTC,
        active_mode,
        exchange,
    )

    # 1. Read persistent position state
    state = {
        "in_position": False,
        "entry_price": 0.0,
        "highest_price_since_entry": 0.0,
        "current_atr": 0.0,
        "atr_multiplier": ATR_MULTIPLIER,
        "trailing_stop_price": 0.0,
        "position_size": 0.0,
        "updated_at": None,
    }
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state.update(json.load(f))
        except Exception:
            pass

    # 2. Fetch live price and account balance
    current_price = 0.0
    balances = {"USDT": 0.0, "BTC": 0.0}
    try:
        ticker = exchange.fetch_ticker("BTC/USDT")
        current_price = float(ticker.get("last", 0.0))
        bal = exchange.fetch_balance()
        balances["USDT"] = float(bal.get("USDT", {}).get("free", 0.0))
        balances["BTC"] = float(bal.get("BTC", {}).get("free", 0.0))
    except Exception as e:
        print(f"[API ERROR] Exchange fetch failed: {e}")

    # Compute unrealized PnL if in position
    unrealized_pnl_pct = 0.0
    unrealized_pnl_usd = 0.0
    trailing_stop = float(state.get("trailing_stop_price", 0.0))
    if state.get("in_position") and state.get("entry_price", 0.0) > 0:
        entry = state["entry_price"]
        size = state.get("position_size", TRADE_SIZE_BTC)
        unrealized_pnl_pct = (current_price - entry) / entry
        unrealized_pnl_usd = (current_price - entry) * size
        if trailing_stop <= 0 and state.get("current_atr", 0.0) > 0:
            peak = state.get("highest_price_since_entry", entry)
            trailing_stop = max(0.0, peak - (ATR_MULTIPLIER * state["current_atr"]))

    return {
        "status": "online",
        "exchange": exchange.id.upper(),
        "mode": active_mode,
        "symbol": "BTC/USDT",
        "current_price": current_price,
        "state": state,
        "unrealized_pnl": {
            "percent": unrealized_pnl_pct,
            "usd": unrealized_pnl_usd,
        },
        "trailing_stop_price": trailing_stop,
        "balances": balances,
        "risk_rules": {
            "strategy": "ATR Trailing Stop",
            "atr_multiplier": ATR_MULTIPLIER,
            "trade_size_btc": TRADE_SIZE_BTC,
            "execution_engine": "TWAP Asynchronous Slicing",
            "twap_chunks": 5,
            "twap_duration_minutes": 5.0,
        },
    }


@app.get("/api/candles")
def get_chart_candles(limit: int = 30) -> Dict[str, Any]:
    """Returns recent OHLCV candles formatted with EMA 13, EMA 18 & ATR for charts."""
    from backend.bot import add_technical_indicators, fetch_historical_data

    try:
        df = fetch_historical_data("BTC/USDT", timeframe="1h", limit=limit + 30)
        df = add_technical_indicators(df)
        recent = df.tail(limit).reset_index()

        candles = []
        for _, row in recent.iterrows():
            candles.append(
                {
                    "time": row["timestamp"].strftime("%H:%M"),
                    "close": round(float(row["close"]), 2),
                    "ema_fast": round(float(row["ema_fast"]), 2),
                    "ema_slow": round(float(row["ema_slow"]), 2),
                    "ema_13": round(float(row["ema_fast"]), 2),
                    "ema_18": round(float(row["ema_slow"]), 2),
                    "ema_9": round(float(row["ema_fast"]), 2),   # Backward compatibility
                    "ema_21": round(float(row["ema_slow"]), 2),  # Backward compatibility
                    "atr": round(float(row["atr"]), 2),
                    "volume": round(float(row["volume"]), 2),
                }
            )
        return {"symbol": "BTC/USDT", "candles": candles}
    except Exception as e:
        return {"symbol": "BTC/USDT", "candles": [], "error": str(e)}


@app.get("/api/news")
def get_news_sentiment() -> Dict[str, Any]:
    """Returns latest headlines and FinBERT sentiment scoring."""
    from backend.bot import analyze_news_sentiment, fetch_latest_news

    try:
        headlines = fetch_latest_news("BTC")
        sentiment = analyze_news_sentiment(headlines)
        return {"headlines": headlines, "sentiment": sentiment}
    except Exception as e:
        return {"headlines": [], "sentiment": "neutral", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
