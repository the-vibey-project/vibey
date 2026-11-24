# 0082 — Install, copy and reinstall in one command; the krypton interfaces uninstall cleanly; the core stays

**Status:** accepted · **Date:** 2026-10-03 · **Cites:** sub-doctrines 10.h, 10.l, 10.m, 12.c, 12.e and 12.h · **Related:** ADR-0019, ADR-0021, ADR-0037, ADR-0069, ADR-0080 · **Evidence:** `develop` at `3245dc5d8`; the files of `krypton-desktop-0.1.0-linux-x86_64.tar.gz` in the 3.4.0 release · **Canon:** drafts sub-doctrine 10.m, ratified by the operator's merge under Article II.3

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; `properdocs.yml` nav entries for this record and for
`docs/guides/install.md`; `docs/llms.txt` regenerated from that nav. All are in the change
that carries this record.

## Context

The operator asked for the codebase to be "as easy to copy and reinstall as insanely
possible", for an uninstall script for every krypton interface and the TUI, and ruled that
"vibey-engine's core lives forever, no uninstall script for that". Installing already took
one documented command (`uv tool install vibey-engine`), but nothing removed the clients:
krypton desktop alone installs three different ways (a Flatpak, four files under `/usr` from
the Ubuntu tarball, a macOS app), and its pairing with a hub leaves a device key on disk.

## Decision

1. **`scripts/install.sh`** installs uv if missing, then `uv tool install --reinstall
   vibey-engine`, and ends with `vibey doctor`. Because it reinstalls, running it again is a
   repair. `--with-krypton` adds `krypton-app`; `--from-source DIR` clones the full history
   into `DIR`, builds it with `uv sync --extra dev` and installs the commands from that copy,
   updating the same copy when run again.
2. **`scripts/uninstall-krypton.sh`** removes the krypton interfaces: `krypton-app` by the
   tool that installed it, the editor extension from every VS Code-family editor, and krypton
   desktop in each of its three forms. It is a dry run unless given `--yes`; it removes the
   macOS app only when its `Info.plist` names krypton's identifier; it never escalates —
   a root-owned file is printed as a `sudo` command; and it keeps settings and the pairing
   unless given `--purge`, printing the `vibey hub revoke` command first.
3. **The core is never uninstalled** (sub-doctrine 10.m). Neither script, nor anything else
   the project ships, removes vibey-engine. "The TUI" in the request is read accordingly: the
   `vibey` TUI is part of the core and stays; the terminal interface that belongs to krypton is
   the `krypton` command, which goes.
4. **Both are POSIX `sh`**, so they run before Python or uv exist, and both run from
   `curl … | sh` without a clone. Their identifiers default to the shipped ones and can be
   overridden by environment variables (12.h).

## Consequences

- `tests/scripts/test_install_scripts.py` runs both scripts for real against recording stubs
  of every tool they call, so each behaviour above is shown, and the invariant that nothing
  removes vibey-engine is asserted on every run. `tests/meta/test_install_scripts.py` checks
  each hard-coded identifier against the source it comes from — the Flatpak manifest, the
  desktop data files, the extension's manifest, the package names, and the binary the release
  checks — so a rename fails CI rather than leaving an uninstaller that misses its target.
- The Ubuntu tarball's file list is declared in the uninstaller. If a release starts
  installing more files, the meta test does not see them; shipping an install manifest inside
  the tarball would close that gap and is left for the release lane.
- The phone apps cannot be removed from a computer; the uninstaller says so rather than
  pretending.

## Amendment, 2026-11-24: `--full` runs vibey's own setup, and the install reports only what it saw

The operator asked for a true single-command install. `scripts/install.sh --full`, after the
install, runs the setup commands vibey already ships, in order, and stops at the first that
fails, naming the step and the command that re-runs it alone: `vibey install --postgres`,
then `vibey migrate` when `VIBEY_PG_MIGRATE_URL` is set, then `vibey connect --yes`. It
implements none of them itself (10.e). Each step is idempotent, so `--full` is safe to run
again, and each has its own switch (`VIBEY_FULL_POSTGRES`, `VIBEY_FULL_MIGRATE`,
`VIBEY_FULL_CONNECT`, all `1` by default; `VIBEY_FULL_CONNECT_CLIENTS` narrows the clients),
so nothing is forced (12.c). Steps run with stdin closed, because under `curl … | sh` stdin is
the script; where PostgreSQL would come from apt-get or dnf through sudo, the script says a
password may be asked before the step runs, and with no terminal to ask on it stops and says
what to run instead. Without `--full` the script runs exactly what it ran before.

The two steps that had no vibey command now have one, so that `--full` takes a new macOS or
Linux machine to where a first project runs on the local default engine, and each is useful
alone:

- **`vibey install --database`** (`LocalDatabaseSetup`) runs `psql` as the local PostgreSQL's
  administrator -- the person with Homebrew, the `postgres` account through `sudo -u` with
  apt-get or dnf, or `--admin-user` -- to create the owner role and the application role of
  ADR-0055 (`LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE`) and the database the owner owns, then
  runs `vibey migrate`'s own `OwnerMigration`. Each role's password is random, kept in libpq's
  password file (`PGPASSFILE`, else `~/.pgpass`, mode 0600) *before* the role exists, and
  reaches PostgreSQL only as a SCRAM verifier, so every DSN is password-free and every
  connection still proves a password (10.j): a peer or trusted-socket DSN was the easier path
  and 10.j forbids it. A role the file has no password for, or a database another role owns,
  is refused rather than taken over; a second run changes nothing. vibey reads
  `VIBEY_PG_URL` from the environment alone, so the command prints the one line to keep
  (`export VIBEY_PG_URL=postgresql://vibey_app@localhost:5432/vibey`) and the one-command form
  of `vibey migrate`; where that DSN should persist is left open (below). It does not rewrite
  `pg_hba.conf`, ADR-0061's owed step: the closing lines say it is still the person's.
- **`vibey install --model`** (`OllamaModelPuller`) pulls the tag `vibey models --default-tag`
  prints -- `VIBEY_OLLAMA_MODEL`, then `VIBEY_SOVEREIGN_MODEL`, then ADR-0099's default --
  through the Ollama API at `VIBEY_OLLAMA_URL`, after a bounded wait for Ollama to answer. It
  pulls nothing when the model is there, says the model and its size first (12.1 GB for the
  default), and refuses with the next step when Ollama is missing, silent, or the pull fails.

`--full` now runs, in order: `vibey install --postgres`, `vibey install --database`,
`vibey migrate` (only with `VIBEY_FULL_DATABASE=0` and `VIBEY_PG_MIGRATE_URL` set, for a
database of the person's own), Ollama, `vibey install --model`, `vibey connect --yes`; the new
switches are `VIBEY_FULL_DATABASE`, `VIBEY_FULL_OLLAMA` and `VIBEY_FULL_MODEL`. Ollama itself
follows the uv precedent above: skipped when `ollama` is on `PATH`; on macOS `brew install
ollama` and `brew services start ollama` (Homebrew, as `vibey install --postgres` uses there),
and without Homebrew a refusal naming the download page; on Linux Ollama's own installer from
`VIBEY_OLLAMA_INSTALLER` (default `https://ollama.com/install.sh`), fetched to a file and then
run, so a failed download stops the step instead of running half a script, after saying that
its sudo may ask for a password (and refusing with no terminal to ask on). The `VIBEY_PG_URL`
the database step printed is used for the rest of the run, so the closing `vibey doctor`
checks the new database, and it is repeated under "Still yours to do" with the `pg_hba.conf`
step.

The engine is installed as `vibey-engine[hub]` (`VIBEY_ENGINE_EXTRAS`, default `hub`; empty
installs the bare engine), from source as `--editable DIR[hub]`. Installing the published
0.4.0 bare into a throwaway home showed why: `vibey serve` and `vibey hub start` failed with
`No module named 'fastapi'`, so neither the hub nor the hub `vibey mcp` starts for an MCP
client could run, while `vibey-engine[hub]` served `GET /` with 200. krypton-app already
depends on `vibey-engine[hub]`.

Open: where `VIBEY_PG_URL` persists. Today it is the environment only, and the installer prints
the line for the person's shell profile; a `[database]` key in the person's own `vibey.toml`, or
writing the supervised services' environment file, would each be a decision of their own.

Three defects found in a run of the installer are fixed with it. When uv's tool bin
directory is not on `PATH`, the script looks there (`uv tool dir --bin`), adds it for the rest
of the run and prints the line for the shell profile; when `vibey` still cannot be found it
exits 1 with that line, instead of printing "vibey is installed" over a doctor that never ran
(12.e). `--help` prints its usage from a here-document, so it works when the script is piped
and `$0` is no file. And the closing line no longer names `scripts/uninstall-krypton.sh`, which
a piped install does not have: it names `uv tool uninstall krypton-app` and the uninstaller's
URL, and only when krypton was installed. The core is still never uninstalled (§3).
`tests/meta/test_install_scripts.py` now checks that every command and option `--full` passes
is one the `vibey` CLI ships, that the `VIBEY_PG_URL` line it reads is the one
`vibey install --database` prints, and that the engine is installed with the `hub` extra.
