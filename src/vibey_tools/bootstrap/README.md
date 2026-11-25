---
description: "Reference for vibey-bootstrap, the cross-cutting layer for Azure Functions, FastAPI services and AKS workers inside vibey-engine: install, the four-phase bootstrap, extras, examples and gates."
---

# vibey-bootstrap: bootstrap logging, configuration and telemetry in one call

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `vibey_bootstrap` is a Python library for Azure Functions,
> FastAPI services and AKS workers. One call, `initialize_application()`, sets up logging, loads
> Azure App Configuration and Key Vault values into `os.environ`, and starts Application Insights.
> It ships inside `vibey-engine`; install `vibey-engine[azure]` for the Azure core or
> `vibey-engine[bootstrap-all]` for every optional feature. vibey's own hub is built on it.
> `USE_MOCK_BOOTSTRAP=true` runs everything without Azure.

> **Now part of the vibey monorepo.** `vibey-bootstrap` lives in [the-vibey-project/vibey](https://github.com/the-vibey-project/vibey) at [`src/vibey_tools/bootstrap`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap) (vibey ADR-0021). It is not published on its own any more: it ships inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package, so `pip install vibey-engine` installs it (vibey ADR-0037).

> The cross-cutting layer for Azure Functions, FastAPI services, and AKS workers.
> One call bootstraps logging → App Configuration + Key Vault → Application Insights
> and hands you a populated `os.environ`. Everything past that (alerts, tracing,
> Service Bus, ten log transports, a scaffold CLI) is opt-in.

Formerly **azure-bootstrap** — see [NOTICE.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/NOTICE.md).

[![Ships in vibey](https://img.shields.io/pypi/v/vibey-engine?label=ships%20in%20vibey)](https://pypi.org/project/vibey-engine/)
[![Python](https://img.shields.io/pypi/pyversions/vibey-engine.svg)](https://pypi.org/project/vibey-engine/)
[![CI/CD](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-usage%20guide-blue.svg)](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/docs/USAGE.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/LICENSE)

## How to read this page

Daniel was reading the source of vibey's hub and kept meeting an import from `vibey_bootstrap`.

**Daniel:** Professor, this is an Azure library. Why does vibey's hub use it?

**Professor Feynman:** Because a good toolbox is not only for the job it was bought for. The hub
borrows its rate limiter, its metrics and its signature check from here, so vibey does not write
them twice. Read "Why" and the quick start if you are building an app on it; the tables below
are the inventory, for looking up what is on each shelf.

## Why

Every Azure app hits the same startup deadlock: you need logging to report
config loading, but App Insights logging needs config to initialize. Most repos
solve it with a copy-pasted `src/infrastructure/` folder that drifts. This
library is that folder, done once, tested, and versioned.

The **four-phase bootstrap** breaks the cycle:

1. **Console logging** — works immediately, before anything loads.
2. **Telemetry from env** — App Insights if `APPLICATIONINSIGHTS_CONNECTION_STRING` is already set.
3. **Configuration** — Azure App Configuration + Key Vault references → `os.environ`.
   Local values (`local.settings.json`, your shell) always win; nothing is overwritten.
4. **Telemetry upgrade** — if the connection string only arrived via config, upgrade now.

Guarantees: the v1 API surface is preserved byte-identical across the old v2, v3 and v4 lines
(v4 changed only the distribution and import name — see
[MIGRATING-TO-V4.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/MIGRATING-TO-V4.md)).
Those labels name the history of the API, not today's version number: the package now ships
inside `vibey-engine`, versioned with it (0.4.0 after the reset of the whole family to 0.x).
Every extra is opt-in and most are stdlib-only; log transports never block, never raise, and use
a bounded buffer. `USE_MOCK_BOOTSTRAP=true` runs everything without Azure.

## Quick start

```bash
pip install 'vibey-engine[azure]'      # vibey_bootstrap with the App Config / Key Vault / App Insights core
```

```python
import os
from vibey_bootstrap import initialize_application, get_bootstrap_logger

logger = get_bootstrap_logger(__name__)   # usable before bootstrap completes
config_repo = initialize_application()     # runs all four phases

db_host = os.getenv("DATABASE_HOST")       # App Config + Key Vault values are in os.environ
```

Requires Python 3.12+. Falls back to plain environment variables when App
Configuration is not configured, so the same code runs locally and in Azure. A plain
`pip install vibey-engine` also carries the `vibey_bootstrap` package, without the Azure SDKs.

## Worked example: production-grade logging in four lines

```python
from vibey_bootstrap.alerts import install_global_exception_hooks, register_dispatcher
from vibey_bootstrap.bootstrap import ensure_bootstrap
from vibey_bootstrap.logging import configure_logging


def my_email_sender(recipients, subject, html_body):
    ...  # any callable with this signature (Graph, SendGrid, ACS)


configure_logging()
install_global_exception_hooks()
ensure_bootstrap()
register_dispatcher(my_email_sender, recipients=["dev-alerts@example.com"])
```

After this, every line emitted through stdlib `logging` carries a correlation
ID, extra fields render as greppable `key=repr(value)` pairs, noisy third-party
loggers are silenced, and uncaught exceptions fire CRITICAL alerts with dedup,
rate-limiting, and escalation. Runnable version:
[examples/01_quickstart.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/01_quickstart.py).

## Installing the extras

`vibey-engine` exposes the library's optional features through two extras
(root `pyproject.toml`):

| Install | What it adds |
|---|---|
| `pip install vibey-engine` | The `vibey_bootstrap` package itself, and the `vibey-bootstrap` command. |
| `pip install 'vibey-engine[azure]'` | The App Configuration, Key Vault, Azure Identity and Azure Monitor OpenTelemetry SDKs: what the four-phase bootstrap needs in Azure. |
| `pip install 'vibey-engine[bootstrap-all]'` | Everything any optional feature needs: the Azure set plus FastAPI, Service Bus, Blob Storage, Communication Email, Cosmos, Kusto, Event Hubs, APScheduler, tenacity, pypdf, requests, SQLAlchemy, Alembic and PyMongo. |

The finer per-feature extras (`[alerts]`, `[fastapi]`, `[servicebus]`, `[retry]`,
`[logging-all]`, `[db]`, `[email]`, `[http]`, `[aks]` and about 30 more) belong to this tenant's own
`pyproject.toml`. You can only use them from a source checkout, for example
`pip install -e "src/vibey_tools/bootstrap[alerts]"`. The full matrix (what each pulls in, when you
need it) is in the [Usage Guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/docs/USAGE.md#1-installation--extras).

## What's in the box

| Layer | Extra in a source checkout | You get |
| --- | --- | --- |
| **v1 core** | none | Four-phase bootstrap, `EnhancedConfigRepository`, `TelemetryManager` |
| **v2 Tier 1** (always on, stdlib) | none | Structured logging, correlation IDs, masking, `@traced`, counters, error vocabulary, soft-fail, phases, validation, path safety, fail-close env helpers |
| **v2 Tier 2/3** (opt-in) | `[alerts]`, `[fastapi]`, `[servicebus]`, `[retry]`, … | Tiered alerts, FastAPI middleware, health probes, heartbeat, Service Bus consumer + DLQ, webhook auth, ingress hardening, HMAC tokens, AI usage tracker |
| **v3** (opt-in) | `[logging-all]`, `[db]`, `[email]`, `[http]`, `[aks]`, … | Ten log transports, SQLAlchemy + outbox, ACS email, hardened HTTP client, DocumentDB factory, AKS runtime helpers, governance, `vibey-bootstrap` scaffold CLI |

From `vibey-engine`, `[bootstrap-all]` covers every row.

<details>
<summary>Feature inventory by release</summary>

**v2** — structured logging (`ExtraFieldsFormatter`, `correlation_scope`,
secret/email/control-char masking, noisy-logger silencing) · `@traced` with
latency histograms and slow-budget alerts · `alert_dev_team` with WARN / ERROR /
CRITICAL, dedup + rate-limit + escalation, `install_global_exception_hooks` ·
`PipelineError` → `UnrecoverableError` / `TransientError` with `is_unrecoverable`,
soft-fail and per-phase guards · 4-gate attachment classifier (extension → MIME →
size → magic bytes), zip-bomb defense, PDF action stripping, filename sanitizer +
root confinement · Service Bus `handle_message` with dead-letter-vs-abandon
routing and `lock_for_process` · `install_graph_webhook_route` with validation
handshake, clientState verification, dedup, rate limit · AI usage tracker (tokens
+ cost, sliding windows, soft TPM cap) · health probes, FastAPI middleware,
heartbeat + consumer watchdog, dynamic log-level refresh, DLQ digest with
HMAC-signed resubmit tokens, `/api/metrics` aggregator.

**v3** — ten logging transports (console, App Insights, Sumo Logic, Panther, file,
blob, SQL, NoSQL, ADX, Event Hubs; all share `_BufferedShipper` guarantees) ·
SQLAlchemy session factory, Alembic helpers, transactional outbox · `AcsEmailSender`
· hardened sync `requests` session + optional async `httpx` · Mongo/Cosmos client
factory from env · AKS `build_info`, SIGTERM handlers, leader-election stub ·
budget guard + usage tracking hooks · `vibey-bootstrap list|scaffold` for
Terraform/Bicep/Helm/GitOps/CI/policy templates.

Every entry is cataloged by tier in the
[CHANGELOG](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/CHANGELOG.md).

</details>

## The `vibey-bootstrap` command

| Command | What it does |
|---|---|
| `vibey-bootstrap version` | Print the package version. |
| `vibey-bootstrap list` | List the templates: Bicep, CI, GitOps, Helm, policy and Terraform. |
| `vibey-bootstrap scaffold NAME [--out DIR] [--var k=v]` | Copy a template (for example `helm/worker/Chart.yaml.template`) to `--out`, substituting each `--var`. |
| `azbootstrap …` | A deprecated alias from before the 4.0.0 rename; prints a one-line warning, then runs `vibey-bootstrap`. |

## How vibey itself uses it

The conductor follows the family's dogfood rule (ADR-0017): where this library already does a job,
vibey uses it. The hub (`src/vibey/infrastructure/hub/`) takes its request-timing middleware
(`fastapi_middleware`), its metrics snapshot at `/api/metrics` (`metrics`), its per-principal token
bucket (`ratelimit`), its constant-time secret compare (`security`) and a paired device's HMAC
signature check (`auth.hmac`) from here. vibey's `domain/` layer may not import it, because it
carries the Azure SDK and OpenTelemetry; `import-linter` enforces that.

`vibey_bootstrap.gh` is a compatibility alias: the GitHub automation moved out to `vibey_gh`, and
`from vibey_bootstrap.gh import …` now resolves to the same objects. New code should import
`vibey_gh` directly.

## Examples

[examples/](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap/examples/)
holds 42 numbered single-concept files (01 to 39, then 44 to 46) plus 3 end-to-end app templates.
Every file runs with `USE_MOCK_BOOTSTRAP=true` and ends with an `# ── Expected output ──`
block. Start with:

| File | Concept |
| --- | --- |
| [01_quickstart.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/01_quickstart.py) | 30-second setup |
| [03_correlation_scope.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/03_correlation_scope.py) | Correlation IDs across nested calls |
| [09_soft_fail.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/09_soft_fail.py) | Degraded-result pattern |
| [21_consumer_wrapper.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/21_consumer_wrapper.py) | Service Bus handler |
| [39_v3_transports.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/39_v3_transports.py) | All ten log sinks |
| [e2e_azure_function.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/e2e_azure_function.py) | Full Azure Function |
| [e2e_fastapi_pipeline.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/e2e_fastapi_pipeline.py) | Full FastAPI app |
| [e2e_aks_sb_worker.py](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/e2e_aks_sb_worker.py) | Full AKS Service Bus consumer |

Reading order and per-example extras:
[examples/README.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/README.md).

## Docs & links

- **[Documentation](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap/docs)** — usage guide, migration guides, and the generator for the API reference covering all 47 public packages
- **[Usage Guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/docs/USAGE.md)** — installation & extras matrix, every subpackage, three end-to-end recipes, TypeScript/Next.js integration
- **API Reference** — rendered from docstrings and signatures at docs-build time by [`docs/gen_pages.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/docs/gen_pages.py); the standalone Pages site that hosted it has been retired
- **[CHANGELOG](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/CHANGELOG.md)** · **[v1 → v2](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/MIGRATING-FROM-V1.md)** · **[v2 → v3](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/MIGRATING-TO-V3.md)** (additive) · **[v3 → v4](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/MIGRATING-TO-V4.md)** (rename only). These guides predate the move into `vibey-engine`: the `vibey-bootstrap>=4,<5` pin they suggest names a distribution that is no longer released (ADR-0037), so depend on `vibey-engine` instead.
- **[PyPI (`vibey-engine`)](https://pypi.org/project/vibey-engine/)** · **[Issues](https://github.com/the-vibey-project/vibey/issues)** · **[Security policy](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/SECURITY.md)**

## Related projects

Part of the same open-source family — MIT, and all shipping inside the one
[`vibey-engine`](https://pypi.org/project/vibey-engine/) package (vibey ADR-0037):

- **[claudeloop](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude)** · **[codexloop](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex)** — autonomous coding-session runners with the same contract, different vendor
- **[vibey](https://github.com/the-vibey-project/vibey)** — six-phase queue conductor over the loop runners — background reading: the [vibey research paper](https://the-vibey-project.github.io/vibey/main/paper/) ([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)) and the vibey book ([PDF](https://the-vibey-project.github.io/vibey/main/book.pdf), [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub), [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html)).
- **[vibey-skills](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/skills)** — Claude Code plugin marketplace: 153 plugins / 826 Agent Skills (includes a plugin for this library)
- **[clippy-pet](https://github.com/adammatthewsteinberger/clippy-pet)** — the fun one

## Contributing

```bash
git clone https://github.com/the-vibey-project/vibey.git
cd vibey/src/vibey_tools/bootstrap             # vibey-bootstrap lives here in the vibey monorepo
python -m venv .venv && source .venv/bin/activate
pip install -e ../gh && pip install -e ".[test,all,dev]"
pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term   # unit suite with coverage
python -m mypy vibey_bootstrap/ && python -m bandit -r vibey_bootstrap/ -ll -q
```

Those are the commands CI runs (the `tools` job, Python 3.12, 3.13 and 3.14; the static checks on
3.12). The coverage floor is 100% (`fail_under = 100` in this tenant's `pyproject.toml`). CI does
not run the `integration` tests (local I/O against SQLite, mongomock and Azurite) or build docs
for this tenant; run `pytest test/ -m integration` yourself when you change that code.

Branch from `develop` and use Conventional Commits. Details in
[CONTRIBUTING.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/CONTRIBUTING.md);
AI-assistant context lives in
[CLAUDE.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/CLAUDE.md).

## License & attribution

MIT — see [LICENSE](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/LICENSE). Originally developed as
TheViziusGroup/azure-bootstrap while at The Vizius Group; republished as
adammatthewsteinberger/vibey-bootstrap (a standalone repository that has since been folded into
this monorepo) with The Vizius Group's permission — see
[NOTICE.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/NOTICE.md).

## Where next

- [The Usage Guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/docs/USAGE.md):
  every subpackage and the full extras matrix.
- [examples/README.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/bootstrap/examples/README.md):
  the examples in reading order.
- [ADR-0017](https://github.com/the-vibey-project/vibey/blob/develop/docs/architecture/decisions/0017-dogfood-the-family-first.md):
  why vibey uses this library rather than writing its own.

## Say it in one line

vibey-bootstrap gets an Azure app's logging, configuration and telemetry running in one call, and
vibey's own hub is built on its rate limiter, metrics and signature checks.

---

Built by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com) · [more open source](https://vibewithadam.matthewsteinberger.com/open-source)
