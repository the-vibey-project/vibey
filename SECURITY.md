# Security Policy

## Overview

Vibey is a queue-based conductor for autonomous software delivery. Because Vibey orchestrates autonomous engines, tools, code mutation, and optional deployment pipelines, isolation and defense-in-depth are foundational architectural requirements (see ADR-0008, ADR-0012, ADR-0013, ADR-0014).

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

### 4. Untrusted Prompt Defense & Delimiter Shielding (Task 9.4) — implemented and unit-tested, not yet an active runtime path
- `PromptShield` (`src/vibey/domain/prompt_shield.py`) implements the
  protections described below, but nothing outside its own test file
  (`tests/domain/test_prompt_shield.py`) ever constructs or calls it — no
  design or build handler (`application/seed_prompt.py`,
  `application/design_handler.py`, `application/build_implement_handler.py`,
  etc.) frames untrusted input through it. This includes the skills-context
  packet: `infrastructure/skills_context.py`'s `VibeySkillsContextCompiler`
  retrieves markdown from the separately versioned `vibey-skills`
  marketplace (a workspace member at `src/vibey_tools/skills`, invoked as a
  subprocess), whose skill files are themselves third-party content, and `build_implement_handler.py` appends it
  verbatim to the BUILD prompt whenever a project's `skills_context.mode` is
  `inject` — with no `PromptShield` framing. **Do not rely on the controls
  below: seed prompts, interview answers, issue descriptions, skills-context
  packets, and other third-party inputs are not currently shielded.**
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
    stop it reaching the queue and the ledger. `vibey doctor` checks for this: its
    `db-passwordless` line **warns** when the app DSN's database accepts a password-less login
    as the DSN's role or as the worker's OS user, on the DSN's host or (when that host is
    local) a local socket. Require `scram-sha-256` in `pg_hba.conf` for those connections, or
    run the worker as an OS user nothing else runs as.
  - **Same-user reach beyond the database.** A process running as the worker's user can read
    the worker's own environment through the OS (`/proc/<pid>/environ` on Linux), any file the
    worker can read (a `~/.pgpass`, a shell profile that exports `VIBEY_PG_URL`, a launchd
    plist), and can write the user's global git config and home directory.
  - **(b) The container boundary in §1 does not address any of this today.** It is
    implemented but not wired in; nothing runs in a container, so nothing is isolated from the
    worker's user. Until it is wired (and runs sessions as a different user or with no access
    to the database's socket), same-user access is open.
  - The ledger's append-only rule is enforced in the database by `DO INSTEAD NOTHING` rules on
    the `event` parent table, which the role that owns the table can bypass — see
    [the data model](docs/plans/data-model.md).
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
- **The split protects the ledger only once local authentication requires a password for
  the owner and every superuser.** A server that trusts its socket (the common default for
  a local PostgreSQL) lets any process running as the right OS user connect as a superuser
  without a DSN or a password, and no grant stops that. `vibey doctor` checks it as
  `local-auth`:
  - It fails when a password-less connection as the owner or a superuser is let in, or
    when `pg_hba.conf` has a `trust`, `peer` or `ident` rule that can match them.
  - It reports `UNKNOWN`, never a pass, when it could neither get in nor read
    `pg_hba_file_rules`.

  vibey does not edit `pg_hba.conf`: the lines below are the operator's to set. Put them
  above any broader rule and reload (`SELECT pg_reload_conf();`):

  ```
  # TYPE  DATABASE  USER        ADDRESS         METHOD
  local   all       all                         scram-sha-256
  host    all       all         127.0.0.1/32    scram-sha-256
  host    all       all         ::1/128         scram-sha-256
  ```

  `local-auth` keeps failing while any `trust`, `peer` or `ident` rule can match the owner
  or a superuser. If you keep one for administration, the failure stays until you remove
  it, and you carry that risk knowingly.

---

## Reporting a Vulnerability

If you discover a security vulnerability in Vibey, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainer privately at **adam@matthewsteinberger.com** with the subject
   `[vibey security]` (the same published contact as the Code of Conduct).
3. Include reproducible steps, affected versions, and potential impact.
4. We will acknowledge receipt within 48 hours and coordinate remediation before public disclosure.
