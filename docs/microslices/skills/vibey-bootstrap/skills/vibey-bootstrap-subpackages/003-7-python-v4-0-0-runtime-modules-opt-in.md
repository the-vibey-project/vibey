---
id: skill-7-python-v4-0-0-runtime-modules-opt-in-820fde5df1
purpose: 7 python v4 0 0 runtime modules opt in
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-subpackages/SKILL.md
requires: ["skill-6-python-end-to-end-recipes-10f02ecb06"]
links: []
---

## 7. Python: v4.0.0 runtime modules (opt-in)

### `db` — SQLAlchemy session + health (needs `[db]`)
```python
from vibey_bootstrap.db import get_db, get_sessionmaker, db_health, postgres_rls_statements
from vibey_bootstrap.db.migrations import upgrade_to_head, write_env_py
from vibey_bootstrap.db.outbox import Outbox, drain_outbox, OUTBOX_DDL

# FastAPI dependency — yields and always closes:
# def endpoint(db: Session = Depends(get_db)): ...

health = db_health()   # {"status": "ok"|"error", "latency_ms": ...}
```
Env: `DATABASE_URL` (required). `create_engine_from_env()` sets `pool_pre_ping=True`.

### `db.outbox` — transactional outbox (needs `[db]`)
```python
outbox = Outbox(session)
msg = outbox.enqueue(idempotency_key="email-123", payload={"to": [...], "subject": "..."})
sent = drain_outbox(session, AcsEmailSender(), batch_size=10)
```
`OUTBOX_DDL` is Postgres-oriented (`JSONB`, `FOR UPDATE SKIP LOCKED` in drain).
`AcsEmailSender.__call__` is outbox-compatible.

### `email` — ACS sender (needs `[email]`)
```python
from vibey_bootstrap.email import AcsEmailSender
sender = AcsEmailSender()   # reads ACS_CONNECTION_STRING, ACS_SENDER_ADDRESS
sender.send(to=["user@example.com"], subject="...", html_body="...")
```

### `http` — hardened outbound client (needs `[http]` / `[http-async]`)
```python
from vibey_bootstrap.http import build_session, request_with_retry, normalize_pem, write_temp_pem
from vibey_bootstrap.http.async_client import build_async_client, async_request_with_retry

resp = request_with_retry("GET", "https://api.example.com/data", allow_private=False)
```
SSRF guard (`check_ssrf`), default timeout, `traceparent` injection, urllib3 Retry on
`408/429/5xx` with `Retry-After`. PEM helpers normalize Key-Vault-mangled certs.

### `documentdb` — Mongo/Cosmos (needs `[documentdb]`)
```python
from vibey_bootstrap.documentdb import mongo_client_from_env, documentdb_health
client = mongo_client_from_env()   # NOSQL_URI
```
Env: `NOSQL_URI`, `NOSQL_DATABASE`.

### `aks` — pod runtime helpers (stdlib, `[aks]` marker)
```python
from vibey_bootstrap.aks import (
    install_sigterm_handler, setup_async_sigterm_handler,
    build_info, keda_metric_value, mount_build_info_route, pod_context_extra,
)
from vibey_bootstrap.aks.leader_election import leader_election, LeaderElection

install_sigterm_handler(stop_event)
info = build_info()   # BUILD_VERSION, GIT_SHA, POD_NAME, POD_NAMESPACE, …
election = leader_election()   # soft no-op when LEADER_ELECTION_CONFIGMAP unset
if election.is_leader():
    run_scheduled_job()
```
Env: `BUILD_VERSION` / `APP_VERSION`, `GIT_SHA`, `POD_NAME`, `POD_NAMESPACE`,
`NODE_NAME`, `LEADER_ELECTION_CONFIGMAP`.

### `governance` — budget guard + usage meter (stdlib, `[governance]` marker)
```python
from vibey_bootstrap.governance import budget_guard, track_usage, BudgetGuard, UsageTracker

check = budget_guard("my-project", "daily", estimated_usd=0.05)
if not check.allowed:
    raise RateLimitError("budget exceeded")
track_usage("openai", units=1200, unit_type="tokens")
```

### `contrib.scaffold` — `vibey-bootstrap` CLI (core install)
```bash
vibey-bootstrap list
vibey-bootstrap scaffold helm/worker/Chart.yaml.template --out ./deploy --var APP_NAME=my-svc
vibey-bootstrap version
```
Templates: Terraform (AKS), Bicep, Helm worker chart, GitOps kustomize base, CI/CD
workflows, OPA/Conftest policy starters. See `examples/46_scaffold_cli.py`.

### v3 extensions to Tier 1 modules (in existing subpackages)

**`identity`** (v3): `build_tenant_credential()`, `build_tenant_credential_cached()`,
`credential_health()`, `TokenCache`.

**`audit`** (v3): `ChainedAuditRecord`, `AuditChain`, `verify_chain()` — tamper-evident
hash-chained audit log entries atop `build_audit_extra`.
