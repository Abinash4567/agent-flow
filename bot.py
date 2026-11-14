#!/usr/bin/env python3
"""Root entrypoint proxy for backend bot script."""
from backend.bot import verify_connection

if __name__ == "__main__":
    verify_connection()
