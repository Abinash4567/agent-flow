# Frontend Application

This directory houses the frontend application of the monorepo. It is designed to be completely tech-stack agnostic.

## Supported Stacks

You can initialize any frontend framework or library here, such as:

- **React / Next.js / Remix / Vite**
- **Vue / Nuxt / Vite**
- **Svelte / SvelteKit**
- **Astro**
- **Angular**
- **Mobile (React Native / Flutter / Expo)**

## Getting Started

1. Initialize your frontend project inside this directory (`frontend/`).
   - Example (Vite + React):
     ```bash
     npm create vite@latest . -- --template react-ts
     ```
   - Example (Next.js):
     ```bash
     npx create-next-app@latest .
     ```
2. (Optional) Provide a `Dockerfile` for containerized runs via the root `docker-compose.yml`.
3. (Optional) Configure npm scripts (`dev`, `build`, `test`, `lint`) in `package.json` to hook into the root `Makefile`.
