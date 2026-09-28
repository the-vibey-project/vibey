---
id: skill-10-defensive-shell-scripting-de9ddb6b03
purpose: 10 defensive shell scripting
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-shell-scripting-and-userland/SKILL.md
requires: ["skill-9-choosing-a-shell-1420b58c65"]
links: ["skill-11-the-userland-80595ea51a"]
---

## §10. Defensive Shell Scripting

### 10.1 The template

```bash
#!/usr/bin/env bash
# Purpose: one line. Usage: script.sh <input> [output]
set -Eeuo pipefail
#   -E  ERR trap is inherited by functions and subshells
#   -e  exit on error (KNOW ITS LIMITS — §8.2 trap 5)
#   -u  error on unset variable      ← catches the rm -rf "$TYPO/" class
#   -o pipefail  a pipeline fails if ANY element fails
IFS=$'\n\t'                          # remove space from IFS: safer word splitting

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# --- cleanup that actually runs, on every exit path -------------------------
readonly TMPDIR_="$(mktemp -d)"      # mktemp -d, never a predictable /tmp path
cleanup() {
    local rc=$?
    rm -rf -- "$TMPDIR_"
    exit "$rc"
}
trap cleanup EXIT                    # EXIT fires for normal exit, set -e, and signals
trap 'die "interrupted"' INT TERM

die()  { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }
log()  { printf '[%s] %s\n' "$(date -Is)" "$*" >&2; }   # logs to stderr, not stdout

# --- required inputs, validated ---------------------------------------------
: "${INPUT_FILE:?INPUT_FILE must be set}"        # ${:?} is the cheapest validation
[[ -r $INPUT_FILE ]] || die "cannot read: $INPUT_FILE"

need() { command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"; }
need jq; need curl

main() {
    local out="${1:-/dev/stdout}"
    # ... work ...
}
main "$@"
```

### 10.2 The rules

1. **`shellcheck` in CI, non-negotiable.** It is the single highest-value tool in shell
   development and catches the entire quoting class mechanically. `shfmt` for formatting.
2. **Quote every expansion.** `"$var"`, `"$@"`, `"${arr[@]}"`. The exceptions are rare
   and deliberate.
3. **`local` every function variable.** Shell variables are global by default; a function
   that forgets `local i` will silently corrupt its caller's loop.
4. **Never parse `ls`.** Use globs (`for f in ./*.txt`) or `find -print0 | while IFS= read
   -r -d '' f`.
5. **`--` before user-controlled arguments**: `rm -- "$f"`. A file named `-rf` is legal.
6. **Prefix globs with `./`**: `rm ./*` not `rm *`, for the same reason.
7. **`mktemp`, always.** Predictable temp paths are a symlink-attack primitive.
8. **`trap ... EXIT` for cleanup**, not cleanup code at the end (which `set -e` skips).
9. **Log to stderr; put data on stdout.** This is what makes a script composable.
10. **Exit codes mean something**: 0 success, 1 general, 2 usage, 126 not executable,
    127 not found, 128+N killed by signal N.
11. **Idempotence.** Assume the script will be re-run after failing halfway.
12. **`set -x` / `PS4='+ ${BASH_SOURCE}:${LINENO}: '`** for tracing, and
    `bash -n script.sh` for a syntax-only check.
13. **When it exceeds ~200 lines or needs real data structures — stop and use Python.**
    This is the most commonly ignored and most valuable rule in the list.

### 10.3 The safety cases

```bash
# THE classic. With set -u, a typo'd or empty variable exits instead of deleting /.
rm -rf "${BUILD_DIR:?BUILD_DIR not set}"/*

# Confirm before anything destructive when interactive
if [[ -t 0 ]]; then read -r -p "Delete ${count} files? [y/N] " a; [[ $a == [yY] ]] || exit 1; fi

# Atomic file replacement — same recipe as §1.5, in shell
tmp="$(mktemp -- "${target}.XXXXXX")"
generate > "$tmp" && mv -- "$tmp" "$target"     # mv within a filesystem is atomic

# Concurrency: a real lock, not a PID file
exec 9>/var/lock/myjob.lock
flock -n 9 || die "already running"

# Retry with backoff
for i in 1 2 4 8 16; do curl -fsS "$url" && break; sleep "$i"; done
```

---
