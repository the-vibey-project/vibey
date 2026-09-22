## Title
feat(cli): --provider sovereignloop is the sovereign DESIGN/DECOMPOSE provider, and --provider qwenloop is its legacy spelling

ADR-0046 lane L18f (slug `loops-cli-provider-name`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`): `--provider qwenloop` becomes
`--provider sovereignloop`, the old spelling "accepted with a warning", through all of 3.x.
Sub-doctrine 8.b makes `sovereignloop` the default for every phase
(`src/vibey_tools/gh/docs/doctrines.md:128-131`), and 12.c (`:455`) forbids dropping the old
spelling silently.

At integration `d3b4a388`, in `src/vibey/cli/main.py`:
- `_OLLAMA_MODEL_HELP` (`:361-364`) says "for --provider qwenloop";
- `_PROVIDERS = ("scripted", "claudeloop", "qwenloop", "opencode")` (`:365`) and
  `_UNKNOWN_PROVIDER` (`:367-371`) is built from it;
- `_PROVIDER_HELP` (`:373-377`) names qwenloop and "the sovereign pair";
- `_resolve_provider` (`:380-389`) returns `"qwenloop"` when no `--provider` is given;
- `_work_once` branches on `provider == "qwenloop"` (`:441`), `worker` on the same (`:1593`),
  and `worker` refuses a provider outside `_PROVIDERS` before any I/O (`:1478-1480`).

And `src/vibey/infrastructure/cluster_preflight.py:53-58` `PROVIDER_ENGINES` (the keys are the
worker's accepted `--provider` values; `vibey doctor --cluster --provider ...` and the chart's
`worker.provider` go through it) has `"qwenloop": None` and no `"sovereignloop"`.

Lane `loops-engine-id-sovereignloop` (L06) made `EngineId("qwenloop")` resolve to
`sovereignloop`, so `--engines qwenloop` already works; `--provider` is a separate vocabulary.

## Required behaviour
1. `_PROVIDERS = ("scripted", "claudeloop", "sovereignloop", "opencode")`, so
   `_UNKNOWN_PROVIDER == "provider must be 'scripted', 'claudeloop', 'sovereignloop', or 'opencode'"`.
2. `_LEGACY_PROVIDERS: Mapping[str, str] = MappingProxyType({"qwenloop": "sovereignloop"})`,
   with a comment: legacy `--provider` spellings, accepted with a warning through 3.x
   (ADR-0046 Migration table).
3. `_resolve_provider(explicit)`:
   - `None` → `"sovereignloop"`;
   - a key of `_LEGACY_PROVIDERS` → prints to **stderr**
     `--provider qwenloop is a legacy spelling; use --provider sovereignloop (accepted through 3.x)`
     (built as `f"--provider {explicit} is a legacy spelling; use --provider {current} (accepted through 3.x)"`)
     and returns the current name;
   - anything else → returned unchanged (the callers still refuse an unknown one).
   Its docstring says so, and keeps the reason it is module-level.
4. Both `provider == "qwenloop"` branches (in `_work_once` and in `worker`) test
   `provider == "sovereignloop"`; what they build is unchanged.
5. `worker`'s early check accepts a legacy spelling: `provider_opt not in _PROVIDERS and
   provider_opt not in _LEGACY_PROVIDERS` → the unknown-provider message and exit 2, as today.
6. Help texts:
   - `_OLLAMA_MODEL_HELP`: `"Local model for --provider sovereignloop; ignored by the other providers. Default: "`
     (the rest unchanged);
   - `_PROVIDER_HELP`:
     ```python
     _PROVIDER_HELP = (
         "DESIGN/DECOMPOSE provider: scripted, claudeloop, sovereignloop (the sovereign one, on "
         "Ollama), or opencode. Default: sovereignloop -- the sovereign loop is always on "
         "(sub-doctrine 8.b). An explicit value always wins; qwenloop is accepted as a legacy "
         "spelling of sovereignloop through 3.x."
     )
     ```
7. `PROVIDER_ENGINES` gains `"sovereignloop": None` directly before `"qwenloop": None`, which
   stays (the chart's `worker.provider=qwenloop` keeps validating through 3.x). Its comment's
   "the qwenloop provider" becomes "the sovereignloop provider (spelled qwenloop before ADR-0046)".
8. Nothing else changes: `--provider claudeloop`, `scripted` and `opencode` behave as today, and
   the provider still talks to Ollama over HTTP (`QwenloopDesignProvider`), not to the binary.

## Where to change
- `src/vibey/cli/main.py` (1761 lines: `edit_file` only; `installer-doctor` and other lanes edit
  other parts of it, so anchor by text):
  - imports (neither is imported at `d3b4a388`): `from collections.abc import Mapping` between
    `import subprocess  # nosec ...` and `from datetime import UTC, datetime`, and
    `from types import MappingProxyType` between `from pathlib import Path` and
    `from typing import Annotated, cast` (the stdlib block at `:11-19`; keep the SIGTERM latch
    import at `:7` first, where it is);
  - the block from `_OLLAMA_MODEL_HELP = (` through the end of `_resolve_provider` (`:360-389`).
    Reference for the function:
    ```python
    def _resolve_provider(explicit: str | None) -> str:
        """The provider to run: the operator's explicit choice, else the sovereign default.

        Sub-doctrine 8.b keeps sovereignloop always on, never needing declaration, so with no
        `--provider` DESIGN and DECOMPOSE run on it (#322). A legacy spelling
        (`_LEGACY_PROVIDERS`) is accepted with one line on stderr and resolved to its current
        name (ADR-0046 Migration table, through 3.x). Paid (`claudeloop`) and `opencode` are
        always a stated choice. Module-level, like the typer commands that share it, so `work`
        and `worker` cannot disagree.
        """
        if explicit is None:
            return "sovereignloop"
        current = _LEGACY_PROVIDERS.get(explicit)
        if current is None:
            return explicit
        typer.echo(
            f"--provider {explicit} is a legacy spelling; use --provider {current} "
            "(accepted through 3.x)",
            err=True,
        )
        return current
    ```
  - `provider == "qwenloop":` occurs twice (`:441`, `:1593`); replace both with a checked
    replacement asserting `s.count('provider == "qwenloop":') == 2`;
  - `    if provider_opt is not None and provider_opt not in _PROVIDERS:\n` (`:1478`) becomes
    `    if (\n        provider_opt is not None\n        and provider_opt not in _PROVIDERS\n        and provider_opt not in _LEGACY_PROVIDERS\n    ):\n`.
- `src/vibey/infrastructure/cluster_preflight.py` (over 100 lines: `edit_file`): the
  `PROVIDER_ENGINES` entry and its comment (`:48-58`).
- Existing expectations that change, all pure text (`"qwenloop"` → `"sovereignloop"` inside the
  unknown-provider message): `tests/cli/test_sovereign_provider_options.py` `:472-474` (the
  `_UNKNOWN_PROVIDER == (...)` literal) and `:484`, and `tests/cli/test_operational_commands.py`
  `:1429`. Use one checked script:
  one checked replacement, as a single `shell` command (the message text carries apostrophes,
  so the argument is double-quoted and its inner double quotes are escaped):
  ```
  python3 -c "from pathlib import Path; old = \"'scripted', 'claudeloop', 'qwenloop', or 'opencode'\"; new = old.replace(\"qwenloop\", \"sovereignloop\"); pairs = ((\"tests/cli/test_sovereign_provider_options.py\", 2), (\"tests/cli/test_operational_commands.py\", 1)); texts = {n: Path(n).read_text(encoding=\"utf-8\") for n, _ in pairs}; assert all(texts[n].count(old) == c for n, c in pairs), {n: texts[n].count(old) for n, _ in pairs}; [Path(n).write_text(texts[n].replace(old, new), encoding=\"utf-8\") for n, _ in pairs]; print(\"ok\")"
  ```
  The tests that run `--provider qwenloop` stay unedited: they now prove the legacy spelling.
- **Stop rule.** Any other failing test (for example one that asserts the exact output of a
  `--provider qwenloop` run and now also sees the stderr line): stop and report it.

## Acceptance criteria
- [ ] `_resolve_provider(None) == "sovereignloop"`; `_resolve_provider("qwenloop") == "sovereignloop"` with the exact stderr line; `_resolve_provider("claudeloop") == "claudeloop"` with no output.
- [ ] `vibey worker --provider qwenloop --azure bogus` exits 2 with `--azure must be 'memory' or 'az'` (the provider passed its check, before any database I/O); `vibey worker --provider bogus` exits 2 with the new unknown-provider message.
- [ ] `EngineAuthCheck(which=..., provider="sovereignloop")` and `provider="qwenloop"` both construct.
- [ ] `git grep -n '"qwenloop"' -- src/vibey/cli/main.py` prints only the `_LEGACY_PROVIDERS` entry.
- [ ] 100% branch coverage of `src/vibey/cli/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/cli/test_provider_name.py` (none of these tests touches a database or reaches `build_app`):
- `test_the_providers_name_sovereignloop`: `_PROVIDERS` and `_UNKNOWN_PROVIDER` as in behaviour 1.
- `test_the_default_provider_is_sovereignloop`.
- `test_the_legacy_provider_is_resolved_with_a_warning` (`capsys`: `err` is exactly the message plus a newline; `out` is empty).
- `test_an_explicit_provider_is_kept_silently` (`claudeloop`, `scripted`, `opencode`).
- `test_the_worker_accepts_the_legacy_spelling`: `CliRunner().invoke(app, ["worker", "--provider", "qwenloop", "--azure", "bogus"])` → exit 2, `"--azure must be" in res.output`, `"provider must be" not in res.output`.
- `test_the_worker_still_refuses_an_unknown_provider`.
- `test_the_help_texts_name_sovereignloop`: `"--provider sovereignloop" in _OLLAMA_MODEL_HELP`; `"sovereignloop" in _PROVIDER_HELP` and `"legacy" in _PROVIDER_HELP`.
- `test_cluster_preflight_accepts_both_spellings`: `PROVIDER_ENGINES["sovereignloop"] is None`, `PROVIDER_ENGINES["qwenloop"] is None`, and `EngineAuthCheck(which=lambda _name: None, provider="sovereignloop").check({})` reports nothing required for that provider (compare with the existing `test_the_qwenloop_provider_requires_no_engine` in `tests/infrastructure/test_cluster_preflight.py:223-227`).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_provider_name.py tests/cli/test_sovereign_provider_options.py tests/cli/test_operational_commands.py tests/infrastructure/test_cluster_preflight.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

The CLI suites and the full `--cov` run need PostgreSQL until lane `fakes-harness-decouple`
lands; `tests/cli/test_provider_name.py` itself needs none.

## Out of scope
- `--provider opencode` (retired by lane `loops-retire-opencode-refusals`, L38a).
- The chart's `worker.provider` default and golden (lane `loops-chart-sovereignloop-names`).
- Renaming `QwenloopDesignProvider` / `QwenloopWorkPlanProducer` (Python names; not in the Migration table).
- The four `AsyncSubprocessExecutor()` sites (lane `loops-invocation-cli`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-engine-id-sovereignloop`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
