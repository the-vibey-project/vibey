# 0061 — Every PostgreSQL connection authenticates with scram-sha-256

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrine 10.j, drafted in the change that carries this record and awaiting the operator's ratifying merge (Constitution Article II.3); sub-doctrines 10.c, 10.f, 12.c and 12.e · **Related:** ADR-0002, ADR-0020, ADR-0055 · **Evidence:** `develop` at `9abb8c05`, read 2026-09-25; the chart's server configuration booted in `postgres:17-alpine` on the operator's Mac the same day

**Owes:** the conduct is sub-doctrine 10.j, drafted in the same pull request for the
operator's ratifying merge (ADR-0020: the record argues, the canon states). This record
also owes the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.
Both are done in the change that carries it. It leaves one gap open, named under
*Consequences*: the local installer does not rewrite a package's `pg_hba.conf`.

## Context

ADR-0055 made the ledger append-only in the database. It also found that the role split
protects nothing while a local server trusts its socket. It shipped `local-auth`, which
fails when the owner or a superuser can connect with no password, and `db-passwordless`,
which only warned when the app database could. Its `pg_hba.conf` lines in `SECURITY.md`
§7 were offered as "the operator's to set": advice, not a requirement.

That left several gaps.

- An `md5` rule passed `local-auth`, although it accepts a replayable hash. So did a
  `password` rule, although it sends the password in clear.
- A server that stores passwords as `md5` passed too.
- The Helm chart's built-in PostgreSQL ran the image's default `pg_hba.conf`, which
  trusts the local socket.
- CI's services left the method to the image's default.

On 2026-09-25 the operator ruled, in their words: *"YES USE SCRAM-SHA-256, IT IS NOW
LAW!"*

## Decision

1. **The conduct is canon.** Sub-doctrine 10.j, filed under 10 (*No guarantees*) beside
   10.c, covers every PostgreSQL connection the project configures, documents or installs.
   Each one authenticates with `scram-sha-256`, local and remote alike, and every password
   is stored as a SCRAM verifier. `trust`, `md5` and clear-text `password` are named in the
   ruling. `peer` and `ident` are read as excluded too, because "scram-sha-256 and nothing
   else" admits no method that proves only the OS user. That reading is the operator's to
   confirm at the merge.
2. **`SECURITY.md` §7's lines are the required configuration.** They are local, loopback,
   and for a server that takes them, `0.0.0.0/0` and `::/0`, all `scram-sha-256`, with
   `password_encryption = scram-sha-256`. §5(a) no longer offers "run the worker as its
   own OS user" as an alternative.
3. **The chart declares the rule rather than inheriting a default** (12.c).
   - `<release>-postgres-hba` is a ConfigMap holding exactly those lines. The server
     starts with `-c hba_file=/etc/postgresql/vibey/pg_hba.conf -c
     password_encryption=scram-sha-256`, so an install whose data directory predates this
     record follows the rule on its next start.
   - `POSTGRES_INITDB_ARGS` and `POSTGRES_HOST_AUTH_METHOD` make a fresh data
     directory's own file say the same.
   - The surface-role script exports `PGPASSWORD` from `POSTGRES_PASSWORD`, because its
     `postStart` run connects over the socket, which now needs a password.
   - The method is deliberately not a value: 12.c's "everything configurable" does not
     make law a preference.
4. **CI declares it.** The three `postgres` services (`gates`, `noloss`,
   `postgres-compatibility`) set `POSTGRES_HOST_AUTH_METHOD: scram-sha-256` and
   `POSTGRES_INITDB_ARGS: --auth-local=scram-sha-256 --auth-host=scram-sha-256`. The
   suite already connects over TCP with a password, which the image's default rule
   already sent through scram-sha-256. So the tests' behaviour does not change; the
   declaration makes it the rule rather than the default.
5. **The checks fail rather than advise** (10.f, 12.e).
   - `local-auth` now also fails on an `md5` or `password` rule that can match the owner
     or a superuser, and when `password_encryption` is not `scram-sha-256`. It names each
     kind separately.
   - `db-passwordless` prints `FAIL` instead of `WARN`, and `vibey doctor` exits 1 on it.
   - `UNKNOWN` stays `UNKNOWN` and never becomes a pass.
6. **The installer says what it leaves.** `vibey install --postgres` and `vibey doctor
   --install-postgres` install the distribution's package, whose `pg_hba.conf` commonly
   trusts the socket. On success the install's detail names the step 10.j requires and
   points at §7.

## Consequences

- **A development machine that trusts its socket now fails `vibey doctor`.** That
  includes the operator's own Mac, which the test harness reaches over the local socket as the OS
  user with no password. The repository does not change that machine. The one-time steps
  are in the pull request that carries this record. After them, a password in
  `~/.pgpass` keeps password-less DSNs such as `postgresql://$USER@localhost:5432/...`
  working, because libpq and asyncpg both read it. `CONTRIBUTING.md` says so.
- **Owed: the installer does not rewrite `pg_hba.conf`.** Doing that safely means giving
  every role that logs in a password first; otherwise the edit locks the operator out.
  Which password to set, and where to keep it, is the operator's to choose. Until the
  installer can take that choice as a declaration, the gap is closed by the check: the
  install says what is missing, and `vibey doctor` fails until it is done (12.e: where a
  step cannot be made whole, automate the check that says it was missed).
- **An existing chart install changes behaviour on upgrade.** Anything that reached the
  built-in server through its socket with no password now needs one. In the chart that is
  only the surface-role script, which this change fixes. A managed server is the
  operator's; `local-auth` reports it.
- `db-passwordless` and `local-auth` still overlap, as ADR-0055's TODO says. Both now
  fail, so the overlap costs a duplicated line, never a missed failure.

## Alternatives considered

- **Keep `db-passwordless` a warning.** Rejected: under 10.j a trusted socket is no longer
  a choice doctor may pass, and a warning that exits 0 is the silent pass 10.f forbids.
- **Make the method a chart value defaulting to `scram-sha-256`.** Rejected: a value
  invites the exception the law forbids, and 12.c's configurability is about decisions
  that are the adopter's to make. This one is not.
- **Rely on `POSTGRES_INITDB_ARGS` alone.** Rejected: it applies only to a fresh data
  directory, so every existing install would keep a trusted socket. `hba_file` applies on
  every start.
- **Have the installer write `pg_hba.conf` now.** Deferred, not rejected: see
  *Consequences*. A lock-out is worse than a loud failure.
