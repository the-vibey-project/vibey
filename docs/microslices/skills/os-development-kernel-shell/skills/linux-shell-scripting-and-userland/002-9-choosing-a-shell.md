---
id: skill-9-choosing-a-shell-1420b58c65
purpose: 9 choosing a shell
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-shell-scripting-and-userland/SKILL.md
requires: ["skill-8-shell-semantics-the-part-that-causes-the-bugs-17db45c4f3"]
links: ["skill-10-defensive-shell-scripting-de9ddb6b03"]
---

## §9. Choosing a Shell

### 9.1 The comparison

| | **bash** | **zsh** | **fish** | **nushell** | **POSIX sh** (dash) |
|---|---|---|---|---|---|
| Version (Aug 2026) | **5.3** (July 2025) | **5.9.1** (May 2026) | **4.7** (May 2026) | 0.111+ (pre-1.0) | — |
| Written in | C | C | **Rust** (since 4.0) | Rust | C |
| Default on | Most Linux distros | **macOS since Catalina** | none | none | Debian `/bin/sh` |
| POSIX-compatible | Yes (mostly) | Mostly | **No, by design** | **No** | Yes, by definition |
| Runs bash scripts | — | Mostly unmodified | No | No | Only POSIX ones |
| Interactive out of box | Poor | Good with plugins | **Excellent** | Good | Minimal |
| Structured data | No | No | No | **Yes — tables, JSON, SQLite natively** | No |
| Best for | **Scripts, portability, servers** | Daily interactive on macOS/Linux with bash compat | Best interactive UX | Data wrangling in the terminal | `#!/bin/sh` scripts, containers |

**Adoption reality**: Stack Overflow's 2025 survey put Bash/shell scripting at **49% of
developers**, ranking fifth among all languages, ahead of TypeScript. Apple's 2019 switch
of the macOS default to zsh is the single largest driver of zsh adoption. Fish sits around
7% among developers.

### 9.2 The version that matters: bash 5.3

**[VERSIONED] Bash 5.3 (3 July 2025)** — the first release in three years. What's
actually new and useful:
- **`${ command; }`** — command substitution that **runs in the current shell context, no
  fork**, capturing stdout. And **`${| command; }`**, which runs in the current shell and
  leaves the result in `REPLY`. This is the headline feature and it matters for
  performance in loops.
- **`GLOBSORT`** — control pathname-completion/glob sort order by name, size, blocks,
  mtime, atime, ctime, numeric, or none, ascending or descending.
- `source -p PATH` to search a given PATH instead of `$PATH`.
- **Executing the RHS of `&&`/`||` no longer forks when unnecessary** — a real scripting
  speedup.
- `local -` saves and restores single-letter shell options for the function's duration.
- `compgen`/`complete -o nosort`; `wait` can now wait on the most recent process
  substitution; `unset var[0]` behaves like `${var[0]}`.
- **Source updated for C23 conformance — bash no longer compiles with K&R C compilers.**
- Readline 8.3 alongside: case-insensitive search option, `export-completions`,
  `force-meta-prefix`, `rl_print_keybinding`.

> **⚠️ GOTCHA — macOS ships bash 3.2.** Apple has not shipped a newer bash since the
> GPLv3 licence change in 2007. Any script relying on associative arrays (bash 4.0),
> `${var,,}` case conversion (4.0), `readarray`/`mapfile` (4.0), or `${ ... }` (5.3) will
> fail on a stock Mac. Either target POSIX sh, or require `brew install bash` and use
> `#!/usr/bin/env bash`.

### 9.3 The pragmatic answer

**[DURABLE, and the consensus across essentially every practitioner comparison]:**
> **Use whatever you like interactively. Write bash (or POSIX sh) for anything that has
> to run somewhere else.**

fish and nushell are genuinely better interactive shells and genuinely worse scripting
targets — fish requires rewriting with `set`, `if…end`, and function-scoped variables;
nushell requires rethinking (no subshells, no `$(...)`, structured pipelines). The
recurring, practical friction with fish: version managers (nvm, rbenv, pyenv, asdf,
sdkman) all ship bash/zsh hooks, and fish users depend on community wrappers that lag.
And — a distinctly 2026 problem — **AI coding agents shell out to the system default
shell**, so a non-POSIX default shell introduces a whole class of tooling breakage.

For **portable scripts**, target POSIX `sh` and test with `dash`. Bash-isms silently work
on a bash-as-/bin/sh system and break on Debian/Ubuntu where `/bin/sh` is `dash`, and in
Alpine containers where it's busybox `ash`. `shellcheck -s sh` catches this.

---
