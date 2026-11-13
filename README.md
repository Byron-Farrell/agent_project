# Agent project

Django API, React UI, and Postgres, started together with Docker Compose. The browser talks to the Vite dev server. Vite proxies `/api` to Django.

This repository is the skeleton only: configuration, a health check, and agent guidance. It does not implement patients, notes, appointments, or accounts. See [docs/architecture.md](docs/architecture.md) and [AGENTS.md](AGENTS.md).

## Run

Requires Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:5173. The page calls `GET /api/health` and shows the result. Django is also published at http://localhost:8000/api/health.

Postgres data stays in the Compose volume `postgres_data`.

After changing Python dependencies, rebuild the backend image (`docker compose build backend`). After changing frontend dependencies, rebuild the frontend image (`docker compose build frontend`).

## Checks

With the stack running:

```bash
docker compose exec backend ruff check .
docker compose exec backend pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
```

`pytest` runs `backend/apps/health/tests/test_health.py`.
