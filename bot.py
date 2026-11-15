#!/usr/bin/env python3
"""Root entrypoint proxy for backend bot script."""
from backend.bot import (
    add_technical_indicators,
    analyze_news_sentiment,
    fetch_historical_data,
    fetch_latest_news,
    generate_signal,
    test_market_buy,
    test_market_sell,
    verify_connection,
)

if __name__ == "__main__":
    verify_connection()

    # 1. Quantitative Analysis (Level 1: EMA 9 / EMA 21)
    df = fetch_historical_data("BTC/USDT", timeframe="1h", limit=50)
    df = add_technical_indicators(df)
    tech_signal = generate_signal(df)
    print(f"\n[TECHNICAL SIGNAL] EMA Crossover: {tech_signal}")

    # 2. Qualitative Analysis (Level 2: FinBERT News Sentiment)
    headlines = fetch_latest_news("BTC")
    news_sentiment = analyze_news_sentiment(headlines)
    print(f"\n[FUNDAMENTAL SENTIMENT] FinBERT Result: {news_sentiment.upper()}")

    # 3. The Combined Edge Execution
    print("\n===============================")
    print("      FINAL TRADE DECISION     ")
    print("===============================")
    if tech_signal == "BUY" and news_sentiment == "positive":
        print("[ACTION] Golden Setup: Trend is UP and News is POSITIVE. Executing BUY.")
        test_market_buy("BTC/USDT", order_size=0.01)
    elif tech_signal == "SELL" or news_sentiment == "negative":
        print(
            f"[ACTION] Defensive Setup: Trend is {tech_signal} and News is {news_sentiment.upper()}."
        )
        if tech_signal == "SELL":
            print("Trend broke downward: Executing SELL order...")
            test_market_sell("BTC/USDT", order_size=0.01)
        else:
            print("News is NEGATIVE despite neutral/flat trend: Preserving cash, no buy.")
    else:
        print(f"[ACTION] Mixed/Neutral Signals (Tech: {tech_signal}, News: {news_sentiment}). Holding cash.")
