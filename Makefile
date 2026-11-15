.PHONY: help setup dev dev-backend dev-frontend build test lint format bot daemon pm2-start pm2-stop pm2-restart pm2-status pm2-logs clean

help:
	@echo "Available commands:"
	@echo "  make setup          - Initial environment setup"
	@echo "  make dev            - Run backend and frontend concurrently"
	@echo "  make dev-backend    - Run backend service"
	@echo "  make dev-frontend   - Run frontend service"
	@echo "  make bot            - Run a single evaluation cycle of the trading bot"
	@echo "  make daemon         - Run continuous trading bot daemon in foreground"
	@echo "  make pm2-start      - Launch bot daemon as a background PM2 service"
	@echo "  make pm2-stop       - Stop PM2 bot daemon"
	@echo "  make pm2-status     - Check PM2 bot daemon status"
	@echo "  make pm2-logs       - Stream live PM2 bot logs"
	@echo "  make build          - Build both services"
	@echo "  make test           - Run tests across all services"
	@echo "  make lint           - Run linters across root and services"
	@echo "  make format         - Format codebase with Prettier"
	@echo "  make clean          - Clean build artifacts and temporary files"

bot:
	@.venv/bin/python3 bot.py

daemon:
	@DAEMON_MODE=true .venv/bin/python3 bot.py

pm2-start:
	@pm2 start ecosystem.config.cjs

pm2-stop:
	@pm2 stop btc-trading-bot

pm2-restart:
	@pm2 restart btc-trading-bot

pm2-status:
	@pm2 status btc-trading-bot

pm2-logs:
	@pm2 logs btc-trading-bot --lines 30

setup:
	@echo "Running setup..."
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend setup; fi
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend setup; fi

dev-backend:
	@echo "Starting backend..."
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend dev; \
	elif [ -f backend/package.json ]; then cd backend && npm run dev; \
	elif [ -f backend/main.py ] || [ -f backend/app.py ]; then cd backend && (python3 -m uvicorn main:app --reload 2>/dev/null || python3 main.py); \
	else echo "No backend entry point configured yet in ./backend"; fi

dev-frontend:
	@echo "Starting frontend..."
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend dev; \
	elif [ -f frontend/package.json ]; then cd frontend && npm run dev; \
	else echo "No frontend entry point configured yet in ./frontend"; fi

dev:
	@echo "Starting all services..."
	@$(MAKE) -j2 dev-backend dev-frontend

build:
	@echo "Building all packages..."
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend build; fi
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend build; fi

test:
	@echo "Running tests..."
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend test; fi
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend test; fi

lint:
	@echo "Running linting..."
	@if [ -f package.json ]; then npm run lint; fi
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend lint; fi
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend lint; fi

format:
	@echo "Formatting codebase..."
	@if [ -f package.json ]; then npm run format; fi

clean:
	@echo "Cleaning artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
