#!/usr/bin/env python3
"""Root entrypoint proxy for continuous trading bot daemon."""
import os
import sys
from backend.bot import (
    check_exit_conditions,
    run_daemon_loop,
    run_single_cycle,
    verify_connection,
)

if __name__ == "__main__":
    is_daemon = os.getenv("DAEMON_MODE", "false").lower() == "true" or "--daemon" in sys.argv
    max_iter = None if is_daemon else 1
    run_daemon_loop(max_iterations=max_iter)
