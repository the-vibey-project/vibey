# Pre-1.0 Versioning at 0.3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vibey-engine` and `krypton-app` read 0.3.0, the code stays pre-1.0 until the operator says otherwise, and `vibey --version` / `vibey -v` print both versions.

**Architecture:** Three independent pieces. (1) A declared cap in `.vibey-gh.toml` (`[version] max_major = 0`) that `vibey-gh`'s derivation honours, so a breaking change bumps the minor and 1.0.0 is never proposed; (2) the version files set to 0.3.0 and a meta test that no declared version reads 1.0 or above while the cap is set; (3) the `vibey` CLI prints both versions on `--version` and `-v`, and the counted verbose flag moves off `-v`. Tagging, publishing and the old versions' removal stay with the operator (Task 4 is a gate, not work).

**Tech Stack:** Python 3.12, typer, vibey-gh (`src/vibey_tools/gh/vibey_gh/versioning.py`), pytest meta tests.

**Spec:** the operator's request of 2026-11-12 and these rulings (same day): `-v` means version and verbose moves; `--version` prints two lines; the pre-1.0 rule is a declared cap in `.vibey-gh.toml`.

## Global Constraints

- Everything-as-code and configurable (CLAUDE.md): the cap is a key, not a hard-coded constant; removing the key lifts it.
- A governing rule is a ratified sub-doctrine: the pre-1.0 rule is proposed in a separate canon PR the operator merges (not in this PR), plus an ADR.
- vibey_gh keeps its 100% coverage floor; every new branch has a test. `mypy --strict` stays at 0 errors on `src/vibey` and on vibey_gh (strict since #1896; if that PR is not merged yet, add no new errors).
- `domain/` stays pure; the CLI reads `krypton-app`'s version through `importlib.metadata`, never by importing it.
- No tag, release, publish, PyPI call or `vibey-gh rulesets` apply. The operator deletes the old versions.
- Conventional Commits; no `--no-verify`; commit and push in the foreground; a PR touching shipped code needs a `changelog.d/<slug>.<type>.md` fragment; no personal data in files.

## Review Focus

1. A breaking change under the cap yields a minor bump, never `1.0.0`, and the cap off yields today's behaviour exactly.
2. `vibey -v` alone prints the version, and nothing that used to rely on `-v` as verbose silently changes meaning (the `-vv`/`-vvv` wire-log path, `tests/cli/test_workflows_cli.py` passthrough, `test_state_cli.py`).
3. `krypton-app` not installed prints `krypton-app not installed`, never a traceback or a guessed number.
4. No version file can read 1.0 or above without failing the meta test while the cap is set.
5. Nothing in this PR makes CI pull a PyPI version that no longer exists (see the open point under Task 4).

---

### Task 1: The cap in vibey-gh

**Files:** Modify `src/vibey_tools/gh/vibey_gh/versioning.py` (`bump`, `_staged`, `_classify`, ~lines 146-160, 266-326), `src/vibey_tools/gh/vibey_gh/config.py` (`[version]` loading near `content_paths`, ~3611 and ~4019), `.vibey-gh.toml` (`[version]`), the vibey-gh docs for `[version]` keys and its CHANGELOG convention; tests in `src/vibey_tools/gh/test/` beside the existing versioning tests.

**Interfaces:** Produces: `VersionConfig`/`GhConfig` field `max_major: int | None = None`; `bump(version, level, max_major=None)` where a `major` level at `max_major` is bumped as `minor` instead; the derivation's reason text says so ("break capped to a minor: [version] max_major = 0").

- [ ] **Step 1 (tests first):** `test_a_breaking_change_under_max_major_zero_bumps_the_minor`, `test_max_major_unset_keeps_a_breaking_change_major`, `test_max_major_is_a_non_negative_int` (a string, a bool or a negative number raises the loader's config error), `test_the_reason_names_the_cap`.
- [ ] **Step 2:** Implement the key and the cap; every code path that calls `bump(..., "major")` passes the config's value.
- [ ] **Step 3:** Set `max_major = 0` in `.vibey-gh.toml` `[version]` with a comment saying the operator lifts it by deleting the key.
- [ ] **Step 4:** Run the vibey_gh suite from `src/vibey_tools/gh` (100% coverage), black, isort, mypy; commit `feat(gh): let [version] cap the major so a project can stay pre-1.0`.

### Task 2: The CLI prints both versions and `-v` is the version flag

**Files:** Modify `src/vibey/cli/main.py` (`_version_callback` ~190-196, the `main` callback options ~199-215), its tests in `tests/cli/` (`test_errors_and_logging.py:107-112`, `test_state_cli.py:552`, `test_workflows_cli.py:126-128`, `test_llm.py:145`), `docs/reference/cli.md`, and any doc that tells a reader to type `-v`/`-vv`/`-vvv` for `vibey` (grep `vibey -v`, `-vvv`, `vibey llm tail`).

**Interfaces:** Produces: `vibey --version` and `vibey -v` print exactly two lines, `vibey-engine <version>` then `krypton-app <version>` (or `krypton-app not installed`), exit 0, eager (before any subcommand parsing). The counted verbose flag stays `--verbose` (repeatable) and gains the short flag `-d` (count, same semantics: `-d` debug, `-dd` third-party, `-ddd` full payloads); the help text and the `-vvv` mention in the option help are updated. The `claudeloop`/`codexloop` CLIs keep their own `-v` (out of scope).

- [ ] **Step 1 (tests first):** `test_version_and_dash_v_print_both_versions` (monkeypatch `importlib.metadata.version` for `krypton-app`), `test_krypton_app_not_installed_is_named_not_a_traceback`, `test_dash_d_counts_like_the_old_verbose`, update the existing tests that used `-v` as verbose to `-d`, and a test that `-v` together with a subcommand prints the version and exits (document this).
- [ ] **Step 2:** Implement in `main.py`; read `krypton-app` through `importlib.metadata.version` inside a function in a class per the repo's class rule if the surrounding code is class-based, else beside `_version_callback` with its reason.
- [ ] **Step 3:** Update `docs/reference/cli.md` and every doc found by the grep; regenerate any generated CLI reference with its generator (never hand-edit a generated file).
- [ ] **Step 4:** Run `uv run pytest tests/cli -q -p no:cacheprovider`, the four layer coverage gates on `src/vibey/cli`, `uv run mypy --strict src/vibey`, ruff; commit `feat(cli): print the engine and app versions on --version and -v; verbose moves to -d`.

### Task 3: Set the versions to 0.3.0 and hold them there

**Files:** `pyproject.toml` (`version = "4.6.0"` line 7), `src/vibey/__init__.py` (`__version__`), `CITATION.cff` (top-level `version:` only), `clients/krypton-app/pyproject.toml` (0.2.0 to 0.3.0), `uv.lock` (the editable `vibey-engine` entry; keep `revision` as is), the files `scripts/continuation_prompts.py render` rewrites (`docs/continuation/*.md`), tests that assert the old number (grep `4.6.0` and `4\.6` in `tests/`); Create `tests/meta/test_pre_1_0_versions.py`.

**Interfaces:** Consumes: `[version] files` and `max_major` from `.vibey-gh.toml` (read with the repo's TOML reader). Produces: a meta test that, while `max_major` is set, every version declared in `[version] files`, `clients/krypton-app/pyproject.toml`, `clients/vscode/package.json`, `clients/app/package.json` and `packages/vibey-core/package.json` has a major no greater than `max_major` (the app's `1.0.0` fails today: see the open point).

- [ ] **Step 1 (test first):** `test_every_declared_version_respects_max_major`; expect FAIL for `clients/app/package.json` (`1.0.0`) and for the engine (`4.6.0`).
- [ ] **Step 2:** Edit the version files; run `uv run python scripts/continuation_prompts.py render`; `uv lock --check` (restore `uv.lock`'s `revision` if uv rewrites it).
- [ ] **Step 3:** Leave workflow pins (`vibey-engine==4.6.0` in `release-surfaces.yml`, `skip-markers.yml`) and `docs/architecture/evidence/minimum-specs.json` alone: see Task 4.
- [ ] **Step 4:** `uv run pytest tests/meta -q -p no:cacheprovider`, ruff, `uv lock --check`; commit `chore(release): hold vibey-engine and krypton-app at 0.3.0, pre-1.0`.

### Task 4: Gate (the operator's, not an agent's)

This is not implemented here. It lists what only the operator can do and the order it needs.

- [ ] The operator deletes the old releases, tags (`vibey-v4.x` and the rest) and PyPI versions for `vibey-engine` and `krypton-app`. **Open point 1:** a tag `vibey-v0.3.0` already exists on an old commit, and PyPI refuses to re-upload a filename it has ever held, even a deleted one. If `vibey-engine` 0.3.0 was ever published, 0.3.0 cannot be published again; the operator decides between deleting nothing there and a different number.
- [ ] **Open point 2:** `release-surfaces.yml` and `skip-markers.yml` install `vibey-engine==4.6.0` from PyPI, and `docs/architecture/evidence/minimum-specs.json` quotes it. Once 4.6.0 is deleted those steps fail until a published version exists to pin. The order must be: publish 0.3.0, then move the pins (they are stamped by the release flow; find where before touching them).
- [ ] **Open point 3:** `clients/app/package.json` is `1.0.0` and `packages/vibey-core/package.json` is `0.2.0`; the request names only `vibey-engine` and `krypton-app`. The meta test above will fail on `1.0.0`, so either the app moves to 0.3.0 with them or the test's list excludes it with a written reason.
- [ ] A canon PR (sub-doctrine "the code stays pre-1.0 until the operator says otherwise", filed under the Twelve in `src/vibey_tools/gh/docs/doctrines.md`) and an ADR record the rule; the operator merges the canon PR.

### Final: whole-branch review on the most capable model, then push (10 to 12 minutes, foreground, log to a file), open the PR with Review Focus 5 and the three open points stated plainly, and wait for the operator.
