#!/usr/bin/env python3
"""
Root Proxy for Vectorized Historical Backtesting Engine.
Executes backend/backtest.py within the current environment.
"""

import os
import sys

# Ensure backend directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backtest import run_backtest

if __name__ == "__main__":
    run_backtest()
