---
id: skill-4-python-logging-transports-v2-1-v3-0-ten-sinks-35043b1537
purpose: 4 python logging transports v2 1 v3 0 ten sinks
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-primitives/SKILL.md
requires: ["skill-3-python-v2-tier-1-primitives-always-on-stdlib-only-aaedecf92d"]
links: []
---

## 4. Python: logging transports (v2.1 + v3.0 — ten sinks)

A **transport** is a named factory `Callable[[], logging.Handler | None]`. Enabling
attaches its handler to the root logger; disabling detaches and closes it. This
decouples *where logs go* from *how they're formatted*.

```python
from vibey_bootstrap import (
    configure_transports, register_transport,
    enable_transport, disable_transport, list_transports,
)

# One call to wire built-ins (explicit bool wins; else env flag):
configure_transports(console=True, app_insights=False, sumo_logic=True)

# v3.0 — enable additional sinks in one call:
configure_transports(console=True, panther=True, file=True, blob=True, sql=True,
                     nosql=True, adx=True, event_hubs=True)

list_transports()   # {'console': {'registered': True, 'enabled': True}, ...}
```

`configure_transports()` also sets the root logger to `effective_log_level()` so
enabled transports actually receive records. It is idempotent and re-runnable.

### Built-in transports (ten total)

| Name | Handler | Extra | Env flag | Default |
|---|---|---|---|---|
| `console` | `StreamHandler` + `ExtraFieldsFormatter` + `CorrelationFilter` | stdlib | `CONSOLE_LOGGING_ENABLED` | **on** |
| `app_insights` | OpenTelemetry handler (delegates to v1 `TelemetryManager`) | stdlib | `APP_INSIGHTS_LOGGING_ENABLED` | off |
| `sumo_logic` | `SumoLogicHandler` (buffered async POST) | `[sumologic]` | `SUMO_LOGIC_LOGGING_ENABLED` | off |
| `panther` | Panther SIEM HTTP Source | `[panther]` | `PANTHER_LOGGING_ENABLED` | off |
| `file` | Rotating local log file (`JsonLogFormatter`) | stdlib | `FILE_LOGGING_ENABLED` | off |
| `blob` | Azure Blob Storage NDJSON | `[bloblog]` | `BLOB_LOGGING_ENABLED` | off |
| `sql` | SQL table append | `[sqllog]` | `SQL_LOGGING_ENABLED` | off |
| `nosql` | Mongo/Cosmos collection append | `[nosqllog]` | `NOSQL_LOGGING_ENABLED` | off |
| `adx` | Azure Data Explorer ingest | `[adxlog]` | `ADX_LOGGING_ENABLED` | off |
| `event_hubs` | Azure Event Hubs producer | `[eventhubslog]` | `EVENTHUBS_LOGGING_ENABLED` | off |

Two caveats: (1) the `console` transport installs **the same** `StreamHandler` stack
as `configure_logging()` — enabling both produces duplicate console lines, so pick one;
(2) if you also call `configure_logging()` (which does `basicConfig(force=True)` and
replaces root handlers), call it **before** `configure_transports()`, which reconciles
against the live root handlers on each run. Disabling `app_insights` only detaches the
OTel handler (the exporter is not torn down). A custom sink is one call away:

```python
register_transport("my_syslog", lambda: logging.handlers.SysLogHandler())
enable_transport("my_syslog")
```

### `SumoLogicHandler` deep-dive

Requires the `[sumologic]` extra (`requests`). `make_sumo_logic_handler()` returns
`None` (a **soft no-op**) when `SUMO_LOGIC_COLLECTOR_URL` is unset *or* when `requests`
isn't installed — so enabling the transport without the extra never errors.

Behavior: `emit()` only appends to an in-memory bounded `deque` (a daemon thread does
the network I/O — **never blocks, never raises**). It ships **NDJSON** (via
`JsonLogFormatter`), gzips bodies at/above the threshold, batches by count **and**
byte size (Sumo's 100 KB–1 MB sweet spot), and uses a `urllib3` `Retry` adapter that
retries `408/429/5xx` with backoff+jitter, **honors `Retry-After`**, and never retries
`401`/other 4xx. Flushes on interval, on `batch_size`, and at `atexit`. Counters:
`sumologic.transport.{posts,ok,error,throttled,dropped,records}`.

```python
import os
os.environ["SUMO_LOGIC_COLLECTOR_URL"] = "https://collectors.sumologic.com/receiver/v1/http/XXXX"
os.environ["SUMO_LOGIC_LOGGING_ENABLED"] = "true"
configure_transports(sumo_logic=True)   # or rely on the env flag alone
```

| Env var | Default | Purpose |
|---|---|---|
| `SUMO_LOGIC_COLLECTOR_URL` | — (required) | HTTP Source endpoint (unset → transport stays off) |
| `SUMO_LOGIC_COLLECTOR_TOKEN` | — | `x-sumo-token` auth header |
| `SUMO_LOGIC_SOURCE_CATEGORY` | — | `X-Sumo-Category` |
| `SUMO_LOGIC_SOURCE_HOST` | — | `X-Sumo-Host` |
| `SUMO_LOGIC_FIELDS` | — | `X-Sumo-Fields` (`k=v,k2=v2`) |
| `SUMO_LOGIC_BATCH_SIZE` | `100` | records per POST |
| `SUMO_LOGIC_MAX_BATCH_BYTES` | `1000000` | byte cap per POST |
| `SUMO_LOGIC_GZIP_THRESHOLD` | `1024` | gzip bodies ≥ this |
| `SUMO_LOGIC_FLUSH_INTERVAL` | `5.0` | timer flush (s) |
| `SUMO_LOGIC_MAX_BUFFER` | `10000` | buffer cap (oldest dropped on overflow) |
| `SUMO_LOGIC_TIMEOUT` | `5.0` | POST timeout (s) |

### v4.0.0 transports — shared `_BufferedShipper` contract

All v3 network/storage transports subclass `_BufferedShipper` — the same guarantees as
Sumo Logic: **never block the caller, never raise, bounded buffer with drop counting**,
background flush thread, batch by count and bytes, flush at `atexit`. Factories return
`None` (soft no-op) when required env vars are unset or the pip extra is missing.

| Name | Key env vars (factory soft no-op if unset) |
|---|---|
| `panther` | `PANTHER_API_HOST`, `PANTHER_LOG_SOURCE_ID` / `PANTHER_LOG_SOURCE_TOKEN` (or `PANTHER_API_KEY`) |
| `file` | `FILE_LOG_PATH` (+ optional `FILE_LOG_ROOT`, `FILE_LOG_ROTATION`, `FILE_LOG_MAX_BYTES`, …) |
| `blob` | `BLOB_*` connection/container settings |
| `sql` | `SQL_LOG_DSN`, `SQL_LOG_TABLE` |
| `nosql` | `NOSQL_LOG_URI`, `NOSQL_LOG_DATABASE`, `NOSQL_LOG_COLLECTION` |
| `adx` | `ADX_CLUSTER_URI`, `ADX_DATABASE` |
| `event_hubs` | `EVENTHUB_FQNS`, `EVENTHUB_NAME` |

Install all transport deps with `pip install 'vibey[bootstrap-all]'`. See
`examples/39_v3_transports.py`.
