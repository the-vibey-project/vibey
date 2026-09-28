---
id: skill-2-python-the-v1-core-4-phase-bootstrap-eeab716b7e
purpose: 2 python the v1 core 4 phase bootstrap
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-core/SKILL.md
requires: ["skill-1-installation-extras-8ce6dcebe6"]
links: []
---

## 2. Python: the v1 core (4-phase bootstrap)

### The problem and the solution

Configuration loading wants logging to report progress; App Insights logging wants
configuration to initialize. The library breaks the cycle in four phases:

1. **Console logging** — works immediately (always).
2. **Telemetry from env** — try App Insights from `APPLICATIONINSIGHTS_CONNECTION_STRING`.
3. **Configuration load** — Azure App Configuration + Key Vault → `os.environ`.
4. **Telemetry upgrade** — if the connection string only arrived via config, upgrade to App Insights now.

### Quick start (the canonical pattern)

```python
import os
from vibey_bootstrap import initialize_application, get_bootstrap_logger

logger = get_bootstrap_logger(__name__)     # works before bootstrap completes
config_repo = initialize_application()       # runs all four phases
# Every App Config + Key Vault value is now in os.environ:
db_host = os.getenv("DATABASE_HOST")
```

### Configuration precedence & the local-override rule

Lookup order, highest priority first:

1. **Environment variables** (`os.environ`) — local overrides always win
2. **In-process cache** (prior `get_value()` results)
3. **Azure App Configuration** (Key Vault references auto-resolved)
4. **Key Vault** (direct, via the secrets repository)
5. **Default values**

`load_to_environ()` **never overwrites an existing `os.environ` key** — so anything
set by `local.settings.json` (or your shell) survives, and only *new* remote keys are
added. App Config can store Key Vault *references* (a JSON `{"uri": "...vault.../secrets/..."}`);
the provider resolves them transparently, so `os.getenv("DATABASE_PASSWORD")` returns
the actual secret, not the URI.

### API reference — entry points

```python
from vibey_bootstrap import (
    initialize_application, get_bootstrap_logger,
    ensure_bootstrap_logging, create_enhanced_config_repository,
)
```

| Symbol | Signature | Behavior |
|---|---|---|
| `initialize_application` | `(secrets_repository: SecretsRepositoryInterface \| None = None) -> EnhancedConfigRepositoryInterface` | Runs the 4-phase bootstrap; loads all config to `os.environ`; caches the repo for `refresh_setting()`. Raises `RuntimeError` on unrecoverable failure. |
| `get_bootstrap_logger` | `(name: str) -> logging.Logger` | A logger usable immediately; auto-configures bootstrap logging on first call. |
| `ensure_bootstrap_logging` | `() -> None` | Idempotent bootstrap-logging setup. |
| `create_enhanced_config_repository` | `(app_config_connection_string=None, secrets_repository=None, auto_load_to_environ=False) -> EnhancedConfigRepositoryInterface` | Factory for the config repository. |

### API reference — classes

```python
from vibey_bootstrap import (
    ApplicationBootstrap, BootstrapLogger, ExtraFieldsFormatter,
    TelemetryManager, telemetry_manager,
    EnhancedConfigRepository, SecretsRepository,
)
```

- **`ApplicationBootstrap(secrets_repository=None)`** — orchestrator. `.initialize()`
  runs the four phases and returns the repo; `.get_config_repository()`,
  `.is_bootstrap_completed()`.
- **`BootstrapLogger`** — `.configure_bootstrap_logging(level=None)` (class method;
  level falls back to `LOG_LEVEL` env, then `INFO`).
- **`ExtraFieldsFormatter`** — `logging.Formatter` that appends `extra={}` fields to
  each line. (v1 lives in `services.bootstrap_logging`; a v2 variant lives in
  `vibey_bootstrap.logging` — see the `vibey-bootstrap-primitives` skill.)
- **`TelemetryManager` / `telemetry_manager`** (singleton) —
  `.configure(connection_string=None, allow_reconfigure=False) -> bool` and
  `.try_upgrade_from_config(config_repository) -> bool`. Best-effort: always falls
  back to console logging rather than raising.
- **`EnhancedConfigRepository`** — key methods:

  | Method | Purpose |
  |---|---|
  | `get_value(key, default=None) -> str \| None` | env → cache → App Config → Key Vault → default |
  | `get_secret_value(key, default=None) -> str \| None` | direct Key Vault lookup |
  | `get_all_values() -> dict[str, str]` | merged view (env wins) |
  | `load_to_environ() -> int` | populate `os.environ`; returns count of **new** keys |
  | `refresh() -> None` | clear cache + reload (used by `refresh_setting`) |
  | `get_repository_metrics() -> dict` | availability + counts |
  | `is_app_config_available()` / `is_key_vault_available()` | feature probes |

- **`SecretsRepository(vault_url=None)`** — `get_secret`, `set_secret`,
  `delete_secret`, `list_secrets`, `is_available` (reads `AZURE_KEY_VAULT_URL`).

### Interfaces (DI / type hints) and exceptions

```python
from vibey_bootstrap import (
    ApplicationBootstrapInterface, BootstrapLoggerInterface,
    TelemetryManagerInterface, EnhancedConfigRepositoryInterface,
    SecretsRepositoryInterface,
    RepositoryError, ConfigurationError, KeyVaultError,   # ConfigurationError, KeyVaultError subclass RepositoryError
)
```

### v1 environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `TelemetryManager` | App Insights telemetry |
| `AZURE_APP_CONFIGURATION_CONNECTION_STRING` | `EnhancedConfigRepository` | App Configuration endpoint |
| `AZURE_APPCONFIG_ENDPOINT` | health probe / AAD auth | App Config endpoint (credential-based) |
| `AZURE_KEY_VAULT_URL` | `SecretsRepository` | Key Vault endpoint |
| `LOG_LEVEL` | bootstrap + telemetry logging | `DEBUG`/`INFO`/`WARNING`/`ERROR` (default `INFO`) |
| `FUNCTIONS_WORKER_RUNTIME` | bootstrap logging | presence triggers Azure-Functions log setup |
