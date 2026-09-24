## Title
test(domain): an adversarial corpus against the destructive-command guard — blocked forms, and the known evasions pinned as strict xfails

## Why
Issue #301 (rewrite: `issue-audit/updates/301.md`, "Proposed child issues" 10), as in
`roadmap-301-adversarial-injection-suite-p1`. `src/vibey/domain/command_guard.py` documents eleven
rules (`:24-91`), each named for what it prevents — e.g. `GIT_HARD_RESET` "Destructive git hard reset
loses uncommitted changes", `FS_ROOT_RM` "Destructive root / home recursive delete" — and
`scan_command` (`:93-101`) "Scans a command string or argv sequence against destructive rules".
Probed on the integration tree (2026-09-22): `git -C /repo reset --hard`, `rm -r -f /` and
`rm -rf $HOME` pass the guard; `echo reboot later` is blocked (fail-closed over-match). 10.f
(`src/vibey_tools/gh/docs/doctrines.md:419`): the suite states exactly what the guard does. Tests only.

## Required behaviour
New `tests/domain/test_adversarial_command_guard.py` (provenance header copied from
`tests/domain/test_command_guard.py:1`). `from vibey.domain.command_guard import scan_command, CommandSecurityPolicy`.

**Blocked today (assert the rule id):**
| command | rule |
|---|---|
| `git  reset   --hard HEAD~1` | `GIT_HARD_RESET` |
| `GIT RESET --HARD` | `GIT_HARD_RESET` |
| `["git", "reset", "--hard"]` (argv form) | `GIT_HARD_RESET` |
| `git push origin main --force` | `GIT_FORCE_PUSH` |
| `git push -f` | `GIT_FORCE_PUSH` |
| `git push --force-with-lease` | `GIT_FORCE_PUSH` |
| `git branch -D main` | `GIT_DELETE_MAIN` |
| `rm -rf /*` | `FS_ROOT_RM` |
| `rm -fr /` | `FS_ROOT_RM` |
| `rm -rf ~` | `FS_ROOT_RM` |
| `/bin/rm -rf /` | `FS_ROOT_RM` |
| `mkfs.ext4 /dev/sda1` | `FS_MKFS` |
| `dd if=/dev/zero of=/dev/sda` | `FS_RAW_DD` |
| `chmod -R 777 /` | `FS_CHMOD_ROOT` |
| `sudo reboot` | `SYS_POWER` |
| `init 0` | `SYS_POWER` |
| `:(){ :\|:& };:` | `SYS_FORK_BOMB` |
| `psql -c 'DROP DATABASE prod'` | `SQL_DROP_DATABASE` |
| `drop table users;` | `SQL_DROP_TABLE` |

**Allowed today (assert `scan_command(...) is None` and `CommandSecurityPolicy().is_allowed(...)`):**
`git branch -D feature`, `git reset --soft HEAD~1`, `rm -rf ./build`.

**Fail-closed over-match, pinned as current behaviour (ordinary test, with a comment that it is
over-blocking, not a hole):** `echo reboot later` → `SYS_POWER`.

**Known evasions — `xfail(strict=True)` asserting the command IS blocked:**
- `git -C /repo reset --hard` — reason: "a global option between `git` and `reset` evades
  GIT_HARD_RESET (command_guard.py:29: `git\s+reset` must be adjacent)".
- `rm -r -f /` — reason: "split short flags evade FS_ROOT_RM (command_guard.py:49-52 matches one
  flag cluster)".
- `rm -rf $HOME` — reason: "the rule describes a home delete, but `$HOME` is not matched, only `~`".

Also: `CommandSecurityPolicy().check_command("git reset --hard")` raises `DestructiveCommandBlocked`
whose message starts with `"Blocked destructive command [GIT_HARD_RESET]"` (`:16-22`).

## Where to change
- New `tests/domain/test_adversarial_command_guard.py` only. No production change.

## Acceptance criteria
- [ ] Every table row passes; exactly three strict xfails report `xfailed`.
- [ ] `-rx` output lists the three reasons verbatim.

## Tests to write first (TDD)
`test_destructive_forms_are_blocked` (parametrized over the table),
`test_safe_forms_are_allowed`, `test_a_mention_in_an_argument_fails_closed`,
`test_known_evasions` (strict xfail, parametrized), `test_check_command_raises_with_the_rule_id`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider -rx tests/domain/test_adversarial_command_guard.py tests/domain/test_command_guard.py

## Out of scope
- Fixing the guard (one later lane per evasion, each flipping its xfail); shell parsing; sandboxing
  (`infrastructure/container/`). Docs. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
