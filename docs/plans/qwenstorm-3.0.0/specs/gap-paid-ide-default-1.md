## Title
feat(config): a paid IDE declared without a name resolves to `vscode-paid`, 8.b's paid-default IDE

## Why
Sub-doctrine 8.b's paid defaults (`src/vibey_tools/gh/docs/doctrines.md:188-194`): "Where a
human declares a paid counterparty without naming which, the default is fixed ... **VS Code**
is the default IDE for paid loops". ADR-0046 §8 (`specs/ADR-two-loops.md`) adds the adapter,
`vscode-paid`, declared-only (lane `loops-vscode-paid`), and §1 gives the pattern for an
unnamed declaration: writing `paidloop` declares paidloop with its default adapter,
`claudeloop`. Nothing lets a human declare "a paid IDE" without naming the product: the engine
vocabulary is a closed list of product ids (`src/vibey/domain/config.py:25-33`,
`KNOWN_ENGINES`), checked at `:410-412` for `[engines].enabled` and never resolved for
`[phases.*].engines` (`:429-430`).

This lane adds the unnamed declaration `paid-ide` and resolves it, in the pure domain, to the
catalogue's paid-default IDE from lane `gap-paid-defaults` (`src/vibey/domain/paid_defaults.py`),
never to a restated literal (12.c, `doctrines.md:455`). The resolution is recorded on the
parsed config, so the command line can say it aloud (8.b: a paid declaration is made aloud;
lane `gap-paid-ide-default-2`).

## Required behaviour
1. New `src/vibey/domain/paid_ide.py` (provenance line 1, copied from
   `src/vibey/domain/config.py:1`), pure (no I/O, async, clock or network):
   - `PAID_IDE_TOKEN: Final = "paid-ide"`.
   - `class PaidIdeResolver` with
     `resolve(self, engines: Sequence[str]) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]`:
     returns the engine list with every `paid-ide` replaced by the catalogue's `ide` value, in
     order, keeping only the first occurrence of any id; and the declarations it resolved,
     `(("paid-ide", <ide>),)` when the token appeared, else `()`.
   - `PAID_IDE_RESOLVER: Final[PaidIdeResolverInterface] = PaidIdeResolver()`.
   - The IDE id comes from the catalogue instance `vibey.domain.paid_defaults` exports (lane
     `gap-paid-defaults`; its `ide` field is `"vscode-paid"`). Read that module for the
     instance's name; do not redefine the catalogue and do not write `"vscode-paid"` here.
2. New `src/vibey/domain/interfaces/paid_ide_interface.py` (provenance line 1) declares
   `@runtime_checkable class PaidIdeResolverInterface(Protocol)` with `resolve`, docstring only;
   export it from `src/vibey/domain/interfaces/__init__.py` if that module re-exports its siblings.
3. `src/vibey/domain/config.py`:
   - `EnginesConfig` (`:111-114`) gains
     `resolved: tuple[tuple[str, str], ...] = ()` (the unnamed declarations resolved while
     parsing, for the command line to announce).
   - `_parse_engines` (`:403-422`): immediately after `enabled` is read (`:405`) and before
     the always-on sovereign ids are appended, `enabled, resolved = PAID_IDE_RESOLVER.resolve(enabled)`.
     The `weights` table is resolved key by key the same way: a weight under `paid-ide` becomes
     the resolved id's weight; when both `paid-ide` and the resolved id carry a weight, raise
     `ConfigError("engines.weights", "paid-ide and vscode-paid both carry a weight")` (the id in
     the message is the catalogue's value). `EnginesConfig(..., resolved=resolved)`.
   - `_parse_phase` (`:425-432`): a non-None `engines` list is resolved the same way (its
     resolutions are not recorded; the engines table is where a declaration is announced).
   - Every existing check runs after resolution, so `paid-ide` is valid exactly when the
     catalogue's IDE is in `KNOWN_ENGINES` (added by `loops-vscode-paid`).
4. Nothing else changes: with no `paid-ide` anywhere, parsing is byte-for-byte today's.

## Where to change
- New `src/vibey/domain/paid_ide.py`, `src/vibey/domain/interfaces/paid_ide_interface.py`.
- `src/vibey/domain/config.py` (edit_file only; 700+ lines).
- New `tests/domain/test_paid_ide.py`.

## Acceptance criteria
- [ ] `grep -n 'vscode-paid' src/vibey/domain/paid_ide.py` prints nothing (the id comes from
      the catalogue; `KNOWN_ENGINES` may name it, and that is `loops-vscode-paid`'s line).
- [ ] `tests/domain/test_domain_purity.py` passes; `uv run lint-imports` passes.
- [ ] Every existing test in `tests/domain/test_config.py` passes unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_paid_ide.py`:
- `test_paid_ide_resolves_to_the_catalogue_ide` -- `resolve(["claudeloop", "paid-ide"])` is `(("claudeloop", <catalogue ide>), (("paid-ide", <catalogue ide>),))`, the ide read from the catalogue in the test too.
- `test_a_named_ide_and_the_token_collapse_to_one` -- `["vscode-paid", "paid-ide"]` gives one `vscode-paid`, order kept.
- `test_without_the_token_nothing_is_resolved` -- a list without `paid-ide` comes back unchanged with `()`.
- `test_engines_table_records_the_resolution` -- `parse_toml_string` of a minimal config with `[engines] enabled = ["paid-ide"]` gives `engines.resolved == (("paid-ide", <ide>),)` and the ide in `engines.enabled`.
- `test_a_weight_under_the_token_moves_to_the_ide` -- `[engines.weights] paid-ide = 3`.
- `test_both_weights_are_refused` -- the stated `ConfigError`.
- `test_phase_engines_resolve_too` -- `[phases.build] engines = ["paid-ide"]`.
- `test_resolver_satisfies_its_interface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- `--engines` on the command line and the announcement (`gap-paid-ide-default-2`).
- The `vscode-paid` descriptor, its `[engines.vscode_paid]` table and its runner
  (`loops-vscode-paid`); the `paidloop` token (ADR-0046 lanes).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(config): a paid IDE declared without a name resolves to vscode-paid`. Do not push.

## Lane card
- **Depends on:** `gap-paid-defaults` (the catalogue), `loops-vscode-paid` (`vscode-paid` in
  `KNOWN_ENGINES` and `EngineId`).
- **Must keep passing unchanged:** `tests/domain/test_config.py`, `tests/domain/test_domain_purity.py`,
  every protected test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
