#!/bin/sh
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Install vibey, reinstall it, or copy the whole codebase — one command, safe to run again.
# `--full` then runs vibey's own setup commands. `--help` prints the usage (from `usage`
# below, so it works when the script is piped and there is no file to read).
#
# Running it again is a reinstall: `uv tool install --reinstall` replaces what is there, so a
# broken install is repaired by the same command that made it. It asks nothing, changes nothing
# it did not install, and ends by running `vibey doctor` so you see what still needs you.
# POSIX sh on purpose, so it runs before Python or uv exist. ADR-0082.

set -eu

REPOSITORY="${VIBEY_REPOSITORY:-https://github.com/the-vibey-project/vibey.git}"
ENGINE="${VIBEY_ENGINE_PACKAGE:-vibey-engine}"
APPS="${VIBEY_APPS_PACKAGE:-krypton-app}"
UV_INSTALLER="${VIBEY_UV_INSTALLER:-https://astral.sh/uv/install.sh}"
UNINSTALLER="${VIBEY_KRYPTON_UNINSTALLER:-https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh}"
# --full: each setup step has its own switch (0 skips it), so none is forced on anyone.
FULL_POSTGRES="${VIBEY_FULL_POSTGRES:-1}"
FULL_MIGRATE="${VIBEY_FULL_MIGRATE:-1}"
FULL_CONNECT="${VIBEY_FULL_CONNECT:-1}"
# Client ids for `vibey connect --client` (space- or comma-separated); empty means every client.
FULL_CONNECT_CLIENTS="${VIBEY_FULL_CONNECT_CLIENTS:-}"
# The terminal a password prompt is read from. Under `curl ... | sh` stdin is the script itself.
TTY="${VIBEY_TTY:-/dev/tty}"

usage() {
  cat <<'USAGE'
Install vibey, reinstall it, or copy the whole codebase. Safe to run again.

  sh scripts/install.sh                      # install or upgrade vibey-engine
  sh scripts/install.sh --with-krypton       # ... and the krypton apps
  sh scripts/install.sh --from-source DIR    # copy the codebase into DIR and build it
  sh scripts/install.sh --full               # ... then run vibey's own setup commands

Without the repository:
  curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
  curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --full

--full runs these after the install, in order, and stops at the first that fails:
  vibey install --postgres   install and start PostgreSQL (on Linux, sudo may ask for your password)
  vibey migrate              only when VIBEY_PG_MIGRATE_URL (the owner's DSN) and VIBEY_PG_URL are set
  vibey connect --yes        plug vibey into your chat and IDE clients
Skip one with VIBEY_FULL_POSTGRES=0, VIBEY_FULL_MIGRATE=0 or VIBEY_FULL_CONNECT=0.
VIBEY_FULL_CONNECT_CLIENTS="codex zed" connects only those clients.
It does not create the database or install Ollama and its model: it prints what to run.

Running it again is a reinstall, so a broken install is repaired by the same command; --full
is safe to repeat too. It ends by running vibey doctor, which lists what still needs you.
USAGE
}

WITH_KRYPTON=0
FULL=0
SOURCE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --with-krypton) WITH_KRYPTON=1 ;;
    --full) FULL=1 ;;
    --from-source)
      [ $# -ge 2 ] || { echo "install: --from-source needs a directory" >&2; exit 2; }
      SOURCE_DIR="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "install: unknown option $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

have() { command -v "$1" >/dev/null 2>&1; }
say() { printf '%s\n' "$*"; }

# One --full step: say what it is about to run, run it with stdin closed (a piped script's
# stdin is the rest of the script, and every prompt belongs on the terminal), and on failure
# stop the whole run, naming the step and the command that re-runs it on its own.
step() {
  name="$1"; shift
  say "$1"; shift
  "$@" </dev/null && return 0
  status=$?
  say "install: the ${name} step failed (exit ${status}). Fix what it said above, then re-run it: $*" >&2
  say "Running this installer again with --full is safe: each step leaves done work as it is." >&2
  exit "$status"
}

# `vibey install --postgres` uses Homebrew when it is here, and otherwise apt-get or dnf through
# sudo unless this is root (PostgresLocalService reads them in that order).
postgres_needs_sudo() {
  ! have brew && { have apt-get || have dnf; } && [ "$(id -u)" -ne 0 ]
}
have_terminal() { (: <"$TTY") 2>/dev/null; }

# uv is the one tool everything else comes from (ADR-0021). Its own installer puts it in
# ~/.local/bin; that directory is added to this run's PATH so the next steps find it.
if ! have uv; then
  say "Installing uv, which installs everything else..."
  curl -fsSL "$UV_INSTALLER" | sh
  PATH="${HOME}/.local/bin:${PATH}"
  export PATH
fi
have uv || { say "install: uv is still not on PATH; open a new terminal and run this again." >&2; exit 1; }

if [ -n "$SOURCE_DIR" ]; then
  # A full copy: every commit, every tenant, every document — what the Rebuild prompt starts from.
  if [ -d "${SOURCE_DIR}/.git" ]; then
    say "Updating the copy in ${SOURCE_DIR}..."
    git -C "$SOURCE_DIR" pull --ff-only
  else
    say "Copying the codebase into ${SOURCE_DIR}..."
    git clone "$REPOSITORY" "$SOURCE_DIR"
  fi
  say "Building it (uv sync --extra dev)..."
  (cd "$SOURCE_DIR" && uv sync --extra dev)
  say "Installing the commands from that copy..."
  uv tool install --reinstall --editable "$SOURCE_DIR"
  [ "$WITH_KRYPTON" -eq 1 ] && uv tool install --reinstall --editable "${SOURCE_DIR}/clients/krypton-app"
else
  say "Installing ${ENGINE} (a reinstall if it is already here)..."
  uv tool install --reinstall "$ENGINE"
  if [ "$WITH_KRYPTON" -eq 1 ]; then
    say "Installing ${APPS}..."
    uv tool install --reinstall "$APPS"
  fi
fi

# uv puts the commands in its tool bin directory, which is not on PATH when uv was already
# installed elsewhere or the shell predates it. Look there rather than report an install
# nobody can run (12.e: no success that was not observed).
PATH_LINE=""
if ! have vibey; then
  TOOL_BIN="$(uv tool dir --bin 2>/dev/null || true)"
  PATH_LINE="export PATH=\"${TOOL_BIN:-\$(uv tool dir --bin)}:\$PATH\""
  if [ -n "$TOOL_BIN" ] && [ -x "${TOOL_BIN}/vibey" ]; then
    PATH="${TOOL_BIN}:${PATH}"
    export PATH
  fi
  if ! have vibey; then
    say "install: vibey was installed but is not on PATH, so it cannot run." >&2
    say "Add this line to your shell profile (~/.profile, ~/.bashrc or ~/.zshrc), open a new terminal, and run vibey doctor:" >&2
    say "  ${PATH_LINE}" >&2
    exit 1
  fi
fi

LATER=""
if [ "$FULL" -eq 1 ]; then
  if [ "$FULL_POSTGRES" = 1 ]; then
    if postgres_needs_sudo; then
      if ! have_terminal && ! sudo -n true 2>/dev/null; then
        say "install: the postgres step needs sudo (apt-get or dnf), which needs your password, and there is no terminal to ask on." >&2
        say "Run it from a terminal: vibey install --postgres. Or set VIBEY_FULL_POSTGRES=0 when PostgreSQL 14+ already runs here." >&2
        exit 1
      fi
      say "The next step runs apt-get or dnf through sudo, which may ask for your password."
    fi
    step postgres "Installing and starting PostgreSQL: vibey install --postgres" vibey install --postgres
  fi
  if [ "$FULL_MIGRATE" = 1 ]; then
    if [ -n "${VIBEY_PG_MIGRATE_URL:-}" ]; then
      step migrate "Applying the database migrations as the owner: vibey migrate" vibey migrate
    else
      say "Not migrating the database: VIBEY_PG_MIGRATE_URL is not set (creating the database and its roles is yours)."
      LATER="${LATER}
  The database: createdb vibey, then VIBEY_PG_MIGRATE_URL=postgresql://\$USER@localhost:5432/vibey VIBEY_PG_URL=postgresql://vibey_app:<password>@localhost:5432/vibey vibey migrate"
    fi
  fi
  if [ "$FULL_CONNECT" = 1 ]; then
    connect_args="--yes"
    for client in $(printf '%s' "$FULL_CONNECT_CLIENTS" | tr ',' ' '); do
      connect_args="${connect_args} --client ${client}"
    done
    # Unquoted on purpose: one argument per word. Claude Code and VS Code are connected for
    # the current directory (their entries are project-scope).
    # shellcheck disable=SC2086
    step connect "Plugging vibey into your chat and IDE clients: vibey connect ${connect_args}" vibey connect $connect_args
  fi
  LATER="${LATER}
  Ollama and the default model: install Ollama (https://ollama.com/download), then run the ollama pull command vibey doctor names."
fi

say
say "Checking the result with vibey doctor:"
# The doctor says what still needs a person (PostgreSQL, Ollama, a login); it is a report, so
# its findings do not fail the install.
vibey doctor || true
say
say "vibey is installed."
if [ -n "$PATH_LINE" ]; then
  say "Its directory is not on your PATH yet. Add this line to your shell profile: ${PATH_LINE}"
fi
if [ -n "$LATER" ]; then
  say "Still yours to do:${LATER}"
fi
if [ "$WITH_KRYPTON" -eq 1 ]; then
  say "To remove the krypton apps later: uv tool uninstall ${APPS} (or every krypton interface: curl -fsSL ${UNINSTALLER} | sh)"
fi
