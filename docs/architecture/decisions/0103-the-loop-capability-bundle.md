# 0103 — The loop capability bundle: declared by the person, locked by content, fetched only on their word

**Status:** proposed · **Date:** 2026-11-23 · **Cites:** SD-01 v1.0; sub-doctrines 8.b, 10.f, 12.c, 12.d · **Related:** ADR-0016, ADR-0017, ADR-0034, ADR-0092, ADR-0101, ADR-0102

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

A BUILD job can fall to any loop (`claudeloop`, `claudeloop-local`, `codexloop`, `gptossloop`,
`qwenloop`), and a handoff moves it between them. The operator ruled on 2026-11-22 that every loop
supports MCP servers, plugins, marketplaces, skills, files, pasted text and text, with vibey
providing one shared layer (the SP-LOOPS design, approach A). Plugins and MCP servers are code and
instruction a model acts on, and a marketplace can come from the network, so the questions this
record answers are who may say what a loop is given, how a run knows it is getting what was
approved, and when vibey may reach the network to get it.

## Decision

1. **One bundle, in the person's own configuration.** `[loops]` of the person's own `vibey.toml`
   (`bootstrap.acp_user_config`, ADR-0101) declares the marketplaces, plugins, MCP servers and
   skills. A project's `vibey.toml` is untrusted: its `[loops]` may only `disable`, held to the
   same rule as the person's own list; every other key is dropped and named. The schema is strict
   at every level (`BundleSpec.from_mapping`), so a typo is refused by key path rather than
   silently dropping a capability. The research-methodology plugin (`currency-research@vibey`)
   is the default.
2. **Locked by content.** Each marketplace is pinned in a lock file beside the configuration
   (`<configuration folder>/loops/lock.json`) by the sha256 of its tree, never followed through a
   symlink. The marketplace that ships in the wheel locks itself at first use, as
   `vibey-engine <installed version>`, scoped to its manifest and the plugin folders it lists;
   an upgrade is a new source and re-locks, the same release with other content is a mismatch.
3. **A run never fetches, and loads only a verified copy.** The resolver copies what the lock
   names into a fresh 0700 run snapshot and compares the copy with the locked records before
   anything loads from it; an unlocked or changed marketplace stops the run and names the command
   to run.
4. **The network only on the person's word.** `vibey loops marketplace update` is the one
   command that fetches. Its sources are an allowlist -- git over `https` (no credentials in the
   URL), `ssh` or `git`, or an absolute folder copied without git -- and git runs four fixed
   commands with the source after `--`, `protocol.allow=never` plus those three, the person's and
   the system's git configuration not read, no hooks, submodules or LFS, a scrubbed environment
   and one deadline. The store's copy is named by its digest, and the lock entry is written only
   after the copy is checked: the lock is the commit point, so a failed update changes nothing.
   The family's guarded web fetch (ADR-0102) is not used: it fetches pages as bounded text, not
   repository trees.
5. **One table writer.** vibey had no writer of `vibey.toml`. `TomlTrustedTableWriter` changes
   one table and keeps every other byte; it refuses (and prints the table to paste) rather than
   drop a comment inside the table, and checks that the result parses back to exactly the intended
   file before replacing it atomically with mode 0600.
6. **Text from a marketplace is shown safely.** Names, descriptions and skipped rows reach a
   terminal or a model through one allowlist cleaner (`SafeText`); `--json` carries the values
   typed.

## Consequences

- A fresh install lists the research skills with no network (`vibey loops skills list`), and a
  network marketplace is usable only after an explicit `update`.
- Run snapshots accumulate until removed. `vibey loops snapshots prune` removes old ones now;
  removal at the end of each run and a sweep at worker start belong to the phase that wires runs
  (SP-LOOPS Phase 4), which must also load only from the snapshot's plugin folders.
- The size cap on a git fetch is checked after the fetch, so a hostile remote can use disk for as
  long as git's deadline allows. Private https repositories need ssh (the person's credential
  helpers are deliberately not read).
- Not yet run against a real git server or a real `/plugin marketplace add`: the git flags are
  tested against a recording runner only, and the operator-run checks the SP-LOOPS reviews list
  stay open.

## Alternatives considered

- **Each loop's own plugin and marketplace mechanisms** (design approach B): behaviour and trust
  would differ per loop, and Codex's are unverified. Rejected by the operator.
- **A TOML library that keeps comments everywhere.** It would add a third-party dependency for
  one table; the refusal-plus-snippet keeps the person's comments without one, and the pattern
  matches `vibey connect`'s refusal of a commented settings file.
- **Fetching on demand during a run.** It would let a run reach the network on its own and load
  what nobody approved. Rejected by the design's anti-goals.
