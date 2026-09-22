## Title
feat(install): PostgreSQL installs on Arch Linux with pacman, initdb and a role; Homebrew installs the major the chart runs

## Why
`PostgresLocalService` (src/vibey/infrastructure/postgres.py:134-397) finds brew, apt-get and
dnf (`_package_manager`, :304-308) but not pacman. So `vibey install --postgres` fails on Arch
Linux, the sovereign default OS, with "could not find Homebrew, apt-get, or dnf". An Arch
install also needs more than the package:
- the data directory must be initialized (`initdb`, which the Arch package does not run);
- the service must be enabled;
- the login user needs a role and a `vibey` database. Without them, the printed
  `VIBEY_PG_URL` example (src/vibey/cli/main.py:1179-1182) cannot connect.

Separately, Homebrew installs `postgresql@18` (`POSTGRES_INSTALL_MAJOR = POSTGRES_LATEST_MAJOR`,
postgres.py:33), while the chart runs 17 (`deploy/helm/vibey/values.yaml:53`,
`postgres:17-alpine`) and CI's gate job runs 17 (CLAUDE.md). Arch's repositories carry only
the current major (`extra/postgresql` 18.6 on 2026-09-22). That is within vibey's supported
range (14+, postgres.py:27-31), so Arch takes the repository's major.

## Required behaviour
1. `POSTGRES_INSTALL_MAJOR: Final = 17`, with a comment naming values.yaml:53 and the CI gate.
   Update the module docstring (postgres.py:9-13) so it no longer says the installer takes the
   current stable release: Homebrew installs 17, and pacman installs Arch's current major.
2. `_package_manager` checks `("brew", "pacman", "apt-get", "dnf")` in that order, and
   `install()` (:246-253) dispatches `"pacman"` to a new `_install_pacman(before, commands)`.
   `_unsupported_platform_detail` says "could not find Homebrew, pacman, apt-get, or dnf on ...".
3. `_install_pacman` runs these steps, using the existing `_privileged`, `_run_step` and
   `_service_start`:
   1. `_privileged(("pacman", "-S", "--needed", "--noconfirm", "postgresql"))`. With no
      privilege it fails with "pacman needs root or sudo to install PostgreSQL".
   2. Unless `_run(_privileged(("test", "-e", f"{ARCH_POSTGRES_DATA}/PG_VERSION")))` exits 0,
      run initdb as the postgres user: `_as_postgres(("initdb", "--locale=C.UTF-8", "--encoding=UTF8", "-D", ARCH_POSTGRES_DATA))`.
      `ARCH_POSTGRES_DATA: Final = "/var/lib/postgres/data"`. Failure gives "PostgreSQL was
      installed but its data directory could not initialize".
   3. `_service_start("postgresql")`, with the existing failure messages.
   4. Unless the login user is `root` or `postgres`:
      - `_as_postgres(("createuser", "--createdb", user))`;
      - then `_as_postgres(("createdb", "--owner", user, "vibey"))`.

      Each step succeeds on exit 0, or when stderr contains `already exists`; that is what
      makes a re-run idempotent. Otherwise it fails with "PostgreSQL is running but the role or
      database for <user> could not be created: <stderr>".
   5. It returns `True, "pacman installed/started PostgreSQL; role <user> and database vibey are ready"`.
      For root or postgres, the detail ends "; no login role was created for <user>".
4. `_as_postgres(argv)` returns:
   - as root: `("runuser", "-u", "postgres", "--", *argv)`;
   - with sudo on PATH: `("sudo", "-u", "postgres", *argv)`;
   - otherwise None, which fails the step with the privilege message.
5. The constructor gains `login_user: Callable[[], str] | None = None`. The default returns
   `os.environ.get("SUDO_USER") or getpass.getuser()`. Nothing else in the public surface
   changes, and `PostgresLocalServiceInterface` is untouched.
6. The existing brew, apt and dnf behaviour is unchanged except that the formula is now
   `postgresql@17`.

## Where to change
- `src/vibey/infrastructure/postgres.py` only. Use edit_file for each change, never
  write_file (the file is 413 lines).
- `tests/infrastructure/test_postgres_local.py`: the nine `postgresql@18` literals (lines 163,
  175, 176, 183, 211, 245, 251, 252, 286) become `postgresql@17`. Do this with one checked
  replacement that asserts the count is 9 (EDITING-RULES rule 2). Append new tests; do not
  rewrite the file.

## Acceptance criteria
- [ ] Arch as root runs, in order:
      `pacman -S --needed --noconfirm postgresql`, `test -e .../PG_VERSION`,
      `runuser -u postgres -- initdb ...`, `systemctl enable --now postgresql`,
      `runuser -u postgres -- createuser --createdb alice`,
      `runuser -u postgres -- createdb --owner alice vibey`. The result is ok.
- [ ] Arch as a user goes through `sudo` and `sudo -u postgres`.
- [ ] An initialized data directory (the `test -e` exits 0) skips initdb.
- [ ] `createuser` or `createdb` answering "already exists" is success. That covers the
      replay.
- [ ] Each Arch failure is reported with its message: no privilege, pacman, initdb, service,
      role.
- [ ] Root and postgres users get no role, and say so.
- [ ] Brew installs and starts `postgresql@17`.
- [ ] Cross-check: the catalogue's macOS recipe names `postgresql@{POSTGRES_INSTALL_MAJOR}` and
      its Arch recipe names `postgresql`. Both are read from `vibey.domain.local_stack`, lane
      installer-catalogue.
- [ ] All existing tests in the file pass, and postgres.py stays at 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/infrastructure/test_postgres_local.py`, using the file's `_which` and
fake-runner style (see :350-371):
- `test_pacman_install_as_root_initializes_starts_and_creates_the_role`
- `test_pacman_install_uses_sudo_for_a_user`
- `test_pacman_skips_initdb_when_the_cluster_exists`
- `test_pacman_treats_an_existing_role_and_database_as_success`
- `test_pacman_failures_are_reported`, parametrized over pacman, initdb, service start and
  createuser.
- `test_pacman_requires_privilege`
- `test_pacman_creates_no_role_for_root_or_postgres`
- `test_homebrew_formula_matches_the_catalogue`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_postgres_local.py tests/cli/test_operational_commands.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure/test_postgres_local.py
    uv run coverage report --include='src/vibey/infrastructure/postgres.py' --fail-under=100

## Out of scope
- Moving PostgreSQL onto the generic package installer: it keeps its own service because
  initdb and the role are behaviour, not data.
- The CLI.
- apt and dnf behaviour.
- The chart.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
