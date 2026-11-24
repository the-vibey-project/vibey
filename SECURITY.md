---
description: "vibey's security policy: what is enforced today and what is not, the trust boundaries of the hub, pairing, MCP, ACP and web tools, where every token lives, and how to report a vulnerability privately."
---

# Security policy: what vibey enforces, what it does not, and how to report a flaw

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone deciding whether to run vibey, or reporting a
> flaw. Found a vulnerability? Do not open an issue: email **adam@matthewsteinberger.com** with
> the subject `[vibey security]` ([Reporting a vulnerability](#reporting-a-vulnerability)).
> Each control below is marked active, active when configured, or built but not wired. Today a
> model-driven process is isolated from your account by a git worktree only, not the OS (§1, §5).

**How to read this page.**

**Daniel:** Professor, this page is long. Where do I start?

**Professor Feynman:** With the label on each heading. "Active" means the code runs it on
every path. "Not yet an active runtime path" means it is built and tested and nothing calls
it, so it protects you from nothing yet. Read §5 before anything else: it says what a
process running as your user can still reach.

**Daniel:** And the newer parts, the hub and the editors?

**Professor Feynman:** §10 to §14, one surface each. Each ends with what an agent can never do
there. The table under [Where the keys live](#where-the-keys-live) is for lookup.

## Overview

vibey is a queue-based conductor for autonomous software delivery. Because it orchestrates
autonomous engines, tools, code mutation and optional deployment, isolation and
defense-in-depth are architectural requirements. The decisions behind the controls below are
ADR-0008 (worktree isolation), ADR-0055 (the ledger is append-only by the database),
ADR-0061 (every PostgreSQL connection authenticates with scram-sha-256), ADR-0053 (the
unattended run admits no stranger), ADR-0068 and ADR-0071 (the hub, and hub pairing and
trust), ADR-0085 (vibey on the workflows), ADR-0100 (the MCP interface), ADR-0101 (the ACP
agent and its services) and ADR-0102 (local-first search), all under
[docs/architecture/decisions/](docs/architecture/decisions/).

---

## Threat Model & Security Boundaries

### 1. Worktree & Container Isolation Runtime (ADR-0008, Task 9.1)
- **Worktree Sandboxing**: Every job and phase executes inside an isolated ephemeral git worktree branched from base or integration heads. This is the only isolation boundary active today, and it is a boundary for git history, not for the operating system: every engine session, gate command and hook runs as the worker's OS user, with that user's files, sockets and processes within reach (see §5).
- **OCI Container Hardening — implemented and unit-tested, not yet an active runtime path**: `ContainerConfig` and `OciContainerExecutor`
  (`src/vibey/infrastructure/container/config.py`, `runtime.py`) implement the
  hardening described below, but nothing outside their own test file
  (`tests/infrastructure/container/test_runtime.py`) ever constructs them —
  `bootstrap.py` does not import `vibey.infrastructure.container`, and no CLI
  flag or `vibey.toml` key (`[isolation] level = "container"` included; see
  [the configuration reference](docs/reference/configuration.md#isolation))
  reaches this code. Every job runs in a plain worktree regardless of what
  `[isolation]` says. Do not rely on the controls below until this adapter is
  wired into the composition root. In particular, **§5's same-user exposure is not
  addressed by anything here today**: an unwired container runs nothing, so a model-driven
  process shares the worker's OS user in every deployment that exists.
  What the adapter would provide, once wired:
  - **Read-Only Root Filesystem**: Containers run with `--read-only`.
  - **Dropped Capabilities**: All Linux kernel capabilities are dropped (`--cap-drop=ALL`).
  - **Privilege Escalation Prevention**: Containers run with `--security-opt=no-new-privileges:true`.
  - **Ephemeral Storage**: `/tmp` is mounted as a restricted tmpfs (`rw,noexec,nosuid,size=512m`).
  - **Resource Capping**: Hard memory limits (`--memory=4g`) and CPU quotas (`--cpus=2.0`).
  - **Network Isolation**: Defaults to `--network=none` unless explicitly configured for network-dependent build phases.

### 2. Destructive-Command Prevention (Task 9.2) — implemented and unit-tested, not yet an active runtime path
- `CommandSecurityPolicy` (`src/vibey/domain/command_guard.py`) implements the
  scans described below, but nothing outside its own test file
  (`tests/domain/test_command_guard.py`) ever constructs or calls it — none of
  the actual subprocess call sites (`infrastructure/engines/claudeloop_process.py`,
  `infrastructure/build/gate_runner.py`, the CLI's `az` invocations, etc.)
  invoke `check_command` before running a command. **Do not rely on the
  controls below: autonomous engines are not currently prevented from
  executing destructive operations.**
  - **Git Safety**: Blocks `git reset --hard`, `git push --force`, `git push -f`, `git branch -D main|master`.
  - **Filesystem Safety**: Blocks `rm -rf /`, `rm -rf ~`, `rm -rf *`, `mkfs.*`, `dd of=/dev/`.
  - **System Safety**: Blocks `reboot`, `shutdown`, `poweroff`, fork bombs.
  - **Database Safety**: Blocks raw `DROP DATABASE` or `DROP TABLE` outside migration harnesses.

### 3. Scope-Bound Mutation Enforcement (Task 9.3) — implemented and unit-tested, not yet an active runtime path
- `MutationScope` (`src/vibey/domain/scope_guard.py`) implements the checks
  described below, but nothing outside its own test file
  (`tests/domain/test_scope_guard.py`) ever constructs or calls it — the
  Phase ② (Build Implement) file-mutation path
  (`application/build_implement_handler.py`) never invokes it. **Do not rely
  on the controls below: file mutations are not currently scope-checked.**
  - Directory traversal (`../`, absolute paths escaping the worktree root)
  - Symlink escapes pointing outside the repository tree
  - Modification of sensitive repository assets (`.git/`, `.env*`, `id_rsa`, `secrets.json`)
  - Modification of files outside declared `spec.md` work item paths
  would be blocked with a `ScopeViolation` before staging, once wired in.

### 4. Untrusted Prompt Defense & Delimiter Shielding (Task 9.4) — implemented and unit-tested; active on one path, the triaged-delivery intake
- **Active on the triaged-delivery intake.** `scripts/triaged_delivery.py` hands a GitHub
  issue to `vibey new --intake` only after `scripts/intake_trust.py` has checked, from one
  forge query and against the trust grant in reviewed history, that the issue's author,
  every editor and whoever applied its triage labels are trusted (the storm's own seam,
  `storm_trust.py`; ADR-0053, sub-doctrine 12.j). An issue a stranger wrote, edited or
  labelled is held for a person and never dispatched. An admitted issue is framed by
  `PromptShield` before it enters the ledger, where `vibey new` records it as an
  `untrusted` `TranscriptRecorded` event (`docs/runbooks/triaged-delivery.md`). The trust
  check is the control that holds: measured on gpt-oss:20b, the frame did not reduce how often
  a planted instruction surfaced in the DESIGN interview's questions (4 of 10 runs raw, 5 of
  10 framed; the measurement is recorded in
  [the triaged-delivery runbook](docs/runbooks/triaged-delivery.md)).
- **Nowhere else.** Outside that one path, nothing constructs or calls `PromptShield` — no
  design or build handler (`application/seed_prompt.py`,
  `application/design_handler.py`, `application/build_implement_handler.py`,
  etc.) frames untrusted input through it. This includes the skills-context
  packet: `infrastructure/skills_context.py`'s `VibeySkillsContextCompiler`
  retrieves markdown from the separately versioned `vibey-skills`
  marketplace (a workspace member at `src/vibey_tools/skills`, invoked as a
  subprocess), whose skill files are themselves third-party content, and `build_implement_handler.py` appends it
  verbatim to the BUILD prompt whenever a project's `skills_context.mode` is
  `inject` — with no `PromptShield` framing. **Do not rely on the controls
  below anywhere but the triaged-delivery intake: seed prompts, interview answers,
  issue text given to `vibey new --intake` by any other caller, skills-context
  packets, and other third-party inputs are not currently shielded.** (Web search results
  and fetched pages are marked as untrusted by their own code path; see §14.)
  - Strips non-printable ASCII control codes and ANSI escape sequences.
  - Generates unique cryptographic nonces per interaction (`<{label}_{nonce}>...<{label}_{nonce}>`).
  - Neutralizes XML/tag delimiter breakouts (`</...` escaping).
  - Prepends explicit security directives instructing models to treat framed inputs strictly as data.
  - Audits for common injection heuristics (`is_suspicious_injection`).

### 5. Secret Redaction & Environment Hygiene
- **What a model-driven process may see — implemented, tested, and active.** Engine sessions
  (every engine, every phase, and the `--version`/`doctor`/`--help` probes) and gate commands
  never inherit the worker's environment. Each starts from an allow-list built by
  `ChildEnvironment` (`src/vibey/infrastructure/process/child_environment.py`):
  - **Every child**: the system basics only — `PATH` (with vibey's own venv removed), `HOME`,
    `USER`, `LOGNAME`, `SHELL`, the temp directory, locale (`LANG`, `LANGUAGE`, `LC_*`), `TZ`,
    the terminal (`TERM`, `COLORTERM`, `NO_COLOR`, `COLUMNS`, `LINES`), the CA bundle
    (`SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`,
    `NODE_EXTRA_CA_CERTS`), the proxy (`HTTP(S)_PROXY`, `NO_PROXY`, `ALL_PROXY`, either case)
    and `XDG_*_HOME`/`XDG_RUNTIME_DIR`.
  - **An engine session** adds the variables its descriptor declares (`env_passthrough`: its
    runner's and vendor CLI's own, for example `CLAUDELOOP_*`, `CLAUDE_CODE_*`, `ANTHROPIC_*`)
    and its own API credential (`auth_env`); the full per-engine table is in
    [the configuration reference](docs/reference/configuration.md#engine_environment).
  - **Anything else** reaches an engine only when the project declares it, in `vibey.toml`'s
    `[engine_environment]` (`allow`, or `engines.<engine>` for one engine) or the
    `VibeyProject` spec's `engineEnvironment`, and a gate only through `[gates]` `env_allow`
    (`spec.gates`). A GitHub token or a cloud credential is on no default list: it reaches
    only the engine it is declared for.
  - **Never, whoever declares it**: vibey's own `VIBEY_*` variables — `VIBEY_PG_URL`, the queue
    and ledger DSN, among them — and libpq's `PG*`; for gates also `GIT_*`; for engines also
    any name containing `DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`. A declaration that tries
    is refused by `vibey new` and the operator before the project exists, and when the worker
    is built; an engine descriptor's own passthrough is checked when its adapter is built.
- **The limits of this control — read these before relying on it.** It keeps the DSN out of a
  child's *environment*. It is not a boundary between the worker and the processes it starts,
  because they are the same OS user:
  - **(a) A local PostgreSQL with `trust` or `peer` authentication needs no DSN at all.** Any
    process running as the OS user the database trusts connects with no password: `psql -d
    vibey`, as that user, over the local socket or localhost. Review did exactly that on a
    development machine, connecting as the operator's own user with no password. An engine
    session or a gate command is such a process, so on that machine the allow-list does not
    stop it reaching the queue and the ledger. Such a server does not conform to this project:
    sub-doctrine 10.j, drafted in ADR-0061 and in force once the operator's merge ratifies
    it, requires `scram-sha-256` for every connection, local and remote alike. The required
    `pg_hba.conf` lines are in §7. `vibey doctor` checks for this: its `db-passwordless` line
    **fails**, and `vibey doctor` exits 1, when the app DSN's database accepts a password-less
    login as the DSN's role or as the worker's OS user, on the DSN's host or (when that host
    is local) a local socket. Running the worker as an OS user nothing else runs as narrows
    who can reach the socket, but it does not replace the requirement.
  - **Same-user reach beyond the database.** A process running as the worker's user can read
    the worker's own environment through the OS (`/proc/<pid>/environ` on Linux), any file the
    worker can read (a `~/.pgpass`, a shell profile that exports `VIBEY_PG_URL`, a launchd
    plist, and the hub's token files in §10–§12), and can write the user's global git config
    and home directory.
  - **(b) The container boundary in §1 does not address any of this today.** It is
    implemented but not wired in; nothing runs in a container, so nothing is isolated from the
    worker's user. Until it is wired (and runs sessions as a different user or with no access
    to the database's socket), same-user access is open.
  - **The ledger's append-only guard is in the database, and it has a known edge.**
    Migration 0016 dropped the old `DO INSTEAD NOTHING` rules, which bound only a query
    addressed to `event` itself and turned a stray write into a silent no-op. It replaced
    them with triggers that refuse every `UPDATE`, `DELETE` and `TRUNCATE`, the table owner's
    included, on `event` and every partition; migration 0017 pins their `search_path`. The
    owner's DDL is not refused: dropping or detaching a partition, or disabling a trigger.
    What stands against that is that only `vibey migrate` holds the owner's DSN, and every
    workload connects as a role that owns nothing and holds no `UPDATE`, `DELETE` or
    `TRUNCATE` on the ledger. §7 has the whole of it (ADR-0055).
- **(c) vibey's own git calls — what is and is not covered.** vibey runs git on repositories an
  engine writes to from its linked worktree, so a planted hook or config entry would otherwise
  run inside vibey's git calls. `CleanGitEnvSubprocessExecutor`
  (`src/vibey/infrastructure/git/clean_env.py`) runs every one of them (the BUILD worktree's
  `git worktree add`, the integration `git merge`, prune, config and listing calls):
  - **with the system basics only**, plus `GIT_CONFIG_NOSYSTEM=1`: no `VIBEY_*`, no `PG*`, no
    credential, and no `GIT_*` inherited from a surrounding hook;
  - **with no hook**: `-c core.hooksPath=/dev/null` outranks every config file, so a hook
    planted in the common `hooks/` directory or behind any `core.hooksPath` does not run; the
    integration merge also passes `--no-verify` (switching off repository-planted hooks in
    vibey's own merge plumbing — vibey's gates run separately, before integration, and are
    not skipped);
  - **with no file-system monitor**: `-c core.fsmonitor=false`;
  - **and it refuses a repository whose own config declares a filter or merge driver.**
    Drivers are named by the repository and cannot be switched off generically, so before a
    checkout or a merge `RepositoryConfigGuard` reads the config git will use and fails the
    job when the `local` or `worktree` scope (or a file they include) declares
    `filter.<x>.clean|smudge|process` or `merge.<x>.driver`.

  **Not covered:** a filter or merge driver in the operator's *global* git config (Git LFS
  installs one there) still runs — without vibey's secrets in its environment, but as the
  operator, and an engine running as the same user can write that file. `git diff HEAD` in
  BUILD verify runs through the gate runner with the gate environment and honours the
  repository's config like any gate command. The scratch repository `vibey doctor
  --conformance` creates is driven by the application layer with the doctor's environment.
  The `az` CLI runs through its own executor with the system basics plus the Azure CLI's
  configuration variables; the desktop notifier runs `osascript`/`notify-send` with the
  system basics and passes the notification's text as arguments, never as script.
- All ledger and telemetry records run through redaction masks (`redact.py`) to prevent leakage of credentials, tokens, or private keys.

### 6. Webhook Payload Integrity — implemented, unit-tested, and active when configured
- `infrastructure/notify/` implements a `NotificationService` whose webhook
  dispatch signs payloads with HMAC-SHA256 signatures
  (`X-Vibey-Signature: sha256=...`) and validates them against URL scheme
  restrictions, and it is covered by tests. `build_app()` constructs the
  service, and `vibey new` copies `[notifications]` from the repository's
  `vibey.toml` into the project record. Delivery remains opt-in: configure
  `[notifications] enabled = true` before relying on desktop or webhook alerts.
  See the README's [Notifications](README.md#notifications) section.

### 7. The ledger is append-only by the database (ADR-0055) — implemented, tested, and active
- **Triggers refuse every rewrite.** Migration 0016 puts a `BEFORE UPDATE OR DELETE` row
  trigger and a `BEFORE TRUNCATE` trigger on `event`. They cover every partition: the row
  trigger is cloned onto each, and `ledger_guard_partitions()` attaches the `TRUNCATE`
  guard on every migration run. They refuse the owner's DML too, with `the ledger is
  append-only`. Both functions pin `search_path = pg_catalog, pg_temp` (migration 0017).
- **The triggers do not refuse the owner's DDL.** The owner can still `DROP` a partition,
  `DETACH` one and then `DELETE` from it (a detached table has no clone of the row
  trigger), `TRUNCATE` a partition created since the last `vibey migrate` (it gets the
  `TRUNCATE` guard at the next one), or disable a trigger. What stands against those is
  that nothing but `vibey migrate` holds the owner's DSN. DDL-refusing event triggers
  (`ddl_command_start`, `sql_drop`) are future work: they need a superuser to install.
- **The application cannot rewrite the ledger.** Every workload connects with
  `VIBEY_PG_URL` as an application role that owns nothing. On `event` it holds `SELECT`
  and `INSERT` only. It holds no `DELETE` or `TRUNCATE` anywhere, and it cannot disable a
  trigger. It may not `CREATE` in `public` or in the database, owns no object, and may call
  no `SECURITY DEFINER` function that runs as the owner or a superuser: `ledger-guard`
  fails on each (review of #1100 — a role that could create in `public` planted an
  operator the owner's SQL resolved to, and wiped the ledger). Migrations and grants run
  with the owner's DSN, `VIBEY_PG_MIGRATE_URL`, read by `vibey migrate` alone: never
  export it. In the Helm chart it is mounted only into the `migrate` init container; each
  surface database (Plane, Infisical) is owned by a login role of its own, so no surface
  pod holds the owner's credentials. The grants are declared in `APP_ROLE_GRANTS` and
  reconciled on every migration run, under the migration lock, with the owner's session
  pinned to `search_path = pg_catalog, pg_temp`.
- **An install still on one role is reported, never silently accepted.** `vibey doctor`
  and `vibey doctor --cluster` fail `ledger-guard`, `vibey migrate` exits 1, and `vibey
  worker` says so on stderr at every start. The upgrade path is in
  [the configuration reference](docs/reference/configuration.md#database-roles).
- **The split protects the ledger only once every connection proves its password with
  scram-sha-256.** A server that trusts its socket (the common default for a local
  PostgreSQL) lets any process running as the right OS user connect as a superuser without
  a DSN or a password, and no grant stops that. An `md5` rule asks for a password but
  accepts a replayable hash, and a `password` rule sends it in clear.
- **scram-sha-256 is the required configuration, not an option** (sub-doctrine 10.j,
  ADR-0061; law once the operator's merge ratifies it). Every PostgreSQL connection this
  project configures, documents or installs authenticates with `scram-sha-256`, local and
  remote alike. It never uses `trust`, `peer`, `ident`, `md5` or `password`, and passwords
  are stored as SCRAM verifiers (`password_encryption = scram-sha-256`). A server that
  vibey uses must carry these `pg_hba.conf` lines above any broader rule, and no rule that
  admits anyone another way. The two `0.0.0.0/0` and `::/0` lines are for a server that
  takes remote connections. A server that listens only locally needs only the first three.

  ```
  # TYPE  DATABASE  USER        ADDRESS         METHOD
  local   all       all                         scram-sha-256
  host    all       all         127.0.0.1/32    scram-sha-256
  host    all       all         ::1/128         scram-sha-256
  host    all       all         0.0.0.0/0       scram-sha-256
  host    all       all         ::/0            scram-sha-256
  ```

  In `postgresql.conf`, set `password_encryption = scram-sha-256` (the default since
  PostgreSQL 14). Give every role that logs in a password before reloading
  (`ALTER ROLE … PASSWORD …`, which stores a SCRAM verifier under that setting), or it
  can no longer connect. Then run `SELECT pg_reload_conf();`. A password set while the
  server stored `md5` must be set again. The Helm chart's built-in PostgreSQL declares
  exactly these rules in its own `pg_hba.conf` and sets `password_encryption`. CI's
  PostgreSQL services declare `POSTGRES_HOST_AUTH_METHOD` and `POSTGRES_INITDB_ARGS` as
  `scram-sha-256`. `vibey install --postgres` and `vibey doctor --install-postgres` install
  the distribution's package, and the package's own `pg_hba.conf` is left for the
  operator to replace. The install says so, and `vibey doctor` fails until it is replaced.
- `vibey doctor` checks the server as `local-auth`:
  - It fails when a password-less connection as the owner or a superuser is let in.
  - It fails when `pg_hba.conf` has a `trust`, `peer`, `ident`, `md5` or `password` rule
    that can match them.
  - It fails when `password_encryption` is anything but `scram-sha-256`.
  - It reports `UNKNOWN`, never a pass, when it could neither get in nor read
    `pg_hba_file_rules`.

  vibey does not edit a server's `pg_hba.conf` that it did not deploy. `local-auth` keeps
  failing while any such rule can match the owner or a superuser. No exemption is kept
  for administration: an administrator authenticates with scram-sha-256 like everyone
  else.

### 8. Dependency advisories — every known one blocks, unless an expiring exception is declared and reviewed

Python dependencies are gated by `pip-audit --skip-editable` in CI's `gates` job and in the
pre-push hook. The npm lockfiles, the root workspace and `clients/app`, are gated by
`vibey-gh advisory-check` in the `@vibey/core`, `app` and `VS Code extension` jobs. The check
runs `npm audit --json` and fails on every advisory at `[advisories] audit_level` (`high`) or
worse, as `npm audit --audit-level=high` does. The one difference is that an advisory may be
excepted in `.github/advisory-exceptions.toml`.

If the advisory service itself cannot be reached, no audit happened, and the gate fails by
default (`on_unavailable = "fail"`). This repository sets `on_unavailable = "warn"`: an npm
network timeout or 5xx is reported as a `::warning::` naming the workspace and the reason and
the job continues, with the workspace explicitly unaudited. It does not excuse an advisory,
a malformed report, a missing lockfile, or an advisory-database lookup that failed.

An exception exists for an advisory that cannot be fixed yet, such as one with no patched release,
where the vulnerable code is shown not to be reached. It is not a way to skip the gate:

- **Declared narrowly.** Each entry names one GitHub advisory (`GHSA-…`), one package and one
  workspace. It says why the vulnerable code is not reached, with the evidence (dependency path,
  call sites, shipped bundles). It also gives the condition that retires it and where upstream
  tracks that condition.
- **Expiring.** `expires` is at most `[advisories] max_exception_days` (30) after `added`.
  On that date the exception stops being honoured and CI fails until someone takes the fix or
  re-decides it with fresh evidence. `warn_days` (7) before then, every run warns.
- **Never silent.** Every run prints each exception it honours, the date it runs until, and the
  packages that are flagged only because of it.
- **Self-retiring.** The check fails when an exception matches nothing at the audit level any
  more, so it is deleted rather than left to rot. It also fails when the advisory database
  names a patched release of the package, so the fix replaces the exception. When the database
  cannot be read, the exception is not honoured. The same applies when npm reports an error or
  returns a report the check cannot account for: it is refused, not passed.
- **Reviewed.** The file is a protected path (`.github/CODEOWNERS`, `[merge_train]
  protected_paths`). Accepting a risk takes the code owner's approval and a human merge, and
  the merge train never lands a change to it unattended. Merging an exception accepts its risk
  until it expires.

### 9. The sovereign review runner reads untrusted pull-request content on the operator's machine — accepted 2026-10-24

The sovereign review lane (sub-doctrine 8.a) runs `pr-review.yml`'s host job on a self-hosted
runner, labelled `vibey-local-vibey`, on the operator's own Mac. A pull request's diff, title
and description are untrusted text, and a model and its tools read them there. The operator
accepted that risk on 2026-10-24 (#668, item 10), on these conditions, which are the
isolation in force and are set out, with a way to verify each, in
[`docs/runbooks/sovereign-review-runner.md`](docs/runbooks/sovereign-review-runner.md):

- **One ephemeral container per job.** The supervisor starts a fresh runner container for each
  job, so one job's container is not another's.
- **An egress gate.** The job container joins only an internal Docker network, so the gate
  (`vibey-egress`) is the only thing it can reach: HTTPS on port 443 to the hosts in
  `[runners] egress_allow` only, refusing any address that is not globally routable, and the
  model server's four read and chat endpoints. A job cannot pull, create or delete a model,
  and cannot reach any other service on the machine. This closes a hole measured on
  2026-10-09, when the host's PostgreSQL and RabbitMQ ports accepted connections from inside
  a runner container.
- **A credential of its own, scoped to one repository.** The runner logs in with a
  fine-grained token for `the-vibey-project/vibey` alone, holding only
  *Administration: Read and write* (to mint registration tokens and reap offline runners),
  stored by a file-based `gh` login in `~/.config/gh-runner`. It is never the operator's own
  login, which can administer every repository the operator owns. The supervisor refuses to
  start if that login is missing, if its credential file is readable by other users, if GitHub
  rejects the token, or if the directory resolves to the operator's own `gh` directory.

**What this does not remove.** The gate bounds what a job can *reach*, not what it can
*compute*: a hostile pull request can still try to steer the model that reads it, and the
token the supervisor holds can still register and delete this repository's runners. The
accepted risk is exactly those two. Reopen it if a job is found reaching anything outside the
gate, if a container escape is demonstrated, or if the token's scope is widened.

### 10. The hub (`vibey serve`, ADR-0068) — implemented, tested, and active whenever a hub runs

The hub is the one HTTP surface every krypton client, `vibey mcp` and `vibey acp` reach
(`src/vibey/cli/serve.py`, `src/vibey/infrastructure/hub/`).

- **Loopback unless two things say otherwise.** It binds `127.0.0.1` on port 8765 (`[hub]
  port`). Leaving loopback takes both an explicit `vibey serve --host <address>` and
  `[hub] lan = true` in `vibey.toml`; an address the file does not declare is refused
  (exit 2), and a repository's `vibey.toml` alone never opens the LAN.
- **TLS only on a declared LAN.** With `[hub] lan = true` the hub serves HTTPS with its own
  certificate (a P-256 key, self-signed), and, with the optional `hub` extra installed,
  advertises itself as `_vibey._tcp` over mDNS. The advertisement grants nothing. On loopback it serves plain HTTP and announces nothing.
- **Every request names its caller first.** Every `/api/v1` route except the OpenAPI
  document answers only an authenticated principal; anything else gets 401 and learns
  nothing. `/health/live` and `/health/ready` need no credential and say only "live" and
  "ready".
- **Web hardening on every response.** A `Host` the hub does not expect is refused with 421
  (the DNS-rebinding defence). No CORS header is ever sent, so a page on another origin cannot
  read a response. Every response carries `default-src 'none'`, no framing, no referrer,
  `nosniff` and `no-store`. A body over the limit, or sent without a length, is refused
  (413/411) before it is read. Each principal has its own rate-limit bucket, and failed
  attempts draw from a small bucket per client address (`infrastructure/hub/app.py`).
- **Exposure is checked.** `vibey doctor`'s `hub-exposure` line fails when a running hub
  listens on an address no declaration allows, and reports `UNKNOWN` when no hub runs.
- **What no scope reaches.** Declaring paid use, lifting or changing a budget cap, the
  database DSN, migrations, the canon and state sync are never hub actions, whoever asks
  (`NEVER_FROM_THE_HUB` in `src/vibey/domain/hub_scope.py`). A command sent to the
  GitHub-hosted workflows through the hub (`vibey -w`, ADR-0085) that would reach one of them
  is refused there too.

### 11. Device pairing and scopes (ADR-0071) — implemented, tested, and active on a declared LAN

A phone or another computer is never trusted for where it is on the network (SD-01 §2). It
is trusted for what it holds (`src/vibey/domain/hub_pairing.py`,
`src/vibey/infrastructure/hub/pairing.py`, `devices.py`).

- **Only the host offers a pairing.** `vibey hub pair --scope <scope>` (repeatable, at least
  one: an empty grant is refused) asks the running hub for a 6-digit code from the OS's
  random source, good for 120 seconds, and shows it with a QR code. The QR code carries the
  hub's certificate fingerprint, so the device's first TLS connection trusts that certificate
  and no other.
- **The first correct claim spends the code.** It returns the device's id and a 32-byte key,
  once. Codes are compared in constant time. Five wrong claims withdraw every open offer, and
  offers live only in the running process.
- **Every request after is signed.** A device sends its id, a timestamp within 60 seconds of
  the host's clock, a nonce it never reuses and the SHA-256 of the body, signed with
  HMAC-SHA256 over the method, path and query. There is no session: every action, a `spend`
  answer included, is verified on its own.
- **Revocation is immediate.** `vibey hub revoke` removes the device from the registry, so it
  is refused from its very next request. Every pairing and revocation is also written to the
  ledger. Only the host principal may offer, list or revoke; a device is refused even for its
  own record, so no device can widen its own grant or pair another.
- **The scopes** (`HubScope`): `view` (read), `answer` (a gate that does not spend), `spend`
  (a gate whose answer spends money: `budget_exhausted` and the four deployment gates), `run`
  (start, pause or unwind work, ADR-0091), `bump` (move a queued job to the front),
  `workflows` (run a command on the repository's GitHub-hosted runners), `acp_sessions` and
  `web`. `vibey hub pair` offers `view`, `answer`, `spend`, `run` and `bump`; a device holds
  only what the host offered it, and never `acp_sessions` or `web` by default.
- **Starting projects from a device** is refused unless the host's own `vibey.toml` sets
  `[hub] projects_root`.

### 12. The agent principal: `vibey mcp` and `vibey acp` (ADR-0100, ADR-0101) — implemented, tested, and active when a client is connected

`vibey mcp` is a stdio MCP server a chat client launches (Claude Code, Claude Desktop, Codex,
Cursor, VS Code, Gemini CLI). `vibey acp` is an ACP agent an editor such as Zed launches.
Both turn what the model asks for into hub requests made as the **agent** principal, never as
the host (`src/vibey/cli/mcp.py`, `src/vibey/infrastructure/mcp/hub_gateway.py`,
`src/vibey/application/acp/`).

- **A narrower key.** They present `<state_dir>/agent.token`, never the host's
  `<state_dir>/token`, so the hub applies `[hub] agent_scopes`. The default is `view`,
  `answer`, `run`, `acp_sessions` and `web`. `agent_scopes = []` in your own `vibey.toml`
  turns agent access off.
- **What an agent principal can never do by default:** `spend`, `bump` or `workflows`. A model
  that has been argued out of its instructions still cannot spend money by answering a budget
  or deployment gate: the hub refuses it with 403, whatever the model says. Nothing in §10's
  `NEVER_FROM_THE_HUB` list is reachable at any scope.
- **A cloned repository can only narrow.** `[hub]` and the state folder come from your own
  configuration folder's `vibey.toml`. The `vibey.toml` of the folder the client opened may
  only narrow `agent_scopes` and `[web]`; it can never name a state folder.
- **Loopback only.** The gateway reaches only a hub on this computer's loopback. A runtime
  record naming any other host is refused before the token is read or anything is sent, and
  a record is believed only while its process holds the hub's lock.
- **No double sends.** A request that may have reached the hub (a read timeout, a reset after
  sending) is never sent again.
- **ACP modes narrow further.** An ACP session in `observe` mode reads; `drive` (the default)
  also answers non-spending gates and starts, pauses or unwinds work. Neither mode holds
  `spend` or `web`, and a gate reaches the editor as a permission request that only a person's
  pick answers.
- **Known gap.** The REVIEW phase's opt-in to deployment is a generic `choice` gate that the
  hub cannot tell apart by kind, so over MCP a principal with `answer` can answer it. ACP
  refuses it by recognising its options (`local_only`, `deploy`). The deployment gates that
  follow need `spend`, so no infrastructure is provisioned without a person, but the opt-in
  itself is answerable from MCP (`src/vibey/domain/hub_scope.py`, `SPEND_GATE_KINDS`).
- **Abandon is guarded by the model, not the hub.** The MCP `vibey_abandon_project` tool
  defaults to a dry run, and the server's instructions tell the model to ask you before a
  real one; the hub itself accepts a real abandon from any `run`-scoped caller.

### 13. `vibey connect` and the ACP user services — implemented, tested, and active when you run them

- **`vibey connect` writes other tools' configuration files** (`src/vibey/infrastructure/mcp/host_installer.py`).
  It registers `vibey mcp` (or, for Zed, `vibey acp`) by the absolute path of the running
  install, never a `PATH` lookup. With no `--client` it plans and writes all seven clients,
  creating their folders, so name the one you want (`--client claude_code`) and run
  `--dry-run` first. Claude Code and VS Code are project-scope: their entry goes into
  `.mcp.json` or `.vscode/mcp.json` in the current folder, which then holds your absolute
  `vibey` path; keep it out of commits you do not mean to make.
- **How it writes.** Atomically (a temporary file, then a rename), never wider than the file
  was (a new file is 0600, a backup keeps the original's bits), only inside its scope's root
  (the home folder or the project folder, after every symlink is resolved), never through a
  symbolic link or a hard link, and with a `.vibey.bak` copy of what was there. Every target
  is checked before any file is written. A Zed `settings.json` with comments is never
  rewritten: the snippet to paste is printed instead.
- **The ACP user services** (ADR-0101). When an editor first connects, `vibey acp` may run
  `vibey connect` for the clients installed here and write and load user-level services
  (launchd or `systemd --user`) that keep the hub and a worker running. Each step is behind a
  key in your own `[acp]` table (`auto_bootstrap`, `auto_connect`, `auto_services`), never
  replaces a unit you edited, and says which units it loaded and how to unload them;
  `vibey acp unload` stops and removes them. It installs PostgreSQL or SearXNG only after you
  pick "Install" in the editor, and it runs the PostgreSQL install with `sudo -n`, so it never
  waits at a password prompt.

### 14. Web search and fetch (ADR-0102) — implemented, tested, and active when used

Local research, the MCP tools `vibey_search` and `vibey_fetch`, and the `vibey search` and
`vibey fetch` commands can reach the web. A query or a URL a model was steered to write can
carry data out of the computer, so:

- **Local first.** Search asks the local SearXNG (`vibey searxng install`, on loopback) first,
  and the Brave API only as its backup. The Brave key (`VIBEY_BRAVE_API_KEY` or
  `BRAVE_SEARCH_API_KEY`) is read by the hub and by the CLI; inside an engine session there is
  no key, so there `vibey search` is the local SearXNG alone.
- **A guarded fetch** (`src/vibey/domain/web_tools.py`, `src/vibey/infrastructure/web/guarded_fetch.py`):
  only `http` and `https`, no credentials in the URL, no private, loopback, link-local,
  metadata, carrier-grade NAT or oddly spelt address; every address a name resolves to is
  checked and the connection goes to the address checked, so DNS rebinding cannot steer it
  inward. Every redirect is checked again and never steps down from HTTPS to HTTP. No cookie,
  no credential and no caller-chosen header is sent. Compressed answers, PDFs, images and other
  binary types are refused; text is capped and cleaned of terminal control codes.
- **Budgets and a record, through the hub.** Each principal holding `web` may search
  `[web] searches_per_hour` and fetch `fetches_per_hour` times in any rolling hour (429 when
  spent). Each use is recorded on the ledger with who, which tool, the outcome, the backend
  and, for a fetch, the hosts reached, never the query or the URL. A project's `vibey.toml`
  may only tighten `[web]`, never loosen it.
- **Untrusted output.** Everything returned is marked as untrusted web content: data to read,
  never instructions.
- **The SearXNG container** runs only on podman or docker found in trusted system folders
  (never on `PATH`), from an image pinned by digest, and only a container labelled as yours is
  ever removed.

---

## Where the keys live

| Secret | Where | Who can read it | What it grants |
|---|---|---|---|
| Host token | `<state_dir>/token` (0600, in a 0700 folder) | the account that runs vibey | every hub scope; nothing in `NEVER_FROM_THE_HUB` |
| Agent token | `<state_dir>/agent.token` (0600) | the account that runs vibey | `[hub] agent_scopes` (default `view`, `answer`, `run`, `acp_sessions`, `web`) |
| Device keys | `<state_dir>/devices.json` (0600) | the account that runs vibey | each paired device's own scopes |
| Hub certificate and key | `<state_dir>/hub-cert.pem`, `hub-key.pem` (0600) | the account that runs vibey | the identity a paired device pins |
| Run key | `<state_dir>/run.key` (0600) | the account that runs vibey | minting the ids of commands sent to the workflows, so a device reads back only its own runs |
| Runtime record | `<state_dir>/serving.json` | the account that runs vibey | not a secret: where a running hub listens |
| Application DSN | `VIBEY_PG_URL` (environment) | the worker and the hub; never an engine or gate (§5) | `SELECT`/`INSERT` on the ledger, no rewrite |
| Owner DSN | `VIBEY_PG_MIGRATE_URL` (environment) | `vibey migrate` alone; never export it | migrations and grants (§7) |
| Brave API key | `VIBEY_BRAVE_API_KEY` or `BRAVE_SEARCH_API_KEY` (environment) | the hub and the CLI, never an engine session | the search backup (§14) |

`<state_dir>` is `[hub] state_dir`, by default the `hub` folder inside the platform's user
state folder: `~/Library/Application Support/vibey/hub` on macOS, and
`$XDG_STATE_HOME/vibey/hub` (else `~/.local/state/vibey/hub`) on Linux. The token, agent
token and run key are opened without following a symlink and refused unless this account
owns them and no other account can read them; the certificate files are created exclusively
and never through a symlink. Anyone who can read these files can act as their holder, so §5's
same-user limit applies to them.

## Supported versions

vibey is pre-1.0 and has no maintenance branches: a fix lands on `develop` and ships in the
next release promoted to `main` (`vibey-engine` on PyPI, the `vibey-v<version>` GitHub
Release). Report against the newest release or `develop`, and say which.

## Reporting a Vulnerability

If you discover a security vulnerability in vibey, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainer privately at **adam@matthewsteinberger.com** with the subject
   `[vibey security]` (the same published contact as the Code of Conduct).
3. Include reproducible steps, affected versions (`vibey -v` prints them), and potential impact.
4. We will acknowledge receipt within 48 hours and coordinate remediation before public disclosure.

## Say it in one line

vibey isolates work in git worktrees, not the operating system, keeps its ledger append-only in the database, and gives an agent a narrower hub key that can never spend money.
