#!/usr/bin/env python3
"""Root entrypoint proxy for backend bot script."""
from backend.bot import (
    add_technical_indicators,
    fetch_historical_data,
    generate_signal,
    test_market_buy,
    test_market_sell,
    verify_connection,
)

if __name__ == "__main__":
    verify_connection()

    # 1. Fetch historical data (1h candles)
    df = fetch_historical_data("BTC/USDT", timeframe="1h", limit=50)

    # 2. Add technical indicators (EMA 9 & EMA 21)
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
