#!/bin/sh
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Install vibey, reinstall it, or copy the whole codebase — one command, safe to run again.
#
#   sh scripts/install.sh                      # install or upgrade vibey-engine
#   sh scripts/install.sh --with-krypton       # ... and the krypton apps
#   sh scripts/install.sh --from-source DIR    # copy the codebase into DIR and build it
#
# Without the repository:
#   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
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

WITH_KRYPTON=0
SOURCE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --with-krypton) WITH_KRYPTON=1 ;;
    --from-source)
      [ $# -ge 2 ] || { echo "install: --from-source needs a directory" >&2; exit 2; }
      SOURCE_DIR="$2"; shift ;;
    -h|--help) sed -n '4,17p' "$0" 2>/dev/null; exit 0 ;;
    *) echo "install: unknown option $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

have() { command -v "$1" >/dev/null 2>&1; }
say() { printf '%s\n' "$*"; }

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

say
say "Checking the result with vibey doctor:"
# The doctor says what still needs a person (PostgreSQL, Ollama, a login); it is a report, so
# its findings do not fail the install.
vibey doctor || true
say
say "vibey is installed. To remove the krypton apps later: sh scripts/uninstall-krypton.sh"
