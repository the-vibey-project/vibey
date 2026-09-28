---
id: skill-python-backend-architecture-7c85633100
purpose: python backend architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-api-style-selection-8790618ccd"]
links: ["skill-next-js-typescript-frontend-architecture-2a271c4136"]
---

## Python Backend Architecture

### Layered / Clean Architecture (FastAPI)
```
API (routers) → application/services → domain (entities, value objects) → infrastructure (repositories, SQLAlchemy)
```
- **Domain layer must have zero dependencies** on API or infrastructure
- Repositories defined as Protocol/ABC interfaces in the application layer, implemented in infrastructure (Dependency Inversion)
- `src/` layout with domain modules; `pyproject.toml` per package

### Repository + Unit of Work Pattern
- Repositories receive a request-scoped `AsyncSession`
- UnitOfWork coordinates commit/rollback across repositories
- Production SQLAlchemy pool tuning: pool size 20, max overflow 30, `pool_pre_ping=True`

### Dependency Injection
- **FastAPI `Depends`** for request-scoped wiring (DB sessions, current user)
- **`dependency-injector`** (Container, providers.Factory/Resource, `@inject`, WiringConfiguration) for larger apps
- **`lagom`** as a lighter alternative
- Manual DI (constructor injection wired in a composition root) is preferable for smaller services

### Application Factory + Lifespan
- `create_app()` builds the FastAPI app, wires the DI container, adds middleware/CORS, includes routers
- `lifespan` manages startup/shutdown (DB pools, caches)
- `app.include_router()` composition has negligible startup cost

### Background Tasks

| Library | Use When |
|---|---|
| **RQ** | Simplest setup; most Django/Flask apps |
| **Celery** | Periodic tasks, complex workflows, existing ecosystem. Caveat: switch to `acks_late` — default `ACKS_EARLY=True` loses payloads on worker crash |
| **Dramatiq** | Message reliability is paramount (financial/compliance); tasks acked only after completion |
| **ARQ** | Async-native (asyncio), Redis-based; pair with supervisord for multi-worker |

### Python Monorepo: uv Workspaces
- Single root `pyproject.toml` with `[tool.uv.workspace] members = [...]`
- One shared `uv.lock`, one `.venv`, cross-package deps via `[tool.uv.sources] pkg = { workspace = true }` (editable by default)
- Limits: single `requires-python` (intersection of all members); no conflicting dependency versions across members

### Testing Pyramid
- Many unit → fewer integration → fewest E2E
- Integration tests against real dependencies using **testcontainers** (real Postgres/Redis in Docker)
- Mock at architectural boundaries (repository interfaces), not deep internals

---
