# Backend Service

This directory houses the backend service of the monorepo. It is designed to be completely tech-stack agnostic.

## Supported Stacks

You can initialize any backend framework or runtime here, such as:

- **Python**: FastAPI, Flask, Django, Litestar (`uv`, `poetry`, or `venv`)
- **Node.js / TypeScript**: Express, NestJS, Fastify, Hono (`pnpm`, `npm`, `yarn`, `bun`)
- **Go**: Gin, Fiber, Chi, Echo
- **Rust**: Actix-web, Axum
- **Java / Kotlin**: Spring Boot, Quarkus

## Getting Started

1. Place your backend project files directly inside this directory (`backend/`).
2. (Optional) Provide a `Dockerfile` for containerized runs via the root `docker-compose.yml`.
3. (Optional) Add standard npm scripts (`package.json`) or a `Makefile` with targets (`setup`, `dev`, `build`, `test`, `lint`) to hook seamlessly into the root `Makefile`.
