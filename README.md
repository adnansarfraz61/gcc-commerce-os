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

   Required Amazon OAuth variables:

   ```bash
   AMAZON_CLIENT_ID=amzn1.application-oa2-client...
   AMAZON_CLIENT_SECRET=...
   AMAZON_REDIRECT_URI=http://localhost:8000/api/auth/amazon/callback
   AMAZON_SP_API_APPLICATION_ID=amzn1.sellerapps.app...
   ```

3. Install local dependencies if you want to run the API outside Docker.

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r ../requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

## Docker Setup

1. Start PostgreSQL, Redis, and the API.

   ```bash
   docker compose up --build
   ```

2. Run migrations.

   ```bash
   docker compose exec api alembic upgrade head
   ```

3. Check the API.

   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/health
   ```

## Key Endpoints

- `GET /api/health` liveness probe
- `GET /api/ready` database and Redis readiness probe
- `GET /api/auth/amazon/login?tenant_id=<uuid>` start Amazon OAuth
- `GET /api/auth/amazon/test-login?tenant_id=<uuid>&region=europe` start Seller Central authorization testing
- `GET /api/auth/amazon/callback` complete Amazon OAuth and store seller authorization
- `GET /api/auth/amazon/status?tenant_id=<uuid>` inspect stored Amazon authorizations

## Testing Amazon OAuth Locally

1. Start the local stack and run migrations.

   ```bash
   docker compose up --build
   docker compose exec api alembic upgrade head
   ```

2. Create or seed a tenant row. The backend validates `tenant_id` before it generates OAuth state.

3. Generate a Seller Central authorization URL for the seller's region.

   ```bash
   curl "http://localhost:8000/api/auth/amazon/test-login?tenant_id=<tenant_uuid>&region=europe&marketplace_id=A2VIGQ35RCS4UG"
   ```

   Supported `region` values:

   - `north_america`
   - `europe`
   - `far_east`

4. Open the returned `authorization_url`, sign in to Seller Central, and approve the app. Amazon redirects to `AMAZON_REDIRECT_URI` with `state`, `spapi_oauth_code`, and `selling_partner_id`.

5. The callback accepts `code` or `spapi_oauth_code`, plus `seller_id` or `selling_partner_id`.

   ```bash
   curl "http://localhost:8000/api/auth/amazon/callback?state=<state>&spapi_oauth_code=<code>&selling_partner_id=<seller_id>&marketplace_id=A2VIGQ35RCS4UG"
   ```

6. Verify authorization status without exposing tokens.

   ```bash
   curl "http://localhost:8000/api/auth/amazon/status?tenant_id=<tenant_uuid>"
   ```

7. Verify storage in PostgreSQL.

   ```bash
   docker compose exec postgres psql -U gcc -d gcc_commerce_os -c "select seller_id, marketplace_id, created_at from amazon_seller_authorizations;"
   ```

The OAuth state is signed and stored in Redis by hash with a short TTL. Callback handling consumes the state once, validates it against the signed claims, exchanges the Amazon authorization code for tokens, encrypts the refresh token, and stores it in PostgreSQL.

## Amazon Authorization Instructions

1. Configure the Login With Amazon client and SP-API application in Seller Central.
2. Set `AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_REDIRECT_URI`, and `AMAZON_SP_API_APPLICATION_ID`.
3. Ensure the redirect URI registered in Amazon exactly matches `AMAZON_REDIRECT_URI`.
4. Choose the Seller Central region that matches the seller account:
   - North America: `north_america`
   - Europe: `europe`
   - Far East: `far_east`
5. Run the `/api/auth/amazon/test-login` URL and complete approval in Seller Central.

Integration examples are available in `docs/integration_tests/amazon_oauth.http`.

## Phase 1 Scope

This phase is intentionally backend-heavy. The marketplace abstractions are in place, Amazon is implemented first, and Noon, Shopify, and TikTok Shop have stable extension points for their authorization and catalog/order ingestion modules.
