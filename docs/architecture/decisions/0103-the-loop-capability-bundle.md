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
   URL) or `ssh` (a plain user name), or an absolute folder copied without git. `git://` is
   refused like `http://`: both are plaintext with no integrity, and a tree an on-path attacker
   served would be locked as trusted. git runs four fixed commands with the source after `--`,
   `protocol.allow=never` plus those two, `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` at the null
   device (honoured from git 2.32), an empty `HOME` of its own for an https source (so neither
   `~/.gitconfig` nor `~/.netrc` is read on any git) and the person's `HOME` and ssh agent only for
   ssh (where a git older than 2.32 still reads `~/.gitconfig`), no hooks, submodules or LFS, a
   scrubbed environment, one deadline, and each call in a process group killed whole on a timeout
   with its output read back capped. The store's copy is named by its digest; the copy is placed,
   its lock entry written and every copy the lock no longer names removed under one hold of the
   lock's own file lock (a bounded wait), so the lock is the commit point: a failed update changes
   nothing, and overlapping updates cannot remove the copy the lock names. A change to `[loops]`
   holds the same kind of lock beside `vibey.toml`.
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
  (SP-LOOPS Phase 4), which must also load only from the snapshot's plugin folders. *Closed by
  Phase 4 (below): a BUILD run's snapshot folder is removed when the run ends and a starting
  worker sweeps the rest (R10); a snapshot run loads plugins only from the snapshot's plugin
  folders, with no Claude settings at all (R5).*
- The size cap on a git fetch is checked after the fetch, so a hostile remote can use disk for as
  long as git's deadline allows. Private https repositories need ssh: neither the person's
  credential helpers nor `~/.netrc` are read for https.
- A run snapshot is aged by the newest change at its top, so `snapshots prune` removes a run that
  has been inactive that long even if it still runs; Phase 4 should mark a live run (a lease or a
  marker the pruner honours). *Answered by Phase 4 (R10): no marker is needed, since a session is
  bounded by its engine run deadline and the worker's sweep never removes a folder younger than
  that deadline plus an hour. A `snapshots prune` a person runs by hand with a shorter age can
  still remove a running session's snapshot; that is their explicit act, and the CLI reference
  says so.*
- The file locks are `fcntl.flock`, POSIX only, like the rest of the family today; Windows is
  backlog #1097.
- An MCP server's `env_allow` never names a secret (a token, key, password or the Brave key):
  what a server prints reaches the model.
- Not yet run against a real git server or a real `/plugin marketplace add`: the git flags are
  tested against a recording runner only, and the operator-run checks the SP-LOOPS reviews list
  stay open.

## Phase 4: claudeloop and claudeloop-local apply the snapshot

SP-LOOPS Phase 4 (plan `docs/superpowers/plans/2026-11-24-sp-loops-phase4-claudeloop.md`) makes
the first loops apply the bundle. The status above is unchanged; these are its rulings.

- **R1 (transport).** The snapshot reaches the runner as a JSON document in the run's own 0700
  snapshot folder, outside the worktree the model edits, named by `claudeloop run --capabilities
  PATH`. The runners never import `vibey`.
- **R2 (scope).** Only `build.implement` runs are given the snapshot. BUILD's verify reviewer,
  DESIGN and DECOMPOSE keep their behaviour until a later phase.
- **R3 (event).** `LoopCapabilitiesSnapshotted` records, before the engine starts, the digest and
  counts a run was given, only for an engine whose descriptor takes the document
  (`capabilities_flag`). It is withheld from ledger publication, and it opens, closes and spends
  nothing under the no-loss rules.
- **R4 (built-in web).** A person-only `[loops] builtin_web`, default `false`, which claudeloop
  maps to disallowing Claude Code's `WebSearch` and `WebFetch` (`CLAUDE_BUILTIN_WEB_TOOLS`).
  vibey no longer passes `--web-search` or `--deep-research` to a claudeloop run, which amends the
  launch flags ADR-0092 recorded, and claudeloop's `web_search` capability is `false` until Phase 6
  gives every loop `vibey_search`. DESIGN's bounded research still asks for web search; it carries
  no snapshot.
- **R5 (settings).** `setting_sources=[]` and `strict_mcp_config=True` only when a snapshot is
  applied, so a snapshot run loads plugins only from the snapshot's plugin folders and loads no
  user, project or local Claude setting. A standalone `claudeloop run` without `--capabilities`
  is unchanged.
- **R6 (skills).** Exactly the catalog's skills, by qualified name `plugin:skill`; a skill the
  index skipped is never enabled. `[loops] skills` is not applied yet (Phase 7).
- **R7 (MCP).** `local` becomes `{"type": "stdio"}`, started through a scrubbed launcher that keeps
  only the `env_allow` names, reads their values from its own environment and execs the server;
  an absent name is skipped and logged by name. `remote` becomes `{"type": "http"}`, never `sse`.
  Which variables reach the session at all stays `[engine_environment]`'s decision.
- **R8 (instruction files).** claudeloop reads `CLAUDE.md` and `AGENTS.md` from the run's `cwd`
  only and appends them to the system prompt, never to the plan. A file over
  `[loops] instruction_max_bytes` is named with its size, never cut (ADR-0075); a symlink is
  refused.
- **R9 (failure).** A snapshot that cannot be resolved parks the job on a
  `loop_capabilities_unresolved` gate; a run never starts without it. claudeloop exits 78 on a
  document it refuses, which the `engine_misconfigured` gate then parks.
- **R10 (lifetime).** The run's snapshot folder is removed when the run's handler returns or
  raises. A worker sweeps at start, with an age of the larger of
  `[loops] snapshot_max_age_days` and the engine run deadline plus an hour.
- **R11 (`claudeloop-local`).** The same code path, except that `builtin_web = true` does not turn
  the web tools back on against a local backend; claudeloop says so in a notice.
- **R12 (merge with flags).** The snapshot and claudeloop's own `--plugin`, `--skill`,
  `--connector` and `--add-folder` are a union, the snapshot first. An MCP name in both, or
  `--web-search` beside `builtin_web = false`, is refused with exit 2. vibey never passes both.
- **R13 (new person-only keys).** `builtin_web` (`false`), `instruction_files`
  (`["CLAUDE.md", "AGENTS.md"]`, at most 16 plain names), `instruction_max_bytes` (`65536`, from 1
  to 1048576) and `snapshot_max_age_days` (`7`, at least 1). The first three enter the snapshot's
  digest; the last does not. A project's `[loops]` may still only `disable`.
- **R14 (document size).** The reader refuses a document over 4 MiB, a parser guard sized from
  the bundle's own caps, not a policy limit.

Still open after Phase 4:

- A mid-run `claudeloop connector add NAME` with a name the snapshot already gives is not refused
  at the `connector` command: the next connect fails with `CapabilityFlagConflict` inside the
  runner's resource flush.
- The worker's start-up sweep runs before any project is known, so it uses
  `VIBEY_ENGINE_MAX_RUN_MINUTES` or 240 minutes, not a project's `[engines] max_run_minutes`.
- None of this has run against a real `claude` binary or a real MCP server; the tests use
  recorded and scripted doubles.

## Alternatives considered

- **Each loop's own plugin and marketplace mechanisms** (design approach B): behaviour and trust
  would differ per loop, and Codex's are unverified. Rejected by the operator.
- **A TOML library that keeps comments everywhere.** It would add a third-party dependency for
  one table; the refusal-plus-snippet keeps the person's comments without one, and the pattern
  matches `vibey connect`'s refusal of a commented settings file.
- **Fetching on demand during a run.** It would let a run reach the network on its own and load
  what nobody approved. Rejected by the design's anti-goals.
