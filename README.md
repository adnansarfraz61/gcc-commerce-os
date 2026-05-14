# GCC Commerce OS

AI Commerce Operating System for GCC sellers.

Phase 1 establishes a production-ready FastAPI backend foundation for a multi-tenant commerce platform that can connect sellers across Amazon SP-API, Noon, Shopify, and TikTok Shop.

## What Is Included

- Async FastAPI application with modular route registration
- Environment-driven configuration using Pydantic settings
- PostgreSQL access through SQLAlchemy 2.x async sessions
- Redis connection management for cache, session, and worker use cases
- Alembic migrations for tenants, users, and marketplace authorizations
- JWT helpers for tenant-aware API authentication and OAuth state validation
- Amazon Login With Amazon OAuth module with refresh-token exchange support
- Seller authorization persistence with encrypted refresh-token storage
- Structured logging, CORS, health checks, Dockerfile, and Docker Compose

## Repository Layout

```text
backend/          FastAPI application, integrations, models, migrations
frontend/         Placeholder for the seller/admin web experience
workers/          Placeholder for async ingestion and AI automation workers
docker/           Local container support files
infrastructure/   Cloud deployment notes and future IaC home
docs/             Architecture and phase documentation
```

## Quick Start

1. Copy the sample environment file.

   ```bash
   cp .env.example .env
   ```

2. Fill in secrets and Amazon Login With Amazon credentials in `.env`.

3. Start the local stack.

   ```bash
   docker compose up --build
   ```

4. Run migrations.

   ```bash
   docker compose exec api alembic upgrade head
   ```

5. Check the API.

   ```bash
   curl http://localhost:8000/api/health
   ```

## Key Endpoints

- `GET /api/health` liveness probe
- `GET /api/ready` database and Redis readiness probe
- `GET /api/auth/amazon/login?tenant_id=<uuid>` start Amazon OAuth
- `GET /api/auth/amazon/callback` complete Amazon OAuth and store seller authorization

## Phase 1 Scope

This phase is intentionally backend-heavy. The marketplace abstractions are in place, Amazon is implemented first, and Noon, Shopify, and TikTok Shop have stable extension points for their authorization and catalog/order ingestion modules.
