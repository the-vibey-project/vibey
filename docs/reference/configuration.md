# Configuration reference: `vibey.toml`

The schema below is fully implemented
and unit-tested in
[`src/vibey/domain/config.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/domain/config.py)
(`VibeyConfig`, `parse_config`, `parse_toml_string`) and
[`src/vibey/infrastructure/config_loader.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/infrastructure/config_loader.py)
(`load_config_from_path`). `vibey new` reads the `[notifications]` and
`[telemetry]` tables from the repository's `vibey.toml` and stores them in the
project record; the worker and lifecycle repository consume those stored
tables. The other schema tables remain documented inputs for future wiring.

## What is read at runtime today

| Input | Read by | What it controls |
|---|---|---|
| `./vibey.toml`, key `[features].qwenloop` | `vibey doctor` (`cli/main.py` `_qwenloop_feature_enabled`) | Whether `qwenloop` is added to the health sweep. The file is read from the current directory with `parse_toml_string`; a missing or malformed file counts as `qwenloop = false`. |
| `./vibey.toml`, `[notifications]` and `[telemetry]` | `vibey new` (`infrastructure/config_loader.py`) | Copies project notification channels and the telemetry switch into the stored project config. |
| The project's stored record (the `project` row: `max_cycles` column and `config` JSON) | `vibey worker`, lifecycle repository, and job handlers | Cycle cap, per-cycle spend and turn caps, skills-context policy, notification delivery, telemetry, and (in principle) `features.qwenloop` — see below. |
| Environment variables | See [Environment variables](#environment-variables) | Database DSN, the migration-lock wait, the qwenloop switch, the sovereign DESIGN provider's evidence directory. |

The project record is written once, at creation, by one of two paths:

- **`vibey new`** (see the [CLI reference](cli.md)): `--max-cycles` is stored
  in the `project.max_cycles` column; `--max-cycle-dollars`,
  `--max-cycle-turns`, `--skills-context-mode` and `--skills-context-budget`
  are stored in the `config` JSON as `max_cycle_dollars`, `max_cycle_turns`
  and `skills_context` (the last only when the mode is not `off`). When the repo
  contains `vibey.toml`, its `[notifications]` and `[telemetry]` tables are
  copied into that same JSON record.
- **The Kubernetes operator** ([ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md)):
  a `VibeyProject` spec's `maxCycles` sets the column (default `10`);
  `repo`, `maxCycleDollars`, `maxCycleTurns` and `skillsContext` are stored in
  the `config` JSON. `spec.engines` is stored as a flat `engines` list that
  nothing reads back yet.

Neither path passes through `parse_config`. No command updates these values on
an existing project.

Neither path writes a `features` key either, so the worker's check of the
stored `features.qwenloop` is always false for projects created today:
**`VIBEY_FEATURE_QWENLOOP` is the switch that reaches the worker.**

## Environment variables

| Variable | Read by | Effect |
|---|---|---|
| `VIBEY_PG_URL` | `bootstrap.database_url()` (every command that opens the queue) | PostgreSQL DSN. Required; there is no default — `vibey` exits with `DatabaseNotConfigured` if it is unset. |
| `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` | `bootstrap.build_app()` via `PostgresMigrator.from_environ` (every command that opens the queue) | How long a start waits for another process's migration before failing with `MigrationLockTimeout`, which names the backend pid holding the lock. Seconds, fractions allowed and rounded up to the next millisecond; default `300`; `0` waits indefinitely. Unset or blank means the default; anything that is not a number from `0` to `2147483.647` fails the start with `InvalidMigrationLockTimeout` before the pool opens, rather than falling back. See [the migration lock](../plans/data-model.md#71-the-migration-lock). |
| `VIBEY_FEATURE_QWENLOOP` | `vibey worker` (`bootstrap.qwenloop_enabled`), `vibey doctor` (`cli/main.py` `_qwenloop_feature_enabled`), and `load_config_from_path` | Overrides `features.qwenloop`. `1`, `true`, `yes`, `on` (case-insensitive, surrounding whitespace ignored) enable; any other value disables. When set it wins over both the stored project record and `./vibey.toml`. Only `load_config_from_path` rejects a non-boolean value. For the worker, enabling it adds a qwenloop adapter and makes qwenloop the standby engine for BUILD rotation. |
| `VIBEY_EVIDENCE_DIR` | `vibey work --provider qwenloop`, `vibey worker --provider qwenloop` | Directory of reading that the sovereign DESIGN provider's research stage draws from ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)). Unset, research refuses rather than inventing a source, and the phase stops there. |

### Operational surface environment variable overlay

Every operational surface setting can be configured or overridden via environment variables.
An environment variable always takes precedence over the corresponding key in `vibey.toml`.
An empty or whitespace-only value counts as unset.

| Variable | Target Table & Key | Description |
|---|---|---|
| `VIBEY_TRACKER_URL` | `[tracker].url` | Plane API endpoint URL |
| `VIBEY_TRACKER_TOKEN` | `[tracker].token` | Plane user or API token |
| `VIBEY_TRACKER_WORKSPACE_SLUG` | `[tracker].workspace_slug` | Plane workspace slug |
| `VIBEY_TRACKER_PROJECT_ID` | `[tracker].project_id` | Plane project UUID |
| `VIBEY_DOCS_URL` | `[docs].url` | BookStack base URL |
| `VIBEY_DOCS_TOKEN_ID` | `[docs].token_id` | BookStack API token ID |
| `VIBEY_DOCS_TOKEN_SECRET` | `[docs].token_secret` | BookStack API token secret |
| `VIBEY_DOCS_BOOK_ID` | `[docs].book_id` | BookStack book integer ID |
| `VIBEY_SECRETS_URL` | `[secrets].url` | OpenBao server URL |
| `VIBEY_SECRETS_TOKEN` | `[secrets].token` | OpenBao access token |
| `VIBEY_FILES_URL` | `[files].url` | Nextcloud WebDAV URL |
| `VIBEY_FILES_USER` | `[files].user` | Nextcloud WebDAV username |
| `VIBEY_FILES_PASSWORD` | `[files].password` | Nextcloud WebDAV password |
| `VIBEY_EMAIL_SMTP_HOST` | `[email].smtp_host` | Postfix/SMTP host |
| `VIBEY_EMAIL_SMTP_PORT` | `[email].smtp_port` | SMTP port (e.g. 587 or 465) |
| `VIBEY_EMAIL_USERNAME` | `[email].username` | SMTP username |
| `VIBEY_EMAIL_PASSWORD` | `[email].password` | SMTP password |
| `VIBEY_EMAIL_FROM` | `[email].from_email` | Sender address |
| `VIBEY_SMS_URL` | `[sms].url` | Kannel sendsms gateway URL |
| `VIBEY_SMS_USERNAME` | `[sms].username` | Kannel sendsms username |
| `VIBEY_SMS_PASSWORD` | `[sms].password` | Kannel sendsms password |
| `VIBEY_SMS_SENDER` | `[sms].sender` | SMS sender ID/number |
| `VIBEY_MESSAGING_URL` | `[messaging].url` | Matrix Synapse URL |
| `VIBEY_MESSAGING_TOKEN` | `[messaging].token` | Matrix access token |
| `VIBEY_MESSAGING_ROOM_ID` | `[messaging].room_id` | Matrix target room ID |
| `VIBEY_CONFIG_STORE_URL` | `[config_store].url` | Infisical URL |
| `VIBEY_CONFIG_STORE_TOKEN` | `[config_store].token` | Infisical token |
| `VIBEY_CONFIG_STORE_PROJECT_ID` | `[config_store].project_id` | Infisical project UUID |
| `VIBEY_CONFIG_STORE_ENVIRONMENT` | `[config_store].environment` | Infisical environment slug |
| `VIBEY_CACHE_URL` | `[cache].url` | Redis URL (`redis://...`) |
| `VIBEY_BUS_URL` | `[bus].url` | RabbitMQ Management URL |
| `VIBEY_BUS_USERNAME` | `[bus].username` | RabbitMQ username |
| `VIBEY_BUS_PASSWORD` | `[bus].password` | RabbitMQ password |
| `VIBEY_BLOB_URL` | `[blob].url` | Garage S3 URL |
| `VIBEY_BLOB_ACCESS_KEY` | `[blob].access_key` | Garage S3 access key |
| `VIBEY_BLOB_SECRET_KEY` | `[blob].secret_key` | Garage S3 secret key |
| `VIBEY_BLOB_REGION` | `[blob].region` | Garage S3 region |
| `VIBEY_SIEM_URL` | `[siem].url` | Wazuh indexer endpoint |
| `VIBEY_SIEM_USERNAME` | `[siem].username` | Wazuh indexer username |
| `VIBEY_SIEM_PASSWORD` | `[siem].password` | Wazuh indexer password |
| `VIBEY_SIEM_INDEX` | `[siem].index` | Wazuh index name |

## Schema semantics

`domain/config.py` is a pure, stdlib-only module with no filesystem access
of its own (reading the file is an infrastructure concern). Every table
below is optional; omit any of them and the listed defaults apply.

Validation is partial. The Type column is the intended shape. `parse_config`
type-checks every key except `[budget].*`, `[phases.*].engines` (not even
checked to be a list — a bare string is split into single-character engine
ids), `[phases.*].parallelism`, the elements of `[isolation].egress` and
`[provision].plugins`, and the values of `[engines].weights`; those are stored
as written. No numeric range is checked outside `[qwenloop]`
(`idle_timeout_seconds ≥ 0`, `startup_timeout_seconds > 0`,
`context_window > 0`), booleans pass integer checks (`max_cycles = true` is
accepted), and `[deploy].target` / `[deploy].iac` accept any string.

Engine names: an unknown engine name in `[engines].enabled` or as a key of
`[engines].weights` fails validation with a `ConfigError` naming the offending
path, as does `qwenloop` in `[engines].enabled` or any `[phases.*].engines`
list before `features.qwenloop = true`. `[phases.*].engines` entries are
otherwise not validated — unknown names and engines outside
`[engines].enabled` are accepted as written — and `[engines].weights` may name
`qwenloop` without the feature flag. Unknown tables (for example
`[skills_context]`) are silently ignored. All of this applies only when
something calls `load_config_from_path`/`parse_config`, which nothing in this
codebase does outside tests.

## `[project]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | *required* | Project name. |
| `repo` | string | `"."` | Path to the repository this project builds against. |
| `max_cycles` | integer | `10` | Cap on delivery cycles. Not range-checked. The live value is the `project.max_cycles` column set by `vibey new --max-cycles` or `spec.maxCycles`. |
| `strict_loopback` | boolean | `false` | When true, tightens review-loopback routing ([ADR-0010](../architecture/decisions/0010-review-loopback-routing.md)). |

## `[isolation]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `level` | string | `"worktree"` | One of `worktree`, `container`, `vm`. |
| `allow_push` | boolean | `false` | Whether a worktree may push to a remote. |
| `egress` | array of strings | `[]` | Allowed egress destinations when network isolation is otherwise closed. Element types are not validated. |

`worktree` isolation is the one active runtime behavior today: every job
and phase runs in an isolated ephemeral git worktree. `container` and `vm`
are schema-valid values, and the container hardening path
(`infrastructure/container/config.py`'s `ContainerConfig`,
`infrastructure/container/runtime.py`'s `OciContainerExecutor`) is
implemented and unit-tested, but it is never constructed by `bootstrap.py`
or anything else outside `infrastructure/container/` and its tests, and
`[isolation]` itself is never read from a real `vibey.toml`. Setting
`level = "container"` has no effect today; see
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/main/SECURITY.md#1-worktree--container-isolation-runtime-adr-0008-task-91)
for the same disclosure.

## `[budget]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `max_dollars_per_cycle` | float or unset | unset (no cap) | Intended per-cycle spend cap. Not validated. |
| `max_dollars_total` | float or unset | unset (no cap) | Intended total spend cap across the project's lifetime. Not validated. |
| `max_turns_per_item` | integer or unset | unset (no cap) | Intended per-work-item turn cap; the implemented cap (`max_cycle_turns`) is per cycle. Not validated. |

None of these keys is read at runtime. The live brake is the project's stored
`max_cycle_dollars` / `max_cycle_turns` (set by `vibey new --max-cycle-dollars`
/ `--max-cycle-turns`, or the operator's `spec.maxCycleDollars` /
`spec.maxCycleTurns`). `LedgerBudgetSource` sums them live from the current
cycle's `TurnCompleted` and `BudgetSpent` ledger events — never estimated
ahead of time — and tripping either parks a `budget_exhausted` gate. With
neither set, spend is uncapped.

`vibey cost` prints caps from a `budget` key in the stored project config
(`max_dollars_per_cycle`, `max_dollars_total`) that nothing writes, so it
currently shows the fallbacks $40.00 (cycle) and $250.00 (total) rather than
the real cap.

## `[verify]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `require_independent_review` | bool | `false` | When `true`, `build.verify` always fails as `VIBEY` if the reviewing engine is the implementer, even when the configured pool has nobody else. When `false` (the default) a pool that cannot supply a second reviewer gets a self-review, recorded as a `DecisionRecorded` in the ledger so the weakened independence is visible. See [ADR-0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md). |

Unlike `[budget]` above, this key **is** read at runtime, by
`bootstrap.build_full_worker`.

## `[engines]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | array of strings | `["claudeloop", "codexloop", "cursorloop", "agyloop", "opencode"]` | Must be a subset of the known engines below. If omitted while `features.qwenloop = true`, `qwenloop` is appended to the default automatically; an explicit list is never extended. |
| `weights` | table of string→int | `{}` | Per-engine weight for smooth weighted round robin ([ADR-0005](../architecture/decisions/0005-smooth-weighted-round-robin.md)). Keys must be known engines; values are not validated. |

Known engine ids: `claudeloop`, `codexloop`, `cursorloop`, `agyloop`,
`opencode`, and `qwenloop` (valid in `enabled` and `[phases.*].engines` only once
`features.qwenloop = true`).

## `[phases.design]`, `[phases.build]`, `[phases.review]`

Each phase table accepts the same three fields:

| Field | Type | Default (per phase) | Notes |
|---|---|---|---|
| `effort` | string | `design` = `high`, `build` = `low`, `review` = `high` | One of `trivial`, `low`, `standard`, `high`, `max`. |
| `engines` | array of strings or unset | unset (falls back to `[engines].enabled`) | Engine ids this phase may use. Not validated against known engines or `[engines].enabled`, and not checked to be a list. |
| `parallelism` | integer or unset | unset | Per-phase worker concurrency override. Not validated. |

```toml
[phases.build]
effort = "standard"
engines = ["claudeloop", "agyloop"]
parallelism = 4
```

## `[provision]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `plugins` | array of strings | `[]` | Reserved for agent-surface provisioning plugins ([ADR-0011](../architecture/decisions/0011-agent-surface-provisioning.md)). Parsed and stored only; `infrastructure/provision/agent_surface.py` does not read it today. |

## `[deploy]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `false` | Opts the project into the DEPLOY_DESIGN / DEPLOY_EXECUTE / DEPLOY_REVIEW stage set. |
| `target` | string | `"azure"` | Deployment target. Azure is the only implemented target today; other strings are accepted by `parse_config`. |
| `iac` | string | `"bicep"` | Infrastructure-as-code format used by the deploy adapters; other strings are accepted by `parse_config`. |

## `[notifications]`

Notifications are opt-in because desktop alerts and outbound webhooks are
side effects. `vibey new` copies this table into the project's stored config;
`build_app()` constructs one service and applies the project policy when a
worker raises a gate or a project changes phase.

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `false` | Enables delivery for this project. |
| `desktop` | boolean | `true` | Sends desktop alerts when enabled. |
| `webhooks` | array of tables | `[]` | Each table requires `url` and may include a `secret`; URLs must be public `http://` or `https://` destinations at publish time (loopback, private, link-local, reserved, local-name, credential-bearing, and redirecting endpoints are rejected). Secrets sign the JSON payload with `X-Vibey-Signature: sha256=...`. |

```toml
[notifications]
enabled = true
desktop = true

[[notifications.webhooks]]
url = "https://ops.example/vibey"
secret = "replace-me"
```

## `[telemetry]`

`build_app()` constructs the in-process tracer and metrics recorder. Workers
record job spans, queue latency, phase duration, engine selections, engine
turns, handoff-gate failures, and cost spend. The recorder is available to
the running application but has no external exporter yet.

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `true` | Set `false` to disable runtime tracing and metrics for this project. |
| `export_path` | string or unset | unset | Reserved for a future file/exporter integration; it is validated and stored. |

## `[features]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `qwenloop` | boolean | `false` | Must be `true` before `qwenloop` can appear in `[engines].enabled` or any `[phases.*].engines` list. |

Runtime: `vibey doctor` reads this key from `./vibey.toml`. `vibey worker`
reads it from the project's stored config record, which `vibey new` and the
operator never write, so for the worker `VIBEY_FEATURE_QWENLOOP=1` is
currently the only way to enable qwenloop. The environment variable overrides
both. Without it, the worker's default adapter set has no qwenloop adapter.

## `[qwenloop]`

Only meaningful when `features.qwenloop = true`. In engine-driven BUILD
rotation qwenloop is a standby tier — selected only when no paid engine is
eligible ([ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)).
It is also the sovereign DESIGN provider, selected explicitly with
`vibey work --provider qwenloop` or `vibey worker --provider qwenloop`
([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)).
These keys mirror the runner's own `QwenConfig`
(`src/vibey_runners/qwen/src/qwenloop/domain/config.py`, which additionally
has `max_turns`, default `40`, must be positive); `parse_config` validates
them into `VibeyConfig`, but nothing passes them to the runner.

| Field | Type | Default | Notes |
|---|---|---|---|
| `backend` | string | `"auto"` | One of `auto`, `llama.cpp`, `vllm`. |
| `portable_profile` | string | `"qwen2.5-coder-14b-q5-k-m"` | Model profile used on the portable (CPU/quantized) backend path. |
| `nvidia_profile` | string | `"qwen2.5-coder-14b-bf16"` | Model profile used when an NVIDIA GPU backend is selected. |
| `idle_timeout_seconds` | integer | `900` | Must be non-negative; how long an idle local model stays warm. |
| `startup_timeout_seconds` | integer | `180` | Must be positive. |
| `context_window` | integer | `32768` | Must be positive. |

## Operational surfaces (sovereign defaults, declared-only paid relays)

Each table is optional: an omitted table (or an omitted key) leaves the
surface on its in-memory default, so a project runs with no external service
configured at all. A real endpoint declares a self-hosted sovereign service
(or a paid relay). `parse_config` validates all eight into `VibeyConfig`;
`bootstrap.build_app` wires the concrete adapter only when every required key
for that surface is present, otherwise the in-memory default.

## `[tracker]` (sovereign default: Plane)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the Plane instance, e.g. `https://plane.example.com`. |
| `token` | string | unset | API token (`X-API-Key`, or Bearer for OAuth). |
| `workspace_slug` | string | unset | Workspace slug from the Plane URL, e.g. `my-team`. Required with `project_id`: Plane's work-item routes are workspace-scoped (`/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`). |
| `project_id` | string | unset | Plane project UUID. Required with `workspace_slug`. |

## `[docs]` (sovereign default: BookStack)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the BookStack instance. |
| `token_id` | string | unset | API token ID (`Token <id>:<secret>` auth). |
| `token_secret` | string | unset | API token secret. |
| `book_id` | integer | unset | Book pages are created under. Must be an integer, never a boolean. |

## `[secrets]` (sovereign default: OpenBao)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the OpenBao instance, e.g. `http://localhost:8200`. |
| `token` | string | unset | OpenBao root or service token (`X-Vault-Token`). |

## `[files]` (sovereign default: Nextcloud)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the Nextcloud instance (WebDAV). |
| `user` | string | unset | WebDAV username. |
| `password` | string | unset | WebDAV password or app token. |

## `[email]` (sovereign default: Forward Email)

| Field | Type | Default | Notes |
|---|---|---|---|
| `smtp_host` | string | unset | SMTP relay host. |
| `smtp_port` | integer | unset | `587` for STARTTLS submission, `465` for implicit TLS (`SMTP_SSL`). Must be an integer, never a boolean. |
| `username` | string | unset | SMTP username (also the default sender). |
| `password` | string | unset | SMTP password. Login and STARTTLS are skipped without it. |
| `from_email` | string | unset | Sender address; defaults to `username`, then `vibey@localhost`. |

## `[sms]` (gateway: Kannel; handsets: Fossify Messages)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the Kannel smsbox instance (`/cgi-bin/sendsms`). |
| `username` | string | unset | Kannel sendsms username. |
| `password` | string | unset | Kannel sendsms password. |
| `sender` | string | unset | Sender phone number or alphanumeric origin. |

## `[messaging]` (sovereign default: Matrix)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the Matrix homeserver. |
| `token` | string | unset | Access token (Bearer). |
| `room_id` | string | unset | Default room, e.g. `!room:example.org`. |

## `[config_store]` (sovereign default: Infisical)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the Infisical instance. |
| `token` | string | unset | API access token (Bearer) or machine identity token. |
| `project_id` | string | unset | Infisical project ID. |
| `environment` | string | `"dev"` | Environment slug secrets are read from and written to. |

## `[cache]` (sovereign default: Redis)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Redis connection URL, e.g. `redis://localhost:6379/0`. |

## `[bus]` (sovereign default: RabbitMQ)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Base URL of the RabbitMQ Management API, e.g. `http://localhost:15672`. |
| `username` | string | unset | RabbitMQ management username. |
| `password` | string | unset | RabbitMQ management password. |

## `[blob]` (sovereign default: Garage, S3 API)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Garage S3 endpoint URL, e.g. `http://localhost:3900`. |
| `access_key` | string | unset | S3 API access key ID. |
| `secret_key` | string | unset | S3 API secret access key. |
| `region` | string | `"us-east-1"` | S3 signing region (must match server configuration). |

## `[siem]` (sovereign default: Wazuh Indexer)

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | unset | Wazuh indexer REST endpoint, e.g. `http://localhost:9200`. |
| `username` | string | unset | Indexer username for Basic auth (omitted when security is disabled). |
| `password` | string | unset | Indexer password. |
| `index` | string | `"vibey-audit"` | Target audit index name. |

## Skills context (project config record — not a `vibey.toml` table) { #skills_context }

`VibeyConfig` has no `skills_context` field; a `[skills_context]` table in
`vibey.toml` is silently ignored by `parse_config`. The values live in the
project's stored config record and are written by
`vibey new --skills-context-mode` / `--skills-context-budget` (only when the
mode is not `off`; see the [CLI reference](cli.md#vibey-new-name)) or by the
operator's `spec.skillsContext` object (copied verbatim).
`compiler_from_config` (`infrastructure/skills_context.py`) reads them when
`bootstrap.build_full_worker` builds the worker ([ADR-0031](../architecture/decisions/0031-skills-context-packets-over-a-process-boundary.md)).

| Field | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | `"off"` | `off`, `shadow` (measure only, never changes prompts), or `inject` (append successful packets to BUILD prompts). Any other value raises when the worker is built. |
| `budget` | integer | `6000` | Token budget for retrieval, 1,000–32,000 (enforced by the `vibey new` flag, the operator CRD, and `VibeySkillsContextCompiler`). |
| `timeout_seconds` | number | `120.0` | Skills compile timeout; must be positive. Settable only through `spec.skillsContext`. |
| `command` | array of non-empty strings | unset (`<python> -m vibey_skills.cli`) | Override for the `vibey-skills` command. Read by `compiler_from_config` but not declared in the `VibeyProject` CRD schema, so neither creation path sets it today. |
| `index_path` | string | `.vibey/skills-context/index` under the repo | Path to the skills index; relative paths resolve under the repo. Read by `compiler_from_config` but not declared in the CRD schema, so neither creation path sets it today. |

## Automated review checks (project config record — not a `vibey.toml` table) { #review }

`VibeyConfig` has no `review` field; a `[review]` table in `vibey.toml` is
silently ignored by `parse_config`, and `vibey.toml` is never loaded by the
worker anyway. The values live in the project's stored config record under a
`review` object, and `SubprocessAutomatedReviewRunner.from_config`
(`infrastructure/build/automated_review_runner.py`) reads them when
`bootstrap.build_full_worker` builds the worker. They are the commands
`review.demo` shells out to: a non-zero exit becomes a `Severity.HIGH`
`security` finding or a `Severity.MEDIUM` `code_review` finding, which sends
REVIEW back to BUILD.

Neither `vibey new` nor the operator's `VibeyProject` spec writes this object
today, the same way `skills_context.command` and `skills_context.index_path`
are read but never written; the record is written directly. Until one of them
does, an unconfigured project runs REVIEW's code-review check and no security
check at all — which is what the empty `security_commands` default states
plainly, rather than running a scan that inspects nothing and reports success.
vibey's own `bandit -q -r src/vibey` is enforced for real as gate 6 of
`ci.yml`, on every pull request, independently of this.

| Field | Type | Default | Notes |
|---|---|---|---|
| `security_commands` | array of arrays of non-empty strings | `[]` (no security check runs) | Security checks. There is deliberately no default: any baked-in command names both a tool and a layout, and `bandit -q -r <path that does not exist>` exits 0 — a wrong default reports a passing security check that examined zero files. Configure this to get one. |
| `code_review_commands` | array of arrays of non-empty strings | `[["ruff", "check", ".", "--exclude", ".vibey", "--exclude", ".claudeloop", "--exclude", ".codexloop", "--exclude", ".cursorloop", "--exclude", ".agyloop", "--exclude", ".opencodeloop"]]` | Code-review checks. The default excludes vibey's own machinery inside the repo — worktrees under `.vibey/` and the engines' state dirs — which are not the product. An explicit `[]` disables the check. |

A malformed `review` object (not an object, a command list that is not a list
of non-empty string arrays) raises when the worker is built, rather than
silently running nothing.

## Full example

This is a valid file exercising most of the schema that `parse_config`
validates. `vibey new` also copies its `[notifications]` and `[telemetry]`
tables into the project's stored config (see the top of this page).

```toml
[project]
name = "my-app"
repo = "."
max_cycles = 15

[isolation]
level = "container"
allow_push = false

[budget]
max_dollars_per_cycle = 15.0
max_dollars_total = 250.0

[engines]
enabled = ["claudeloop", "agyloop"]
weights = { claudeloop = 3, agyloop = 1 }

[phases.design]
effort = "high"

[phases.build]
effort = "low"
parallelism = 2

[phases.review]
effort = "high"

[deploy]
enabled = true
target = "azure"
iac = "bicep"

[notifications]
enabled = true
desktop = false

[[notifications.webhooks]]
url = "https://ops.example/vibey"
secret = "replace-me"

[telemetry]
enabled = true

[features]
qwenloop = true

[qwenloop]
backend = "auto"
idle_timeout_seconds = 600
```
