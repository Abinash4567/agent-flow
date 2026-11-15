#!/usr/bin/env python3
"""
Institutional Vectorized Backtesting Engine
Powered by VectorBT (compiled Numba C-loops) and NumPy.

Validates EMA strategies across historical market data, generates institutional tear sheets
(Sharpe ratio, Max Drawdown, Calmar ratio, Profit Factor), and conducts combinatorial parameter
sweeps to determine mathematically optimal parameters.
"""

import os
import sys
import numpy as np
import pandas as pd
import vectorbt as vbt


def fetch_historical_prices(symbol="BTC-USD", start="2021-01-01", end="2024-01-01"):
    """
    Fetches deep historical price data via Yahoo Finance with automatic CCXT Binance fallback.
    """
    print(f"[*] Downloading historical data for {symbol} ({start} to {end})...")
    try:
        yf_data = vbt.YFData.download(symbol, start=start, end=end)
        price_series = yf_data.get("Close")
        if price_series is not None and len(price_series) > 0:
            print(f"[+] Loaded {len(price_series)} daily candles via Yahoo Finance.")
            return price_series
    except Exception as e:
        print(f"[!] Yahoo Finance fetch failed: {e}. Falling back to Binance public klines...")

    # Robust fallback to Binance public OHLCV via CCXT
    try:
        import ccxt
        exchange = ccxt.binance()
        since_ts = exchange.parse8601(f"{start}T00:00:00Z")
        end_ts = exchange.parse8601(f"{end}T00:00:00Z")
        
        all_ohlcv = []
        current_since = since_ts
        while current_since < end_ts:
            batch = exchange.fetch_ohlcv("BTC/USDT", "1d", since=current_since, limit=1000)
            if not batch:
                break
            all_ohlcv.extend(batch)
            last_ts = batch[-1][0]
            if last_ts <= current_since:
                break
            current_since = last_ts + 86400000

        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("datetime", inplace=True)
        df = df[~df.index.duplicated(keep="first")]
        price_series = df["close"]
        print(f"[+] Loaded {len(price_series)} daily candles via Binance.")
        return price_series
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch historical market data from all sources: {exc}")


def run_backtest():
    # 1. Fetch Deep Historical Data (3 years of daily Bitcoin prices)
    price_data = fetch_historical_prices("BTC-USD", start="2021-01-01", end="2024-01-01")

    # 2. Test Current 9/21 EMA Strategy
    print("\n" + "=" * 60)
    print("  PHASE 1: TESTING CURRENT EMA 9/21 EDGE (BASELINE)")
    print("=" * 60)
    
    fast_ema = vbt.MA.run(price_data, window=9, ewm=True)
    slow_ema = vbt.MA.run(price_data, window=21, ewm=True)

    entries = fast_ema.ma_crossed_above(slow_ema)
    exits = fast_ema.ma_crossed_below(slow_ema)

    # Simulate portfolio with 0.1% standard exchange taker fee
    pf = vbt.Portfolio.from_signals(
        price_data,
        entries,
        exits,
        init_cash=10000,
        fees=0.001
    )

    # Output full institutional tear sheet
    stats = pf.stats()
    print("\n--- Institutional Performance Tear Sheet (EMA 9/21) ---")
    print(stats)

    # Key metric extraction
    sharpe = stats.get("Sharpe Ratio", np.nan)
    max_dd = stats.get("Max Drawdown [%]", np.nan)
    profit_factor = stats.get("Profit Factor", np.nan)
    total_ret = stats.get("Total Return [%]", np.nan)

    print("\n--- Key Metric Verification ---")
    print(f"Total Return:   {total_ret:.2f}%")
    print(f"Sharpe Ratio:   {sharpe:.2f} (Target: > 1.0 - 1.5)")
    print(f"Max Drawdown:   {max_dd:.2f}%")
    print(f"Profit Factor:  {profit_factor:.2f}")

    # 3. Optimize: Scan combinations from 5 to 50 via Numba C-arrays
    print("\n" + "=" * 60)
    print("  PHASE 2: SCANNING 1,000+ COMBINATIONS FOR MATHEMATICAL OPTIMUM")
    print("=" * 60)
    windows = np.arange(5, 51)

    print(f"Generating parameter combinations across windows [{windows[0]} -> {windows[-1]}]...")
    fast_mas, slow_mas = vbt.MA.run_combs(
        price_data,
        window=windows,
        r=2,
        short_names=["fast", "slow"],
        ewm=True
    )

    entries_opt = fast_mas.ma_crossed_above(slow_mas)
    exits_opt = fast_mas.ma_crossed_below(slow_mas)

    print("Simulating all portfolio combinations simultaneously via VectorBT...")
    multi_pf = vbt.Portfolio.from_signals(
        price_data,
        entries_opt,
        exits_opt,
        init_cash=10000,
        fees=0.001
    )

    # Extract best returns and best Sharpe
    returns = multi_pf.total_return() * 100
    best_return = returns.max()
    best_combo_raw = returns.idxmax()

    sharpe_ratios = multi_pf.sharpe_ratio()
    best_sharpe = sharpe_ratios.max()
    best_sharpe_combo_raw = sharpe_ratios.idxmax()

    index_names = returns.index.names
    fast_idx = index_names.index("fast_window") if "fast_window" in index_names else 0
    slow_idx = index_names.index("slow_window") if "slow_window" in index_names else 2

    best_fast = best_combo_raw[fast_idx]
    best_slow = best_combo_raw[slow_idx]

    sharpe_fast = best_sharpe_combo_raw[fast_idx]
    sharpe_slow = best_sharpe_combo_raw[slow_idx]

    print("\n" + "=" * 60)
    print("  OPTIMIZATION RESULTS: TOP PARAMETER COMBINATIONS")
    print("=" * 60)
    print(f"Mathematically Optimal Return:   Fast EMA = {best_fast}, Slow EMA = {best_slow}")
    print(f"Optimal Total Return:            {best_return:.2f}% (vs {total_ret:.2f}% baseline)")
    print(f"Highest Sharpe Ratio Setup:      Fast EMA = {sharpe_fast}, Slow EMA = {sharpe_slow}")
    print(f"Highest Annualized Sharpe Ratio: {best_sharpe:.2f} (vs {sharpe:.2f} baseline)")

    # Print Top 5 Combinations by Sharpe Ratio
    print("\n--- Top 5 Setups by Risk-Adjusted Return (Sharpe Ratio) ---")
    top_sharpe = sharpe_ratios.sort_values(ascending=False).head(5)
    for rank, (combo, sh) in enumerate(top_sharpe.items(), 1):
        f_w = combo[fast_idx]
        s_w = combo[slow_idx]
        ret = returns.loc[combo]
        print(f"  #{rank}: EMA {f_w}/{s_w} -> Sharpe: {sh:.2f} | Return: {ret:.2f}%")

    # 4. Generate Interactive Visualization Dashboard
    output_html = "backtest_results.html"
    try:
        fig = pf.plot()
        fig.write_html(output_html)
        print(f"\n[+] Interactive equity curve & drawdown report saved to: {output_html}")
    except Exception as e:
        print(f"[!] Could not save HTML plot: {e}")

    return {
        "baseline_stats": stats,
        "best_combo": (best_fast, best_slow),
        "best_return": best_return,
        "best_sharpe_combo": (sharpe_fast, sharpe_slow),
        "best_sharpe": best_sharpe,
    }


if __name__ == "__main__":
    run_backtest()
