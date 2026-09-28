---
id: skill-python-security-patterns-acfb5f9875
purpose: python security patterns
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-critical-next-js-react-cves-2025-2026-64d6893eaf"]
links: ["skill-typescript-next-js-security-patterns-29d8bad069"]
---

## Python Security Patterns

### Type Safety and Validation (Pydantic v2)
- Use Pydantic models as request/response contracts in FastAPI
- `Field` constraints: `min_length`, `ge`/`le`, `EmailStr`
- Custom `@field_validator`/`@model_validator`
- Separate Create/Update/Response models — secrets (password hashes, internal fields) never serialize out
- `response_model` to filter output
- Validation is the first line of defense but not a substitute for authorization

### Dependency Security
- **pip-audit** (PyPA official): run in CI and as a pytest gate against the PyPA advisory DB
- Pin deps with hashes (`uv lock` / `uv pip compile --generate-hashes`)
- Add cool-off (`--exclude-newer "1 week"`) to dodge fresh malicious releases
- Behavioral scanners: **Socket.dev** / **GuardDog** / **Phylum**
- **Trusted Publishing (OIDC)** instead of long-lived PyPI tokens
- Real campaigns to know: Shai-Hulud worm (Nov 2025), GhostAction (Sept 2025, 570+ repos / 3,300+ secrets), PyPI phishing (pypj.org, July 2025)

### Static Analysis
- **Bandit** (~80 plugins: weak crypto, `shell=True`, `eval`/`exec`, `assert` for security [B101 — stripped under `-O`], `random` for secrets, bind-all-interfaces) — run in pre-commit at MEDIUM severity/HIGH confidence
- **Semgrep** (taint tracking, OWASP rulesets, reachability in paid Supply Chain)
- **CodeQL**, **Ruff** security rules, **Pysa**

### Async Pitfalls
- Never block the event loop with sync I/O — use `run_in_threadpool` (Starlette) for sync libs
- Avoid shared mutable state across coroutines
- Set timeouts on all awaits to bound resource use

### Authentication and Authorization
- OAuth2 + JWT via `fastapi.security` (`OAuth2PasswordBearer`)
- Hash passwords with **bcrypt** (passlib) or **Argon2**
- Store JWT/refresh config in pydantic-settings with `SecretStr`
- Short-lived access tokens + rotating refresh tokens
- Never use `assert` for authorization (stripped under `-O`)
- RBAC and BOLA checks on every object access (OWASP API Top 10)
- Never log auth headers/cookies/tokens — use a logging filter to scrub PII

---
