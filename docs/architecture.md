# GCC Commerce OS Architecture

## Goals

Phase 1 creates the backend foundation for a multi-tenant AI commerce platform serving GCC sellers across Amazon SP-API, Noon, Shopify, and TikTok Shop.

The architecture is designed around strict tenant isolation, marketplace-specific integration modules, async I/O, and explicit infrastructure boundaries.

## Backend Components

- **FastAPI app**: Exposes tenant-aware APIs under `/api`.
- **Core layer**: Owns configuration, logging, CORS, and JWT/OAuth state helpers.
- **Database layer**: Uses SQLAlchemy 2.x async sessions backed by PostgreSQL.
- **Cache layer**: Uses Redis for future state, locks, rate limiting, webhooks, and job coordination.
- **Models**: Tenants, users, and seller authorizations are the first durable domain objects.
- **Integrations**: Marketplace modules isolate provider-specific OAuth, token refresh, and API client logic.
- **Migrations**: Alembic controls schema changes from the start.

## Marketplace Strategy

Amazon is implemented first because it is the most credential-heavy flow. The same module pattern should be reused for:

- Noon partner credentials and seller account linking
- Shopify OAuth and store authorization
- TikTok Shop OAuth and shop authorization

Marketplace modules should persist shared authorization metadata in `seller_authorizations`. Provider-specific storage can live beside it, as Amazon does with `amazon_seller_authorizations` for seller ID, marketplace ID, encrypted refresh token, and creation timestamp.

## Security Notes

- JWTs include tenant claims and are signed with `SECRET_KEY`.
- OAuth state is short-lived and signed with the same JWT helper.
- Marketplace refresh tokens are encrypted before storage.
- Production deployments must source secrets from a managed secret store and rotate `TOKEN_ENCRYPTION_KEY` carefully.

## Operational Notes

- `/api/health` is a liveness check.
- `/api/ready` verifies PostgreSQL and Redis.
- Docker Compose is suitable for local development.
- Production should run migrations as an explicit release step before starting new API containers.
