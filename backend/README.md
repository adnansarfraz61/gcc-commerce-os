Backend service for GCC Commerce OS.

## Architecture

The backend follows a modular FastAPI layout:

```text
app/
  api/                Public route composition and versioned API modules
  core/               Settings, logging, security, and cross-cutting concerns
  db/                 PostgreSQL and Redis connection management
  integrations/       Marketplace-specific adapters and OAuth flows
  models/             SQLAlchemy ORM models
  schemas/            Pydantic API contracts
  services/           Reusable domain services
alembic/              Database migrations
```

## Local Commands

```bash
uvicorn app.main:app --reload
alembic upgrade head
```

The application expects environment variables from the root `.env.example`.
