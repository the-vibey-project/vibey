---
id: skill-1-installation-extras-8ce6dcebe6
purpose: 1 installation extras
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-core/SKILL.md
requires: []
links: ["skill-2-python-the-v1-core-4-phase-bootstrap-eeab716b7e"]
---

## 1. Installation & extras

```bash
pip install vibey-engine                     # the whole family; vibey_bootstrap importable
pip install 'vibey-engine[azure]'            # App Configuration + Key Vault + App Insights
pip install 'vibey-engine[bootstrap-all]'    # every optional dependency any extra below needs
```

**Extra names.** The matrix below lists the extras as `vibey-bootstrap`'s own
`pyproject.toml` declares them, and they still select what each feature needs when the
package is installed from the tree. On the `vibey-engine` package there is no per-feature
successor spelling: the replacements are the two aggregates above (vibey ADR-0037).

### Core dependencies (always installed)

```text
azure-appconfiguration-provider>=1.0.0
azure-keyvault-secrets>=4.7.0
azure-identity>=1.15.0
azure-monitor-opentelemetry>=1.2.0
opentelemetry-api>=1.22.0
# Pinned minimums for CVE remediation:
azure-core>=1.38.0     # CVE-2026-21226
filelock>=3.20.3       # CVE-2025-68146, CVE-2026-22701
urllib3>=2.7.0         # CVE-2026-21441 + CVE-2026-44431/44432
cryptography>=48.0.1,<49  # GHSA-537c-gmf6-5ccf (via azure-identity/msal)
pyjwt>=2.13.0          # PYSEC-2026-175..179 (via msal)
```

### Optional extras matrix

Source of truth: `pyproject.toml`. Many extras are empty markers (`[]`): the code is
**stdlib-only** and already importable without the extra — the extra exists for
discoverability / intent, and only pulls real dependencies where a third-party package
is genuinely required.

| Extra | Installs | What it unlocks |
|---|---|---|
| `fastapi` | `fastapi>=0.110` | `fastapi_middleware`, webhook route, API-key dep, `fastapi_rate_limit` |
| `servicebus` | `azure-servicebus>=7.11` | `servicebus.*` consumer/DLQ helpers |
| `sb-lock` | — (uses `servicebus`) | `sb_lock` message-lock renewal |
| `scheduler` | `apscheduler>=3.10` | `scheduler.parse_cron_trigger` |
| `retry` | `tenacity>=8.0` | `retry.build_retry` + Azure/AI presets |
| `pdf-safety` | `pypdf>=6.13.3` | `pdf_safety.sanitize_pdf_for_passthrough` |
| `sumologic` | `requests>=2.32.0` | `SumoLogicHandler` transport |
| `panther` | `requests>=2.32.0` | Panther SIEM transport |
| `bloblog` | `azure-storage-blob>=12.19` | Blob Storage log transport |
| `sqllog` | `sqlalchemy>=2.0` | SQL table log transport |
| `nosqllog` | `pymongo>=4.6` | Mongo/Cosmos log transport |
| `nosqllog-cosmos` | `azure-cosmos>=4.5` | Cosmos-native log transport |
| `adxlog` | `azure-kusto-ingest`, `azure-kusto-data` | ADX log transport |
| `eventhubslog` | `azure-eventhub>=5.11` | Event Hubs log transport |
| `logging-all` | all transport deps above | every logging transport |
| `transports` | — (stdlib) | transport registry + console/app-insights |
| `alerts` | — (stdlib) | tiered alert dispatcher |
| `health` | — (stdlib) | readiness probes |
| `heartbeat` | — (stdlib) | heartbeat + consumer watchdog |
| `config-refresh` | — (stdlib) | `refresh_log_flags` |
| `ingress` | — (stdlib) | 4-gate attachment classifier |
| `ratelimit` | — (stdlib) | `TokenBucket` + presets |
| `notify` | — (stdlib) | two-tier notification builders |
| `subscription` | — (stdlib) | resource renewal loop |
| `auth` | — (uses `fastapi`) | webhook + API-key guards |
| `identity` | — (`azure-identity` in core) | `build_credential` |
| `audit` | — (stdlib) | `build_audit_extra` |
| `failclose` | — (stdlib) | `require_env` / `optional_env` / `fail_open_env` |
| `openai` | — (stdlib) | AI usage tracker |
| `tokens` | — (stdlib) | HMAC action tokens |
| `metrics` | — (stdlib) | `build_metrics_snapshot` |
| `db` | `sqlalchemy>=2.0`, `alembic>=1.13` | `get_db`, outbox, Alembic helpers |
| `email` | `azure-communication-email>=1.0` | `AcsEmailSender` |
| `http` | `requests>=2.32.0` | `build_session()`, `request_with_retry()` |
| `http-async` | `httpx>=0.27` | `build_async_client()`, `async_request_with_retry()` |
| `documentdb` | `pymongo>=4.6` | `mongo_client_from_env()` |
| `governance` | — (stdlib) | `budget_guard()`, `track_usage()` |
| `aks` | — (stdlib) | `build_info()`, `install_sigterm_handler()`, leader election |
| `all` | fastapi, servicebus, apscheduler, requests, blob, sqlalchemy, alembic, pymongo, ACS email, kusto, eventhub, httpx | aggregate of all third-party deps |
| `dev` / `test` | tooling / test deps | development & CI |

The `vibey-bootstrap` console script (`vibey-bootstrap list`, `vibey-bootstrap scaffold`) ships with
the core install — no extra required. Templates live under `vibey_bootstrap.contrib`.
