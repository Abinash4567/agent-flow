.PHONY: help setup dev dev-backend dev-frontend build test lint clean

help:
	@echo "Available commands:"
	@echo "  make setup          - Initial environment setup"
	@echo "  make dev            - Run backend and frontend concurrently"
	@echo "  make dev-backend    - Run backend service"
	@echo "  make dev-frontend   - Run frontend service"
	@echo "  make build          - Build both services"
	@echo "  make test           - Run tests across all services"
	@echo "  make lint           - Run linters across all services"
	@echo "  make clean          - Clean build artifacts and temporary files"

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
	@if [ -f backend/Makefile ]; then $(MAKE) -C backend lint; fi
	@if [ -f frontend/Makefile ]; then $(MAKE) -C frontend lint; fi

clean:
	@echo "Cleaning artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
