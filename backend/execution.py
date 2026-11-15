"""
Institutional TWAP (Time-Weighted Average Price) Execution Engine
Slices parent market orders into discrete, low-impact sub-orders (chunks)
spaced across a configurable execution window to minimize slippage and
market impact on live order books.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional


def execute_twap_order(
    exchange: Any,
    symbol: str,
    side: str,
    total_amount: float,
    chunks: int = 5,
    duration_minutes: float = 5.0,
    on_chunk_complete: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    on_order_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> threading.Thread:
    """
    Executes a TWAP order in an asynchronous background thread to prevent
    blocking the main trading daemon or event loop.

    Parameters:
        exchange: Authenticated CCXT exchange instance.
        symbol: Tradable pair (e.g., 'BTC/USDT').
        side: 'buy' or 'sell'.
        total_amount: Total volume to execute (e.g., 0.05 BTC).
        chunks: Number of order slices (default: 5).
        duration_minutes: Total execution time window in minutes (default: 5.0).
        on_chunk_complete: Optional callback invoked after each chunk fill.
        on_order_complete: Optional callback invoked when entire TWAP finishes.

    Returns:
        threading.Thread: The started daemon thread.
    """
    chunks = max(1, int(chunks))
    total_amount = float(total_amount)
    duration_minutes = float(duration_minutes)

    def twap_worker():
        # Round chunk size to 5 decimal places (standard crypto lot size granularity)
        chunk_size = round(total_amount / chunks, 5)
        # Handle remainder on the last chunk
        interval_seconds = (duration_minutes * 60.0) / chunks

        print("\n" + "=" * 65)
        print(f"[TWAP START] Initiating {side.upper()} order for {total_amount} {symbol}")
        print(f"             Execution Window: {duration_minutes} mins | Chunks: {chunks}")
        print(f"             Target Slice Size: {chunk_size} {symbol} every {interval_seconds:.1f}s")
        print("=" * 65)

        filled_orders: List[Dict[str, Any]] = []
        cumulative_volume = 0.0
        cumulative_cost = 0.0

        for i in range(chunks):
            # For final chunk, adjust for any rounding remainder
            current_slice = chunk_size
            if i == chunks - 1:
                remainder = round(total_amount - cumulative_volume, 5)
                if remainder > 0:
                    current_slice = remainder

            print(f"\n[TWAP SLICE {i+1}/{chunks}] Routing {side.upper()} {current_slice} {symbol} to exchange...")
            try:
                if side.lower() == "buy":
                    order = exchange.create_market_buy_order(symbol, current_slice)
                elif side.lower() == "sell":
                    order = exchange.create_market_sell_order(symbol, current_slice)
                else:
                    raise ValueError(f"Unsupported order side: {side}")

                exec_price = float(order.get("average") or order.get("price") or 0.0)
                filled_qty = float(order.get("filled") or current_slice)
                order_id = order.get("id", "N/A")

                cumulative_volume += filled_qty
                if exec_price > 0:
                    cumulative_cost += (filled_qty * exec_price)

                print(f"[TWAP FILL] Chunk {i+1}/{chunks} FILLED: {filled_qty} {symbol} @ ${exec_price:,.2f} [ID: {order_id}]")
                filled_orders.append(order)

                if on_chunk_complete:
                    on_chunk_complete(i + 1, order)

            except Exception as e:
                print(f"[TWAP ERROR] Chunk {i+1}/{chunks} failed: {type(e).__name__}: {e}")

            # Sleep between chunks (omit pause after final chunk)
            if i < chunks - 1:
                print(f"[TWAP WATCHDOG] Sleeping for {interval_seconds:.1f}s until chunk {i+2}...")
                time.sleep(interval_seconds)

        avg_price = (cumulative_cost / cumulative_volume) if cumulative_volume > 0 else 0.0
        print("\n" + "=" * 65)
        print(f"[TWAP COMPLETE] Successfully completed {side.upper()} order for {symbol}")
        print(f"                Total Executed Volume: {cumulative_volume:.5f} / {total_amount:.5f} {symbol}")
        print(f"                Volume-Weighted Average Price (VWAP): ${avg_price:,.2f}")
        print(f"                Successful Chunks: {len(filled_orders)}/{chunks}")
        print("=" * 65 + "\n")

        if on_order_complete:
            on_order_complete({
                "symbol": symbol,
                "side": side,
                "total_amount": total_amount,
                "filled_amount": cumulative_volume,
                "average_price": avg_price,
                "chunks": len(filled_orders),
            })

    # Launch worker in an asynchronous background daemon thread
    twap_thread = threading.Thread(target=twap_worker, daemon=True, name=f"TWAP-{side.upper()}-{symbol}")
    twap_thread.start()
    return twap_thread
