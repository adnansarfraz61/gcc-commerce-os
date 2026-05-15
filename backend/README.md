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

## Amazon OAuth

`GET /api/auth/amazon/login` builds a Login With Amazon consent URL using `AMAZON_CLIENT_ID` and `AMAZON_REDIRECT_URI`.

`GET /api/auth/amazon/callback` exchanges the authorization code with Amazon's token endpoint using `AMAZON_CLIENT_SECRET`, then stores the seller ID, marketplace ID, encrypted refresh token, and creation timestamp in `amazon_seller_authorizations`.
