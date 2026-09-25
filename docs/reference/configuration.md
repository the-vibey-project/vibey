# Configuration reference: `vibey.toml`

The schema below is fully implemented
and unit-tested in
[`src/vibey/domain/config.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/domain/config.py)
(`VibeyConfig`, `parse_config`, `parse_toml_string`) and
[`src/vibey/infrastructure/config_loader.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/infrastructure/config_loader.py)
(`load_config_from_path`). `vibey new` reads the `[notifications]`,
`[telemetry]`, [`[gates]`](#gates) and [`[engine_environment]`](#engine_environment)
tables from the repository's `vibey.toml` and stores them in the project record; the
worker and lifecycle repository consume those stored tables. The other schema tables
remain documented inputs for future wiring.

## What is read at runtime today

| Input | Read by | What it controls |
|---|---|---|
| `./vibey.toml`, keys `[features].gptossloop`, `[features].qwenloop`, `[features].claudeloop_local` | `vibey doctor` and `vibey loops` (`cli/main.py` `_local_engines_from_toml`, through `LocalEngineSettings`) | Which local engines are added to the health sweep and reported as switched on. The file is read from the current directory with `parse_toml_string`; a missing or malformed file leaves every switch at its default: `gptossloop` on, the others off (ADR-0064). |
| `./vibey.toml`, `[notifications]`, `[telemetry]`, `[gates]` and `[engine_environment]` | `vibey new` (`infrastructure/config_loader.py`) | Copies project notification channels, the telemetry switch, how gate commands run and what an engine session may see of the environment into the stored project config. `[gates]` and `[engine_environment]` are validated first: a forbidden entry stops `vibey new` before a project exists. |
| `<repo>/vibey.toml`, `[queue.priority] sources` — the project's own repository root, never the current directory | `vibey queue bump` / `unbump`, `vibey design resume --priority`, via `QueuePriorityService` (`infrastructure/queue_priority_grant.py` `ProjectPriorityGrantReader`) | Which automations besides the operator may reorder the project's queue ([`[queue.priority]`](#queuepriority)); the file's owner is the operator. Read fresh on every request; only the `[queue]` table is parsed. A missing file declares none; a malformed one refuses every request, recorded. |
| `./vibey.toml`, `[queue.reap]` and `[bus]` -- or, with no `./vibey.toml`, the environment alone (`VIBEY_QUEUE_REAP_*`, `VIBEY_BUS_*`) | `bootstrap.build_app` (every command that opens the queue), via `load_config_from_path` or `EnvironmentConfigLoader` | The queue reaper's thresholds and broker policy ([`[queue.reap]`](#queuereap)) and the bus it inspects. A cluster pod has no `vibey.toml` in its working directory, so the chart's environment is what composes both there (ADR-0056). A malformed environment value fails the start; a `./vibey.toml` that does not parse is skipped, as `build_app` has always skipped it, and the environment alone is read. |
| The project's stored record (the `project` row: `max_cycles` column and `config` JSON) | `vibey worker`, lifecycle repository, and job handlers | Cycle cap, per-cycle spend and turn caps, skills-context policy, [gate commands](#gates), [what an engine session may see of the environment](#engine_environment), notification delivery, telemetry, and (in principle) the `features` local-engine switches — see below. |
| Environment variables | See [Environment variables](#environment-variables) | Database DSN, the migration-lock wait, the local-engine switches, the sovereign DESIGN provider's evidence directory. |

The project record is written once, at creation, by one of two paths:

- **`vibey new`** (see the [CLI reference](cli.md)): `--max-cycles` is stored
  in the `project.max_cycles` column; `--max-cycle-dollars`,
  `--max-cycle-turns`, `--skills-context-mode` and `--skills-context-budget`
  are stored in the `config` JSON as `max_cycle_dollars`, `max_cycle_turns`
  and `skills_context` (the last only when the mode is not `off`). When the repo
  contains `vibey.toml`, its `[notifications]`, `[telemetry]`, `[gates]` and
  `[engine_environment]` tables are copied into that same JSON record.
- **The Kubernetes operator** ([ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md)):
  a `VibeyProject` spec's `maxCycles` sets the column (default `10`);
  `repo`, `maxCycleDollars`, `maxCycleTurns` and `skillsContext` are stored in
  the `config` JSON, and `gates` and `engineEnvironment` as its `gates` and
  `engine_environment` objects (validated the same way). `spec.engines` is stored as
  a flat `engines` list that nothing reads back yet.

Neither path passes through `parse_config`. One command updates any of these values
on an existing project, and only two of them: `vibey budget set` and
`vibey budget clear` rewrite `max_cycle_dollars` and `max_cycle_turns` (see
[Per-cycle caps](#per-cycle-caps-max_cycle_dollars-max_cycle_turns)). No command
changes the rest after creation. The operator applies its spec at creation only,
so later edits to a `VibeyProject`'s `maxCycleDollars` or `maxCycleTurns` change
nothing; use `vibey budget`.

### Per-cycle caps: `max_cycle_dollars`, `max_cycle_turns`

The budget brake's caps. They are top-level keys of the project's stored
`config`, and that is the only place the brake reads them
(`LedgerBudgetSource.caps_from_config`).

| Key | Type | Unset means | Set by |
|---|---|---|---|
| `max_cycle_dollars` | number above zero | no dollar cap | `vibey new --max-cycle-dollars`, the operator's `spec.maxCycleDollars`, `vibey budget set --max-cycle-dollars` |
| `max_cycle_turns` | integer above zero | no turn cap | `vibey new --max-cycle-turns`, the operator's `spec.maxCycleTurns`, `vibey budget set --max-cycle-turns` |

- **Read at every BUILD session**, not once when a worker starts. A cap changed
  while a worker runs binds its next BUILD session. A project created uncapped
  can be capped without a restart.
- **Uncapped is absence.** `vibey budget clear` removes the key, leaving the config
  as if the cap had never been set. A key that is not a number, or a `true` or
  `false`, is also no cap. It is never a default.
- **Every change is on the ledger.** Each `set` or `clear` that changes a cap
  appends one `BudgetCapChanged` event (`field`, `old`, `new`, `by`, `account`)
  in the same transaction as the config write. `vibey budget --json` reads its
  `history` back from those events. A value set at creation has no event.
- **A grant is not a cap change.** Answering a `budget_exhausted` gate with
  `--raw '{"max_dollars": N}'` raises the cap for that one job and leaves the
  stored cap as it is.

Neither path writes a `features` key either, so for projects created today the
worker finds no stored switch and each local engine sits at its default —
`gptossloop` on, `qwenloop` and `claudeloop-local` off (ADR-0064):
**the `VIBEY_FEATURE_*` variables are the switches that reach the worker.**

## Environment variables

| Variable | Read by | Effect |
|---|---|---|
| `VIBEY_PG_URL` | `bootstrap.database_url()` (every command that opens the queue) | The application role's PostgreSQL DSN ([database roles](#database-roles)). Required; there is no default — `vibey` exits with `DatabaseNotConfigured` if it is unset. |
| `VIBEY_PG_MIGRATE_URL` | `vibey migrate` only | The owner's DSN: migrations run on it, and the application role's grants are reconciled from it ([database roles](#database-roles)). Give it to that one command (`VIBEY_PG_MIGRATE_URL=… vibey migrate`); never export it, and nothing else reads it. |
| `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` | `bootstrap.build_app()` via `PostgresMigrator.from_environ` (every command that opens the queue) | How long a start waits for another process's migration before failing with `MigrationLockTimeout`, which names the backend pid holding the lock. Seconds, fractions allowed and rounded up to the next millisecond; default `300`; `0` waits indefinitely. Unset or blank means the default; anything that is not a number from `0` to `2147483.647` fails the start with `InvalidMigrationLockTimeout` before the pool opens, rather than falling back. See [the migration lock](../plans/data-model.md#71-the-migration-lock). |
| `VIBEY_FEATURE_GPTOSSLOOP` | `vibey worker`, `vibey doctor` and `vibey loops`, through `LocalEngineSettings` (`infrastructure/engines/local_engines.py`) | Overrides `features.gptossloop`. `1`, `true`, `yes`, `on` (case-insensitive, surrounding whitespace ignored) enable; any other set value — `0` included — disables. When set it wins over both the stored project record and `./vibey.toml`; when neither sets the switch, gptossloop is on (ADR-0064). For the worker, gptossloop on means a gptossloop adapter in the LOCAL tier, preferred first for BUILD ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md)). |
| `VIBEY_FEATURE_QWENLOOP` | as `VIBEY_FEATURE_GPTOSSLOOP` | Overrides `features.qwenloop`, with the same values. Off when nothing sets it. Enabling it adds a qwenloop adapter — the same runner on a Qwen model — to the LOCAL tier beside gptossloop, and makes the worker and `vibey doctor` print a `note:` that qwenloop runs a Qwen model since ADR-0064. |
| `VIBEY_EVIDENCE_DIR` | `vibey work --provider gptossloop`, `vibey worker --provider gptossloop` (the default) | Directory of reading that the sovereign DESIGN provider's research stage draws from ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)). Unset, research refuses rather than inventing a source, and the phase stops there. |

### Database roles { #database-roles }

The ledger is append-only by the database
([ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)).
Triggers refuse every `UPDATE`, `DELETE` and `TRUNCATE` of `event` and its partitions,
even by the owner. The application connects as a role that could not rewrite the ledger
anyway. There are two roles and two DSNs:

| Role | DSN | Holds |
|---|---|---|
| The owner | `VIBEY_PG_MIGRATE_URL` | Every table. Runs migrations and reconciles grants, nothing else: `vibey migrate`, run by hand or as the chart's `migrate` init container. No other command reads this variable, so no worker, engine session or gate command ever holds the owner's DSN. |
| The application role | `VIBEY_PG_URL` | Exactly `APP_ROLE_GRANTS` (`infrastructure/db/ledger_guard.py`). On `event` that is `SELECT` and `INSERT`. It holds no `DELETE` or `TRUNCATE` anywhere, owns nothing, and is not a superuser. Every worker, CLI command, operator and KEDA scaler connects as it. |

`build_app()` never reads the owner's DSN:

- When the application's role may migrate (a superuser, or a member of the migration
  catalog's owner), it migrates as that role. This is a single-DSN install.
- Otherwise it only verifies the schema, and refuses to start while migrations are pending
  (`SchemaNotMigrated`): run `vibey migrate` first.

**Upgrading a single-DSN install.** Existing installs connect as one role, usually a
superuser. They keep running, but `vibey doctor` fails `ledger-guard`, `vibey worker`
prints `error: ledger guard NOT in force` on every start, and `vibey migrate` exits 1,
until the roles are split:

1. Set `VIBEY_PG_URL` to the same server with a new role and password, for example
   `postgresql://vibey_app:<password>@host:5432/vibey`.
2. Run `VIBEY_PG_MIGRATE_URL=<the DSN you use today> vibey migrate`, giving the owner's DSN
   to that one command rather than exporting it. It creates `vibey_app` (from the DSN's
   password) if it does not exist, grants it exactly the declared privileges, and prints
   `ledger guard in force`.
3. Remove the owner's DSN from every other environment: a worker, an engine session or a
   gate command that holds it can disable the triggers.
4. Run `vibey doctor`, and require scram-sha-256 for every connection (sub-doctrine 10.j,
   ADR-0061): never `trust`, `peer`, `ident`, `md5` or a password in clear. The split
   protects the ledger only once `local-auth` passes. `SECURITY.md` §7 gives the required
   `pg_hba.conf` lines.

With the Helm chart this is `postgres.appRole` (default `vibey_app`) and, for an external
database, `dsn.existingSecretKey` (the application's DSN) with
`dsn.existingSecretMigrateKey` (the owner's). `existingSecretMigrateKey` is empty by
default, which is a single-DSN install.

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
| `VIBEY_BUS_VHOST` | `[bus].vhost` | RabbitMQ vhost the bus and the reaper are scoped to |
| `VIBEY_BLOB_URL` | `[blob].url` | Garage S3 URL |
| `VIBEY_BLOB_ACCESS_KEY` | `[blob].access_key` | Garage S3 access key |
| `VIBEY_BLOB_SECRET_KEY` | `[blob].secret_key` | Garage S3 secret key |
| `VIBEY_BLOB_REGION` | `[blob].region` | Garage S3 region |
| `VIBEY_SIEM_URL` | `[siem].url` | Wazuh indexer endpoint |
| `VIBEY_SIEM_USERNAME` | `[siem].username` | Wazuh indexer username |
| `VIBEY_SIEM_PASSWORD` | `[siem].password` | Wazuh indexer password |
| `VIBEY_SIEM_INDEX` | `[siem].index` | Wazuh index name |

The queue reaper's keys have the same overlay, and the same precedence
([`[queue.reap]`](#queuereap)). A boolean takes `1`, `true`, `yes` or `on` and `0`, `false`,
`no` or `off`, in any case; anything else fails the start, naming the variable.

| Variable | Target Table & Key |
|---|---|
| `VIBEY_QUEUE_REAP_ENABLED` | `[queue.reap].enabled` |
| `VIBEY_QUEUE_REAP_INTERVAL_SECONDS` | `[queue.reap].interval_seconds` |
| `VIBEY_QUEUE_REAP_LEASE_GRACE_SECONDS` | `[queue.reap].lease_grace_seconds` |
| `VIBEY_QUEUE_REAP_STALE_READY_SECONDS` | `[queue.reap].stale_ready_seconds` |
| `VIBEY_QUEUE_REAP_DEAD_LETTER_MIN_DEPTH` | `[queue.reap].dead_letter_min_depth` |
| `VIBEY_QUEUE_REAP_DEAD_LETTER_PEEK_LIMIT` | `[queue.reap].dead_letter_peek_limit` |
| `VIBEY_QUEUE_REAP_OWNED_QUEUE_PATTERN` | `[queue.reap].owned_queue_pattern` |
| `VIBEY_QUEUE_REAP_DEAD_LETTER_QUEUE_PATTERN` | `[queue.reap].dead_letter_queue_pattern` |
| `VIBEY_QUEUE_REAP_POLICY_NAME` | `[queue.reap].policy_name` |
| `VIBEY_QUEUE_REAP_POLICY_PRIORITY` | `[queue.reap].policy_priority` |
| `VIBEY_QUEUE_REAP_CONSUMER_TIMEOUT_SECONDS` | `[queue.reap].consumer_timeout_seconds` |
| `VIBEY_QUEUE_REAP_DELIVERY_LIMIT` | `[queue.reap].delivery_limit` |

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
path, as does a local engine in `[engines].enabled` or any `[phases.*].engines`
list while its switch is off: `qwenloop` before `features.qwenloop = true` (the
message adds that qwenloop runs a Qwen model since ADR-0064 and that the gpt-oss
engine it used to be is `gptossloop`), `claudeloop-local` before
`features.claudeloop_local = true`, and `gptossloop` while
`features.gptossloop = false`. `[phases.*].engines` entries are
otherwise not validated — unknown names and engines outside
`[engines].enabled` are accepted as written — and `[engines].weights` may name
a local engine whose switch is off. Unknown tables (for example
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
/ `--max-cycle-turns` or the operator's `spec.maxCycleDollars` /
`spec.maxCycleTurns`, and changed afterwards by `vibey budget set` / `clear`; see
[Per-cycle caps](#per-cycle-caps-max_cycle_dollars-max_cycle_turns)).
`LedgerBudgetSource` reads the caps at every BUILD session and sums the spend
live from the current cycle's `TurnCompleted` and `BudgetSpent` ledger events,
never estimating it ahead of time. Tripping either cap parks a
`budget_exhausted` gate. With neither set, spend is uncapped.

`vibey cost` and `vibey budget` show those stored caps and that ledger sum. A
`budget` key in the stored project config is not read by either.

## `[verify]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `require_independent_review` | bool | `false` | When `true`, `build.verify` always fails as `VIBEY` if the reviewing engine is the implementer, even when the configured pool has nobody else. When `false` (the default) a pool that cannot supply a second reviewer gets a self-review, recorded as a `DecisionRecorded` in the ledger so the weakened independence is visible. See [ADR-0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md). |

Unlike `[budget]` above, this key **is** read at runtime, by
`bootstrap.build_full_worker`.

## `[engines]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | array of strings | `["gptossloop"]`, plus every other local engine whose switch is on | Must be a subset of the known engines below. `gptossloop`, the sovereign default (sub-doctrine 8.b, `DEFAULT_ENGINES`), is on without declaration: an explicit list that leaves it out is extended with it. It leaves the pool only by `features.gptossloop = false` (ADR-0064). If the list is omitted, each switched-on local engine (`qwenloop`, `claudeloop-local`) is appended too. |
| `weights` | table of string→int | `{}` | Per-engine weight for smooth weighted round robin ([ADR-0005](../architecture/decisions/0005-smooth-weighted-round-robin.md)). Keys must be known engines; values are not validated. |

Known engine ids: `claudeloop`, `codexloop`, `cursorloop`, `agyloop`,
`gptossloop` (valid unless `features.gptossloop = false`), `qwenloop` (valid in
`enabled` and `[phases.*].engines` only once `features.qwenloop = true`), and
`claudeloop-local` (only once `features.claudeloop_local = true`). `opencode` is no
longer an engine: its engine and runner were deleted, and a `vibey.toml` that names
it is refused as an unknown engine.

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
| `gptossloop` | boolean | `true` | The sovereign default engine: the local runner on GPT-OSS 20B (ADR-0064). On unless set `false`; `false` removes it from the default pool and refuses it in `[engines].enabled` and `[phases.*].engines`. |
| `qwenloop` | boolean | `false` | The same runner on a Qwen model (`qwen3:14b` unless `QWENLOOP_MODEL` or its own config names another). Must be `true` before `qwenloop` can appear in `[engines].enabled` or any `[phases.*].engines` list. Before ADR-0064 this switch turned on the engine that ran `gpt-oss:20b`; that engine is now `gptossloop`, on by default. |
| `claudeloop_local` | boolean | `false` | The claudeloop binary on a local backend profile (`[engines.claudeloop_local]`). Must be `true` before `claudeloop-local` can be requested. |

Runtime: `vibey doctor` and `vibey loops` read these keys from `./vibey.toml`.
`vibey worker` reads them from the project's stored config record, which
`vibey new` and the operator never write, so for the worker the
`VIBEY_FEATURE_GPTOSSLOOP`, `VIBEY_FEATURE_QWENLOOP` and
`VIBEY_FEATURE_CLAUDELOOP_LOCAL` variables are currently the only switches; each
overrides both. With none set, the worker runs gptossloop and no other local
engine.

## `[qwenloop]`

Describes the local runner package that both `gptossloop` and `qwenloop` run
(the table keeps its historical name). In engine-driven BUILD rotation the local
engines form the LOCAL tier, preferred first
([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md),
amending the standby of
[ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)). The sovereign
DESIGN and DECOMPOSE providers are gptossloop's, the default for
`vibey work` and `vibey worker`
([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md),
ADR-0064). These keys mirror the runner's own `QwenConfig`
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

## `[queue.priority]` { #queuepriority }

Who besides the operator may move a job to the front of the queue
([ADR-0054](../architecture/decisions/0054-a-bumped-job-runs-next.md),
sub-doctrines 12.h and 12.j). Read from the `vibey.toml` at the root of the
project's own repository — the reviewed file — and never from the current directory
or a path given on the command line.

| Field | Type | Default | Notes |
|---|---|---|---|
| `sources` | list of strings | `[]` | The automations admitted to `vibey queue bump` / `unbump` (and `--priority`), each exactly as it names itself with `--source`. Matched exactly, case included. Each entry must be a non-blank string, may not repeat, and may not be `operator`. |

The **operator** is the account that owns this file (or the repository root, when
there is no file), checked by the process's uid — not a name. A declared source is
admitted only when it also runs as that account: a name is not a credential. Empty —
the default — admits the operator alone: the absence of a grant is refusal (12.f).
Every other request is refused and recorded on the ledger as `JobPriorityRefused`.
Declare a source only for an automation that decides for itself; a source that
relays other people's words (a label anyone may set, an issue comment) admits
everyone who can reach it.

```toml
[queue.priority]
sources = ["storm"]
```

## `[queue.reap]` { #queuereap }

When queued or held work counts as stuck, and what bounds it
([ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md)).
The same thresholds judge the PostgreSQL job queue and every queue on the broker, so both
backends reap identically. The worker runs the reaper when idle; `vibey queue reap` runs it
on demand ([CLI reference](cli.md#vibey-queue)). Every key must have the type of its
default -- `true` is not a number -- and an unknown key is refused.

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | bool | `true` | Whether the worker runs the reaper on its own. `vibey queue reap` runs regardless, and the lease reap -- `JobRepository.reap()`, in every idle worker iteration -- is always bounded. |
| `interval_seconds` | int ≥ 1 | `60` | The most often one worker runs a pass beyond the lease reap. |
| `lease_grace_seconds` | int ≥ 0 | `0` | How far past `lease_expires_at` a lease may run before it is reaped. The lease is already the heartbeat's bound (renewed every third of it), so the default adds nothing. Condition (a)/(b) on PostgreSQL. |
| `stale_ready_seconds` | int ≥ 1 | `900` | How long ready work may wait with nobody taking it before it is surfaced: the oldest claimable job's age on PostgreSQL, the head message's age on a queue with no consumer on the broker. Condition (d). A message without a `timestamp` property is not measured and never reported as old. |
| `dead_letter_min_depth` | int ≥ 1 | `1` | Dead letters on a dead-letter queue before it is acted on. Condition (e). |
| `dead_letter_peek_limit` | int ≥ 1 | `100` | The most dead letters one pass reads off one queue. Reading returns each to its place and the reaper removes none, so any past the limit are counted and surfaced every pass, never assumed parked. |
| `owned_queue_pattern` | regex | `^vibey\.` | Queues vibey owns. Only an owned dead-letter queue's messages are parked, and only owned queues get the policy below; every other queue on the broker -- Plane's Celery queues -- is measured and surfaced, never touched. |
| `dead_letter_queue_pattern` | regex | `(\.dlq\|\.dead)$` | Which queues are dead-letter queues: the bus port's `<queue>.dlq` and ADR-0044's `vibey.jobs.dead` / `vibey.runs.<engine>.dead`. |
| `policy_name` | string | `vibey-reap` | The broker policy the reaper reconciles onto owned queues, then reads back. |
| `policy_priority` | int | `0` | That policy's priority, against any other policy matching the same queues. |
| `consumer_timeout_seconds` | int ≥ 1 | `21600` | The policy's `consumer-timeout`: how long a consumer may hold a delivery from an owned queue before the broker closes its channel and requeues. Six hours: at least the longest job lease (two hours for BUILD), with room. Condition (a). The broker-wide value for everything else is the chart's `surfaces.rabbitmq.consumerTimeoutMs`. |
| `delivery_limit` | int ≥ 1 | `20` | The policy's `delivery-limit`: deliveries of one message on an owned **quorum** queue before the broker dead-letters it (condition (c)). Twenty, not three, because a draining worker's requeues count too (ADR-0044 §11). Classic queues ignore it. |

A reap is a gate a number crossed, never a judgement (12.d): every verdict is recorded as
a `QueueReaped` ledger event with the object, the condition, the measured value, the
threshold and the action. What each condition does is set out in ADR-0056: an expired
lease is requeued while attempts remain and parked with a `delivery_exhausted` gate once
they are spent; a dead letter on an owned queue becomes a parked `bus.dead_letter` job and
a `bus_dead_lettered` gate, and is never deleted.

```toml
[queue.reap]
stale_ready_seconds = 600
dead_letter_peek_limit = 200
```

## Concurrent local runs: `[local_models]` in `.vibey-gh.toml` { #local_models }

How many runs of one local model run at once on a device is not a `vibey.toml` key. It
is declared once per repository in `.vibey-gh.toml` `[local_models] concurrent_runs`,
and checked against **that device's own calibration evidence**
([ADR-0058](../architecture/decisions/0058-concurrent-local-runs-are-measured-per-device.md),
sub-doctrines 8.c and 8.j). The default, `1`, is 8.c as written and needs no evidence.
`"measured"` takes what the device's evidence supports. A number above one runs only if
the device measured that number inside every bound. Missing or stale evidence (another
runner version, model digest, memory or context window) means one, and a calibration is
requested. The storm runner reads the answer from `vibey-gh slots allowed`, and the queue
runs one lane at a time until it says more. Every key, the bounds and the calibration
are documented in the vibey-gh
[configuration reference](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/configuration.md#local_models-and-vibey-gh-slots).

```toml
# .vibey-gh.toml
[local_models]
concurrent_runs = 1
model = "gpt-oss:20b"
context_window = 65536
```

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
| `vhost` | string | `/` | The vhost the bus declares its queues in and the queue reaper reads ([`[queue.reap]`](#queuereap)). |

The bus port consumes at most once: its `consume` acknowledges on take, so no delivery is
ever held -- and one whose consumer dies after `consume` returns is lost. The job queue's
transport is ADR-0044's AMQP client, not this port.

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
| `code_review_commands` | array of arrays of non-empty strings | `[["ruff", "check", ".", "--exclude", ".vibey", "--exclude", ".claudeloop", "--exclude", ".codexloop", "--exclude", ".cursorloop", "--exclude", ".agyloop"]]` | Code-review checks. The default excludes vibey's own machinery inside the repo — worktrees under `.vibey/` and the engines' state dirs — which are not the product. An explicit `[]` disables the check. |

A malformed `review` object (not an object, a command list that is not a list
of non-empty string arrays) raises when the worker is built, rather than
silently running nothing.

## `[gates]` { #gates }

`SubprocessGateRunner.from_config` (`infrastructure/build/gate_runner.py`) reads the
record's `gates` object when `bootstrap.build_full_worker` builds the worker. One
runner runs build.verify's gates, build.integrate's gates and REVIEW's automated
checks. Declare it in `vibey.toml`'s `[gates]` table, which `vibey new` copies into the
record, or in the `VibeyProject` spec's `gates` object; do not edit the record's JSON
by hand (sub-doctrines 12.c and 12.h).

| Field | Type | Default | Notes |
|---|---|---|---|
| `timeout_seconds` | number | `1800` | Per command; one that overruns is killed and fails as exit 124. Must be finite and positive. |
| `kill_grace_seconds` | number | `5` | How long a killed command's reap may take before it is abandoned and logged. |
| `isolate_python_env` | bool | `true` | `false` passes vibey's own Python environment (`VIRTUAL_ENV`, `PYTHONPATH`, its venv on `PATH`) to gates that rely on tools installed beside vibey. |
| `env_allow` | array of strings | `[]` | Environment variables a gate command may receive beyond the system basics listed under [`engine_environment`](#engine_environment). A trailing `*` names a prefix (`GRADLE_*`). A gate command is decomposer-produced argv running engine-written code, so nothing else in the worker's environment reaches it. `VIBEY_*`, `PG*` and `GIT_*` can never be declared. A project's own test database can be (`TEST_DATABASE_URL`). |

A malformed or forbidden `gates` object is refused by `vibey new` and by the operator
before the project is created, and raises when the worker is built.

```toml
[gates]
timeout_seconds = 1800
env_allow = ["JAVA_HOME", "GRADLE_*", "TEST_DATABASE_URL"]
```

## `[engine_environment]` { #engine_environment }

An engine session runs model-chosen shell commands, unattended in BUILD and
DEPLOY_EXECUTE. It never inherits the worker's environment. Every engine process (the
run, its `--version`, `doctor` and `--help` probes, and the claudeloop
DESIGN/DECOMPOSE sessions) starts from an allow-list built by
`EngineEnvironmentPolicy` (`infrastructure/engines/engine_environment.py`). The
allow-list has three parts:

1. **The system basics, for every engine and every gate command:** `PATH` (with vibey's
   own venv removed), `HOME`, `USER`, `LOGNAME`, `SHELL`, `TMPDIR`, `TMP`, `TEMP`, `LANG`,
   `LANGUAGE`, `LC_*`, `TZ`, `TERM`, `COLORTERM`, `NO_COLOR`, `COLUMNS`, `LINES`,
   `SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`,
   `NODE_EXTRA_CA_CERTS`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `ALL_PROXY` (and their
   lower-case forms), `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`,
   `XDG_STATE_HOME`, `XDG_RUNTIME_DIR`, and `__CF_USER_TEXT_ENCODING` (macOS).
2. **What the engine's descriptor declares.** This is its `env_passthrough` and its API
   credential, `auth_env`:

   | Engine | Declared |
   |---|---|
   | `claudeloop` | `ANTHROPIC_API_KEY`, `CLAUDELOOP_*`, `CLAUDE_CODE_*`, `CLAUDE_CONFIG_DIR`, `ANTHROPIC_*` |
   | `claudeloop-local` | `CLAUDELOOP_*`, `CLAUDE_CODE_*`, `CLAUDE_CONFIG_DIR`, `ANTHROPIC_*` |
   | `codexloop` | `OPENAI_API_KEY`, `CODEXLOOP_*`, `CODEX_*`, `OPENAI_*`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
   | `cursorloop` | `CURSOR_API_KEY`, `CURSORLOOP_*`, `CURSOR_*` |
   | `agyloop` | `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `AGYLOOP_*`, `ANTIGRAVITY_*`, `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_GENAI_USE_ENTERPRISE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` |
   | `gptossloop` | `GPTOSSLOOP_*` (plus the `GPTOSSLOOP_BASE_URL`/`GPTOSSLOOP_MODEL` vibey derives from `VIBEY_OLLAMA_URL`) |
   | `qwenloop` | `QWENLOOP_*` (plus the `QWENLOOP_BASE_URL` vibey derives from `VIBEY_OLLAMA_URL`; vibey hands qwenloop no model) |

3. **What the project declares.** This is the record's `engine_environment` object,
   declared in `vibey.toml`'s `[engine_environment]` table (copied into the record by
   `vibey new`) or the `VibeyProject` spec's `engineEnvironment` object:

| Field | Type | Default | Notes |
|---|---|---|---|
| `allow` | array of strings | `[]` | Added for every engine. A trailing `*` names a prefix. |
| `engines` | object of engine id → array of strings | `{}` | Added for one engine only, for example `{"agyloop": ["GOOGLE_ACCESS_TOKEN"]}` or `{"claudeloop": ["GH_TOKEN"]}`. Keys must be known engine ids. |

A GitHub token or a cloud credential is on no default list. It reaches only the
engine it is declared for. Some things need declaring:

- agyloop's Vertex lane needs `GOOGLE_ACCESS_TOKEN` or `CLOUDSDK_AUTH_ACCESS_TOKEN`,
  and optionally `GOOGLE_APPLICATION_CREDENTIALS`. agyloop also finds application
  default credentials under `CLOUDSDK_CONFIG` when the gcloud configuration lives
  somewhere other than `~/.config/gcloud`; declare `CLOUDSDK_CONFIG` too in that
  case.
- claudeloop's GitHub issue import needs `GH_TOKEN` or `GITHUB_TOKEN` for a private
  repository.

Some names can never be declared, by anyone. For every engine: vibey's own `VIBEY_*`
variables (`VIBEY_PG_URL`, the queue and ledger DSN, among them), libpq's `PG*`, and
any name containing `DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`. A malformed object,
an unknown key or engine, or a forbidden entry is refused by `vibey new` and the
operator before the project is created, and raises when the worker is built. A
descriptor's own `env_passthrough` is held to the same rule when its adapter is built.

The worker's startup preflight probes each engine with the project's policy, so a
declared credential reaches the auth check the same way it reaches a session.
`vibey doctor` probes with the defaults, because it reads no project record, unless
`--record` names one (`--project`, default the latest): then it probes and runs
conformance with that project's policy, since the health it records is that
project's.

```toml
[engine_environment]
allow = ["JAVA_HOME"]

[engine_environment.engines]
agyloop = ["GOOGLE_APPLICATION_CREDENTIALS", "CLOUDSDK_CONFIG"]
"claudeloop-local" = ["GH_TOKEN"]
```

## Full example

This is a valid file exercising most of the schema that `parse_config`
validates. `vibey new` also copies its `[notifications]`, `[telemetry]`,
`[gates]` and `[engine_environment]` tables into the project's stored config (see
the top of this page).

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
gptossloop = true   # the default; false switches the sovereign engine off
qwenloop = true     # opt in to the same runner on a Qwen model

[qwenloop]
backend = "auto"
idle_timeout_seconds = 600

[queue.priority]
sources = ["storm"]

[gates]
env_allow = ["JAVA_HOME"]

[engine_environment.engines]
agyloop = ["GOOGLE_APPLICATION_CREDENTIALS"]

[queue.reap]
stale_ready_seconds = 900
```
