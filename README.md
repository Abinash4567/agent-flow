# Agent Flow Monorepo

A flexible, polyglot monorepo structure designed for any tech stack compatibility across frontend, backend, and shared utilities.

## Repository Layout

```text
agent-flow/
├── backend/          # Backend service (FastAPI, Express, Go, NestJS, etc.)
├── frontend/         # Frontend application (Next.js, Vite, React, Vue, Svelte, etc.)
├── shared/           # Cross-cutting assets, API contracts, schemas, or shared types
├── .editorconfig     # Consistent indentation and coding conventions
├── .env.example      # Example environment variables
├── .gitignore        # Comprehensive polyglot git ignore rules
├── .dockerignore     # Docker build context ignore rules
├── docker-compose.yml# Container orchestration for running services
├── Makefile          # Unified task runner (dev, build, test, lint, clean)
├── TRACKING.md       # Step-by-step project tracking log
└── README.md
```

## Quick Start

### 1. Environment Configuration

Copy the example environment file to `.env`:

```bash
cp .env.example .env
```

### 2. Working with the Unified Makefile

You can run commands across services using `make`:

```bash
make help          # Show all available targets
make setup         # Run setup hooks in backend and frontend
make dev           # Start both backend and frontend concurrently
make dev-backend   # Start backend only
make dev-frontend  # Start frontend only
make build         # Build all services
make test          # Run test suites
make lint          # Run linters
make clean         # Clean build and temporary artifacts
```

### 3. Docker Compose (Optional)

If Dockerfiles are defined in `backend/` and `frontend/`:

```bash
docker compose up --build
```
