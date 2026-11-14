#!/usr/bin/env python3
"""Root entrypoint proxy for backend bot script."""
from backend.bot import fetch_historical_data, test_market_buy, verify_connection

if __name__ == "__main__":
    verify_connection()

    # 1. Fetch historical data (e.g., 50 days of Daily candles)
    historical_df = fetch_historical_data("BTC/USDT", timeframe="1d", limit=50)

    # 2. Execute test market buy order
    test_market_buy()
