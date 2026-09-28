---
id: skill-9-appendices-9b27bb150b
purpose: 9 appendices
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-typescript/SKILL.md
requires: ["skill-8-typescript-next-js-b-porting-the-patterns-to-typescript-2ee86b186b"]
links: []
---

## 9. Appendices

### 9.1 Master environment-variable reference

| Variable | Default | Area |
|---|---|---|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | — | telemetry (v1) |
| `AZURE_APP_CONFIGURATION_CONNECTION_STRING` | — | App Config (v1) |
| `AZURE_APPCONFIG_ENDPOINT` | — | App Config via AAD (health) |
| `AZURE_KEY_VAULT_URL` | — | Key Vault (v1) |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | — | `build_credential` |
| `LOG_LEVEL` | `INFO` | logging |
| `DEBUG_LOGGING_ENABLED` | off | DEBUG second gate |
| `USE_MOCK_BOOTSTRAP` | off | mock bootstrap / probes |
| `FUNCTIONS_WORKER_RUNTIME` | — | Azure Functions detection |
| `CONSOLE_LOGGING_ENABLED` | on | transport flag |
| `APP_INSIGHTS_LOGGING_ENABLED` | off | transport flag |
| `SUMO_LOGIC_LOGGING_ENABLED` | off | transport flag |
| `SUMO_LOGIC_COLLECTOR_URL` (+ `_TOKEN`, `_SOURCE_CATEGORY`, `_SOURCE_HOST`, `_FIELDS`, `_BATCH_SIZE`, `_MAX_BATCH_BYTES`, `_GZIP_THRESHOLD`, `_FLUSH_INTERVAL`, `_MAX_BUFFER`, `_TIMEOUT`) | see primitives skill | Sumo transport |
| `PANTHER_LOGGING_ENABLED`, `PANTHER_API_HOST`, `PANTHER_LOG_SOURCE_*` | off | Panther transport (v3) |
| `FILE_LOGGING_ENABLED`, `FILE_LOG_PATH`, `FILE_LOG_ROOT`, `FILE_LOG_ROTATION`, … | off | local file transport (v3) |
| `BLOB_LOGGING_ENABLED`, `BLOB_*` | off | Blob log transport (v3) |
| `SQL_LOGGING_ENABLED`, `SQL_LOG_DSN`, `SQL_LOG_TABLE` | off | SQL log transport (v3) |
| `NOSQL_LOGGING_ENABLED`, `NOSQL_LOG_URI`, `NOSQL_LOG_DATABASE` | off | NoSQL log transport (v3) |
| `ADX_LOGGING_ENABLED`, `ADX_CLUSTER_URI`, `ADX_DATABASE` | off | ADX log transport (v3) |
| `EVENTHUBS_LOGGING_ENABLED`, `EVENTHUB_FQNS`, `EVENTHUB_NAME` | off | Event Hubs log transport (v3) |
| `DATABASE_URL` | — | SQLAlchemy / outbox (v3 `[db]`) |
| `ACS_CONNECTION_STRING`, `ACS_SENDER_ADDRESS` | — | ACS email (v3 `[email]`) |
| `NOSQL_URI`, `NOSQL_DATABASE` | — | documentdb client (v3) |
| `BUILD_VERSION` / `APP_VERSION`, `GIT_SHA`, `POD_NAME`, `POD_NAMESPACE`, `NODE_NAME` | — | AKS build info (v3) |
| `LEADER_ELECTION_CONFIGMAP` | — | AKS leader election (v3) |
| `SERVICE_BUS_TRANSPORT_TYPE` | `amqp` | `amqp` or `websocket` (v3) |
| `API_KEY` | — | `verify_api_key_header` |
| `GRAPH_WEBHOOK_CLIENT_STATE` | — (required for webhooks) | webhook auth |
| `DEV_ALERTS_ENABLED`, `DEV_ALERT_RECIPIENTS`, `ALERT_DEDUP_WINDOW_SECONDS`, `ALERT_MAX_PER_HOUR`, `ALERT_ESCALATE_AFTER`, `ALERT_ESCALATE_WINDOW_SECONDS`, `ALERT_CRITICAL_SUBJECT_PREFIX` | see Part 5 | `alerts` dispatcher |
| `HEARTBEAT_INTERVAL_SECONDS` / `WATCHDOG_*` | see Part 5 | heartbeat |
| `AI_TPM_LIMIT[_<DEPLOYMENT>]`, `AI_COST_ALERT_HOURLY_DOLLARS`, `AI_COST_ALERT_DAILY_DOLLARS`, `AI_HIGH_USAGE_TOKENS_HOURLY` | — | `openai` tracker |
| `AZURE_BOOTSTRAP_ALLOW_RESET` | off | **test-only** (see 9.2) |

### 9.2 Testing note

Subpackages with global state (counters, latency histograms, alert dispatcher,
transports, webhook dedup, …) expose `reset_state()` / `_reset_*` helpers **gated by
`AZURE_BOOTSTRAP_ALLOW_RESET=1`**. The test suite sets it once in `test/conftest.py`;
**production code must never set it.** For local/dev runs without Azure, set
`USE_MOCK_BOOTSTRAP=true` to make `ensure_bootstrap()` a no-op and the health/identity
probes return `{"status":"ok","mock":true}`.

### 9.3 Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Sumo transport silently does nothing | `SUMO_LOGIC_COLLECTOR_URL` unset, or `[sumologic]` extra (`requests`) not installed → `make_sumo_logic_handler()` returns `None` by design. |
| v3 transport silently does nothing | Required env vars unset or pip extra missing — factories return `None` (soft no-op); check `list_transports()`. |
| `ImportError` from `get_db` / `drain_outbox` | Install the `[db]` extra (`sqlalchemy`, `alembic`). |
| `ImportError` from `request_with_retry` | Install the `[http]` extra (`requests`). |
| App Insights never "upgrades" | The connection string wasn't present in env at phase 2 and isn't in App Config either; verify `APPLICATIONINSIGHTS_CONNECTION_STRING`. |
| `ImportError` from `install_graph_webhook_route` / `fastapi_rate_limit` | Install the `fastapi` extra. |
| DEBUG logs missing despite `LOG_LEVEL=DEBUG` | Also set `DEBUG_LOGGING_ENABLED=true` (the second gate). |
| `LoggingExtraConflictError` | An `extra={}` key collides with a reserved `LogRecord` attribute (e.g. `name`, `msg`, `args`) — rename it. |
| `ConfigurationError` from webhook | `GRAPH_WEBHOOK_CLIENT_STATE` is unset; the endpoint refuses all entries (`401`). |

### 9.4 Further reading

- `README.md` — overview + extras matrix
- `docs/USAGE.md` — complete usage guide (Python + TypeScript)
- `examples/README.md` — numbered reading order (01 → 46 + e2e_*)
- `CHANGELOG.md` — release-by-release surface
- `MIGRATING-FROM-V1.md` — v1 → v2 adoption
- `MIGRATING-TO-V3.md` — v4.0.0 opt-in features (additive, no breaking changes)
