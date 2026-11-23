# SP-LOOPS: uniform loop capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every loop (`claudeloop`, `claudeloop-local`, `codexloop`, `gptossloop`, `qwenloop`) takes MCP servers, plugins, marketplaces, skills, files, pasted text and text, searches only through the local SearXNG, and has the research-methodology skills.

**Architecture:** One declarative bundle in the person's own configuration; a resolver in the conductor turns it into a locked, run-scoped snapshot; each loop applies the snapshot the way its engine can and reports evidence. Shared code is stdlib-only in `vibey_runners.common`; the runners never import `vibey`.

**Tech Stack:** Python 3.12+, stdlib only for shared code, typer CLI, pytest + Hypothesis, import-linter, the existing hub web tools (ADR-0102).

**Spec:** `docs/superpowers/specs/2026-11-22-uniform-loop-capabilities-design.md` (approved by the operator 2026-11-22). Read it first: its "Decisions I made while designing" are binding.

**Scope of this document.** The design is eight pull requests whose later halves depend on what the earlier halves teach. Phases 1 and 2 are written in full below. Phases 3 to 8 are listed with their tasks and acceptance, and each is written in full with writing-plans right before it starts (the master plan's convention). Each phase is its own PR through the merge train.

## Global Constraints

- The project's `vibey.toml` is untrusted: marketplaces, plugins and MCP servers come only from the person's own configuration (`user_config_path("vibey")/vibey.toml`); a project may only narrow.
- A run never fetches from the network on its own. Marketplace fetches happen only on an explicit `vibey loops ...` command; runs use the lock.
- A loop never receives the host token, the agent token or any Brave key.
- Plugin, skill and MCP-config text from the locked bundle is instruction; MCP output, fetched pages, search results and project files are untrusted data, bounded and marked.
- A capability claim needs evidence (`EngineAffordances.evidence`); unknown is `None`, never `True`.
- `domain/` stays pure (AST-enforced). Code lives in classes with an interface beside each (`services/interfaces/`). TypeScript, never JavaScript.
- 100% branch coverage per layer, verified with xdist and an empty Missing column. No test depends on thread timing, sleeps, the platform, the network, or a real docker/podman/launchctl/systemctl.
- Never read or print real keys (fake values in tests). Conventional Commits with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; run `git commit` and `git push` in the foreground; never `--no-verify`.
- Pushes and test runs in a worktree use `VIBEY_TEST_TEMPLATE_DB=<a worktree-only name>`.

## Review Focus

Failure modes the spec implies that no task's happy path exercises, most likely first:

1. A marketplace manifest whose plugin `source` is `../..` or absolute: refused, never read. (Task 5)
2. A plugin or skills folder that is a symlink leaving the marketplace root: refused. (Task 5)
3. A marketplace whose files changed on disk after it was locked: the run refuses and names `vibey loops marketplace update`. (Task 7)
4. A project `vibey.toml` carrying a `[loops]` table that adds a marketplace or MCP server: ignored with a notice; a narrowing `disable` list is honoured. (Task 4)
5. A `SKILL.md` with an oversized or malformed frontmatter: skipped with a named reason, never crashes the index. (Task 5)

---

# Phase 1: evidence first

### Task 1: Descriptors tell the truth

**Files:**
- Modify: `src/vibey/infrastructure/engines/descriptors.py` (the `codexloop` `EngineAffordances`, ~line 244)
- Modify: `tests/infrastructure/engines/test_descriptors.py`; the golden files under `tests/infrastructure/engines/golden/`
- Create: `tests/meta/loop_runner_facts.py` (table), `tests/meta/test_loop_capability_evidence.py`

**Interfaces:**
- Produces: `RunnerFact(loop: str, capability: str, source: str, needle: str)` and `RUNNER_FACTS: tuple[RunnerFact, ...]` in `tests/meta/loop_runner_facts.py`. A fact says "the runner source file `source` (path under `src/vibey_runners/`) contains `needle`", which is the code that implements `capability`.

- [ ] **Step 1: Write the failing meta-test.** `test_every_true_claim_has_a_matching_runner_fact`: for every descriptor and every affordance that is `True` or a `PluginSystem`, assert a `RunnerFact` exists for that (loop, capability) and its `needle` is in the file text. `test_a_capability_without_runner_code_is_not_claimed`: for `codexloop` and `mcp`, no fact exists, so the descriptor value must be `None`.
- [ ] **Step 2: Run it:** `uv run pytest tests/meta/test_loop_capability_evidence.py -q`. Expected: FAIL on `codexloop` `mcp` (claimed `True`, no runner code).
- [ ] **Step 3: Fill `RUNNER_FACTS`** from what the runners really contain today (read each runner's CLI definition; examples: claudeloop `--connector` in `claude/src/claudeloop/cli/commands/run.py` for `mcp`, `--plugin` for `plugins`, `--add-folder` for `files`; the local runner's `mcp_list` / `mcp_call` for `mcp`). One fact per true claim; the needle is a literal string the file contains.
- [ ] **Step 4: Change the `codexloop` descriptor** `mcp=True` to `mcp=None` and update its `evidence` entry to say why (no MCP code in `codex/`). Update the golden JSON. Do not touch the other loops' values here.
- [ ] **Step 5: Run** `uv run pytest tests/meta tests/infrastructure/engines tests/domain/test_engine.py -q`. Expected: PASS.
- [ ] **Step 6: Commit** `fix(engines): stop claiming MCP for codexloop and pin every capability claim to runner code`.

### Task 2: `vibey loops` emits `skills` and `web_search`; the doc table matches

**Files:**
- Modify: `src/vibey/cli/loops.py` (the `_document` capabilities block and the presenter)
- Modify: `docs/reference/cli.md` (the `capabilities` row ~line 1520 and the per-loop table ~line 1547)
- Modify: `tests/cli/test_loops*.py` and the loops JSON golden; create `tests/meta/test_cli_doc_capabilities.py`

**Interfaces:**
- Produces: the `--json` `capabilities` object gains `skills` and `web_search` (each `true`, `false` or `null`), and `evidence` gains matching keys where set. The existing keys and exit codes do not change.

- [ ] **Step 1: Write failing tests.** In the loops CLI test, assert the JSON for `claudeloop` has `capabilities["skills"] is True` and `capabilities["web_search"] is True`, and for `codexloop` `capabilities["mcp"] is None`. In the meta test, assert every field name of `EngineAffordances` (except `evidence`) appears in the `capabilities` row of `docs/reference/cli.md`.
- [ ] **Step 2: Run them.** Expected: FAIL (keys missing; doc row lacks `skills`/`web_search`).
- [ ] **Step 3: Emit the two fields** in `_document` the way `files` is emitted, and list them in the human presenter.
- [ ] **Step 4: Correct the doc:** the `capabilities` row names every field; the per-loop table says `codexloop`: files, pasted text, `skills-context`; MCP unknown.
- [ ] **Step 5: Run** `uv run pytest tests/cli tests/meta -q`, then `uv run vibey-gh corpus-index --check`. Expected: PASS.
- [ ] **Step 6: Commit** `feat(cli): vibey loops reports skills and web_search; correct the capability table`.

Phase 1 ends with a PR. Acceptance: no descriptor claims a capability the runner code does not show; `vibey loops --json` is complete; `full_access_gaps()` is unchanged in shape (it shrinks only in later phases).

---

# Phase 2: the shared library and the conductor commands

Layout: `src/vibey_runners/common/src/vibey_runners/common/capabilities/` with one class per file and `interfaces/` beside; tests in `src/vibey_runners/common/tests/capabilities/`. The vibey side imports from it (the family package is dependency-free, so `domain/` may).

### Task 3: Bundle value objects and the trust rule

**Files:**
- Create: `capabilities/bundle.py`, `capabilities/interfaces/bundle_interface.py`; `src/vibey/application/loops_bundle_settings.py` (reads the person's `[loops]` table)
- Test: `src/vibey_runners/common/tests/capabilities/test_bundle.py`, `tests/application/test_loops_bundle_settings.py`

**Interfaces:**
- Produces (frozen dataclasses): `MarketplaceSpec(name: str, source: str, ref: str | None)`, `PluginSpec(name: str, marketplace: str)`, `McpServerSpec(name: str, trust: Literal["local","remote"], command: tuple[str, ...] | None, url: str | None, env_allow: tuple[str, ...])`, `BundleSpec(marketplaces: tuple[MarketplaceSpec, ...], plugins: tuple[PluginSpec, ...], mcp_servers: tuple[McpServerSpec, ...], skills: tuple[str, ...], disabled: frozenset[str])`.
- Produces: `BundleSpec.from_mapping(raw: Mapping[str, object]) -> BundleSpec` (raises `BundleError` with the key path), and `BundleSpec.narrowed_by(disabled: Iterable[str]) -> BundleSpec`.
- Produces: `LoopsBundleSettings.load(user_config: Path, project_config: Path | None) -> BundleSpec`: the user's `[loops]` table is the bundle; a project's `[loops]` contributes only `disable = [...]` (names of plugins, skills or MCP servers); any other project key is dropped and returned as a notice string.

- [ ] **Step 1: Write failing tests** with fake mappings: a full valid `[loops]`; a `remote` server with no `url` raises `BundleError("loops.mcp_servers[0].url")`; a `local` server with no `command` raises likewise; the default bundle (no table) is empty marketplaces plus the research plugin set (see Task 7's constant); a project table adding a marketplace yields the user's bundle unchanged plus a notice naming the key; a project `disable = ["currency-research"]` removes it.
- [ ] **Step 2: Run:** expect FAIL (module missing).
- [ ] **Step 3: Implement** the dataclasses and `from_mapping` (strict: unknown keys raise), and `LoopsBundleSettings` over the existing trusted-config loader (`load_trusted`, ADR-0101), not a second TOML reader.
- [ ] **Step 4: Run** the two test files; expect PASS. **Step 5: Commit** `feat(loops): the loop capability bundle and its trust rule`.

### Task 4: Marketplace manifest, plugin and skill reading

**Files:**
- Create: `capabilities/manifest.py` (`MarketplaceManifest`), `capabilities/skill_index.py` (`SkillIndex`), interfaces beside
- Test: `.../tests/capabilities/test_manifest.py`, `test_skill_index.py`

**Interfaces:**
- Produces: `MarketplaceManifest.read(root: Path) -> MarketplaceCatalog` where `MarketplaceCatalog.plugins: Mapping[str, PluginEntry]`, `PluginEntry(name: str, directory: Path, description: str)`. Reads `<root>/.claude-plugin/marketplace.json`.
- Produces: `SkillIndex.build(plugin_dirs: Sequence[Path]) -> SkillCatalog` where `SkillCatalog.skills: tuple[SkillEntry, ...]`, `SkillEntry(plugin: str, name: str, description: str, path: Path)` and `SkillCatalog.skipped: tuple[tuple[Path, str], ...]` (path and the named reason). Frontmatter is read from `skills/*/SKILL.md`.
- Consumes: a reader seam `FileReaderInterface.read_text(path, limit) -> str` so tests use an in-memory fake.

- [ ] **Step 1: Write failing tests** for Review Focus 1, 2 and 5 plus the happy path: a plugin `source` of `../x` and of an absolute path raises `ManifestError` and the file is never read; a skills directory that is a symlink resolving outside `root` is skipped with reason `"outside the marketplace"`; a `SKILL.md` over the size cap (cap = 64 KiB, a module constant) or with no `name:` is in `skipped` with a reason; a valid skill yields name and description.
- [ ] **Step 2: Run:** expect FAIL. **Step 3: Implement** both classes; resolve every path with `Path.resolve()` and require `relative_to(root.resolve())`.
- [ ] **Step 4: Run:** expect PASS. **Step 5: Commit** `feat(loops): read marketplace manifests and index skills safely`.

### Task 5: The lock file

**Files:**
- Create: `capabilities/lock.py` (`CapabilityLock`, `LockEntry`), interface beside
- Test: `.../tests/capabilities/test_lock.py`

**Interfaces:**
- Produces: `CapabilityLock.digest_tree(root: Path) -> str` (sha256 over sorted relative paths and file digests; symlinks are hashed by target text, never followed), `CapabilityLock.write(path: Path, entries: Sequence[LockEntry]) -> None` (atomic: temp file, fsync, rename, mode 0600), `CapabilityLock.read(path: Path) -> tuple[LockEntry, ...]`, with `LockEntry(marketplace: str, source: str, ref: str | None, digest: str)`.

- [ ] **Step 1: Write failing tests:** digest is stable across directory-listing order (Hypothesis over file sets); changing one byte changes the digest; a symlink is hashed by its target text and not followed; `write` then `read` round-trips; a truncated lock file raises `LockError` and never returns partial entries.
- [ ] **Step 2: Run:** expect FAIL. **Step 3: Implement.** **Step 4: Run:** expect PASS. **Step 5: Commit** `feat(loops): a content-hashed lock for marketplaces`.

### Task 6: Resolver and run-scoped snapshot

**Files:**
- Create: `capabilities/resolver.py` (`CapabilityResolver`), `capabilities/snapshot.py` (`CapabilitySnapshot`), interfaces beside; `capabilities/defaults.py` (`DEFAULT_MARKETPLACE_NAME = "vibey"`, `DEFAULT_RESEARCH_PLUGINS = ("currency-research",)`)
- Test: `.../tests/capabilities/test_resolver.py`

**Interfaces:**
- Consumes: Tasks 3 to 5.
- Produces: `CapabilityResolver.resolve(bundle: BundleSpec, lock: Sequence[LockEntry], roots: Mapping[str, Path]) -> CapabilitySnapshot`, where `roots` maps a marketplace name to its on-disk root. Raises `UnlockedMarketplaceError(name)` when a marketplace has no lock entry (message: `run \`vibey loops marketplace update <name>\``), and `LockMismatchError(name)` when the digest differs (Review Focus 3).
- Produces: `CapabilitySnapshot(plugin_dirs: tuple[Path, ...], skills: SkillCatalog, mcp_servers: tuple[McpServerSpec, ...], digest: str)` where `digest` is the sha256 of the lock entries and the bundle's canonical JSON, the value later recorded in the ledger.
- Default marketplace: its root is the copy that ships in the installed wheel; its lock entry is created automatically at first use (Decisions 1). A network marketplace is never auto-locked.

- [ ] **Step 1: Write failing tests:** unlocked network marketplace raises with the command to run; changed files after lock raises `LockMismatchError`; the default marketplace locks itself on first resolve and not again; `disabled` names are absent from the snapshot; the same inputs give the same `digest`.
- [ ] **Step 2: Run:** expect FAIL. **Step 3: Implement.**
- [ ] **Step 4: Verify the wheel carries the default marketplace:** `uv build --wheel` into `$TMPDIR`, then list its contents for `.claude-plugin/marketplace.json` and the `currency-research` plugin. If either is missing, add them to the wheel's package data in `pyproject.toml` and add `tests/meta/test_wheel_ships_default_marketplace.py` that reads the built wheel's file list. Record which case it was in the commit body.
- [ ] **Step 5: Run** the resolver tests; expect PASS. **Step 6: Commit** `feat(loops): resolve a bundle into a locked run-scoped snapshot`.

### Task 7: `vibey loops marketplace | plugin | mcp | skills`

**Files:**
- Create: `src/vibey/cli/loops_bundle.py` (`LoopsBundleCommands`) with `cli/interfaces/loops_bundle_interface.py`; register under the existing `loops` group in `cli/main.py`
- Modify: `docs/reference/cli.md`, `docs/reference/configuration.md` (the `[loops]` table), `CHANGELOG.md`
- Test: `tests/cli/test_loops_bundle.py`

**Interfaces:**
- Produces commands (all read and write only the person's own config and lock folder; none contacts the network except `marketplace add` and `update` of a git or http source): `vibey loops marketplace add NAME SOURCE [--ref REF]`, `marketplace update [NAME]`, `marketplace list`, `plugin add NAME@MARKETPLACE`, `plugin remove NAME`, `mcp add NAME --local -- CMD...` / `--remote URL`, `mcp list`, `skills list`. `list` commands accept `--json`.
- Network fetches go through the family's existing guarded fetch where it fits, else a `git` subprocess with an injected runner; tests use fakes only.

- [ ] **Step 1: Write failing CLI tests** with `CliRunner` and fake fetcher/lock paths: `marketplace add` writes the user's config and no lock until `update`; `update` writes the lock and prints the digest; `plugin add` for an unknown marketplace exits 2 and names it; `mcp add --remote` with a non-https URL exits 2; `skills list --json` lists the research skills from the default marketplace with no network.
- [ ] **Step 2: Run:** expect FAIL. **Step 3: Implement**; writes to the config go through the existing trusted-config writer pattern (comments preserved, 0600), never a hand-rolled second one.
- [ ] **Step 4: Docs and changelog**, then `uv run vibey-gh corpus-index --check`. **Step 5: Run** the 100% layer floors with xdist; expect an empty Missing column.
- [ ] **Step 6: Commit** `feat(cli): vibey loops marketplace, plugin, mcp and skills`.

Phase 2 ends with a PR. Acceptance: a fresh install lists the research skills with no network; a network marketplace is usable only after an explicit `update`; nothing yet changes how a loop runs.

---

# Phases 3 to 8 (each written in full right before it starts)

**Phase 3, the input set.** Tasks: a hash-addressed inputs folder under the project's state (size limits, 0700); `vibey run --paste`, `--file` and ACP embedded resources write into it; one `RunInputs` value (plan, attachments dir, paste file) every loop reads; ledger records digests only. Acceptance: the same paste and file reach every loop through one code path; nothing enters Postgres.

**Phase 4, `claudeloop` and `claudeloop-local`.** Tasks: apply the snapshot (plugins as local directories, MCP connectors with an explicit transport `type`, skills by name, `setting_sources=[]`, repo `CLAUDE.md` and `AGENTS.md` injected as text, attachments added to the agent's folders); disallow `WebSearch` and `WebFetch`; fix `--attach` so files reach the agent; record the snapshot digest in a new append-only ledger event `LoopCapabilitiesSnapshotted` at job start; evidence entries added to the descriptor. Acceptance: a real-run probe (operator-run) shows a plugin skill, an MCP tool and a pasted file in one run.

**Phase 5, the local runner (`gptossloop`, `qwenloop`).** Tasks: MCP client over the shared JSON-RPC peer moved into `common` (stdio plus HTTP, persistent session, schemas on demand within a token budget); skill tools over the snapshot (`skills_list`, `skill_read`); `PluginSystem.VIBEY_BUNDLE` added, `full_access_gaps()` counts it, ADR-0092 amended; research skills listed (names and descriptions only) in the system prompt. Acceptance: the sovereign default has every capability the paid loops have, within a 32k context.

**Phase 6, per-session web principal and hub-served search.** Tasks: the worker mints a `web`-only principal per engine session with its own budget; every loop reaches `vibey_search` and `vibey_fetch` through the hub; sessions stop receiving the SearXNG address and marker; a worker without a hub says so and runs without search. Acceptance: no session environment holds a SearXNG address or any Brave key (a test walks the child environment).

**Phase 7, the research bundle by default.** Tasks: the default bundle names the research plugins; DESIGN and REVIEW list them as required skills; a meta-test keeps the list and the `currency-research` plugin in step. Acceptance: a new install's DESIGN prompt names the three research skills.

**Phase 8, `codexloop`.** Starts only after the operator runs a verification of what the real Codex supports for MCP and skills and records it. Tasks come from that result; until then `codexloop` keeps its declared gaps and rotation honours them (Decisions 7).

## Self-review

- **Spec coverage:** Goals 1 and 2 (Phase 2), 3 (Phases 4, 5, 8), 4 (Phase 3), 5 (Phase 6), 6 (Phase 7), 7 (Phase 1, then each phase's evidence entry). Decisions 1 to 10 are each carried: 1 in Task 6, 2 in Phases 4 and 6, 3 in Global Constraints, 4 in Phase 4, 5 in Phase 6, 6 in Phase 3, 7 in Phase 1 and 8, 8 in Phase 5, 9 in Phase 5 (and Task 3's `trust`), 10 in Phases 5 and 7.
- **Type consistency:** `BundleSpec`, `MarketplaceSpec`, `PluginSpec`, `McpServerSpec` (Task 3) are the inputs of Tasks 6 and 7; `LockEntry` (Task 5) feeds Task 6; `SkillCatalog` (Task 4) is a field of `CapabilitySnapshot` (Task 6).
- **Left to the builder:** names of private helpers, the exact JSON of the lock file, the cap constants other than the 64 KiB skill-file limit, and which existing fetcher Task 7 reuses.
