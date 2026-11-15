.PHONY: help setup dev dev-backend dev-frontend build test lint format bot daemon backtest pm2-start pm2-stop pm2-restart pm2-status pm2-logs api clean

help:
	@echo "Available commands:"
	@echo "  make setup          - Initial environment setup"
	@echo "  make dev            - Run FastAPI backend and React frontend concurrently"
	@echo "  make dev-backend    - Run FastAPI backend bridge"
	@echo "  make dev-frontend   - Run Vite React frontend dashboard"
	@echo "  make api            - Run FastAPI backend server directly"
	@echo "  make bot            - Run a single evaluation cycle of the trading bot"
	@echo "  make daemon         - Run continuous trading bot daemon in foreground"
	@echo "  make backtest       - Run VectorBT historical backtest and parameter scan"
	@echo "  make pm2-start      - Launch bot daemon as a background PM2 service"
	@echo "  make pm2-stop       - Stop PM2 bot daemon"
	@echo "  make pm2-status     - Check PM2 bot daemon status"
	@echo "  make pm2-logs       - Stream live PM2 bot logs"
	@echo "  make build          - Build both services"
	@echo "  make test           - Run tests across all services"
	@echo "  make lint           - Run linters across root and services"
	@echo "  make format         - Format codebase with Prettier"
	@echo "  make clean          - Clean build artifacts and temporary files"

api:
	@.venv/bin/uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

bot:
	@.venv/bin/python3 bot.py

daemon:
	@DAEMON_MODE=true .venv/bin/python3 bot.py

backtest:
	@.venv/bin/python3 backtest.py

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
	@if [ -f frontend/package.json ]; then cd frontend && npm install; fi

dev-backend:
	@echo "Starting backend API bridge on port 8000..."
	@if [ -f backend/api.py ]; then .venv/bin/uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload; \
	elif [ -f backend/Makefile ]; then $(MAKE) -C backend dev; \
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
