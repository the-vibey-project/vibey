## Title
feat(config): [engines.vscode_paid] names the paid provider and model VS Code runs on

ADR-0046 lane L20c (slug `loops-vscode-paid-config`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:277`): "**`vscode-paid`** (PAID, so paidloop). It is
declared-only, and needs `[engines.vscode_paid] provider` and `model`." Sub-doctrine 8.b keeps
paid adapters declared-only, and 12.c says every tunable is a key: the paid provider and the
model are the operator's decision, never a default vibey picks. Lane `loops-vscode-engine-ids`
added the engine ids; this lane lets a project declare them, and refuses a paid declaration
that does not say what it pays for.

At integration `d3b4a388`, `KNOWN_ENGINES` (`src/vibey/domain/config.py:25-33`) does not know
either id, and `EnginesConfig` (`:110-114`) has one engine sub-table, `claudeloop_local`,
parsed by `ClaudeloopLocalConfig.from_table` (`:88-107`) from `_parse_engines` (`:403-422`).
This lane copies that pattern.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. `KNOWN_ENGINES` gains `"vscode"` and `"vscode-paid"`, after `"claudeloop-local"`.
2. New frozen, slotted dataclass in `src/vibey/domain/config.py`, placed right after
   `ClaudeloopLocalConfig`:
   ```python
   @dataclass(frozen=True, slots=True)
   class VscodePaidConfig:
       """`[engines.vscode_paid]`: the paid provider and model the vscode-paid adapter runs
       (ADR-0046 §8). Both are the operator's to name; vibey never picks a paid provider."""

       provider: str = ""
       model: str = ""

       @classmethod
       def from_table(cls, table: dict[str, Any], path: str) -> "VscodePaidConfig":
           provider = _optional(table, "provider", f"{path}.provider", str, "")
           model = _optional(table, "model", f"{path}.model", str, "")
           return cls(provider=provider.strip(), model=model.strip())

       @property
       def complete(self) -> bool:
           return bool(self.provider) and bool(self.model)
   ```
3. `EnginesConfig` gains `vscode_paid: VscodePaidConfig = field(default_factory=VscodePaidConfig)`
   as its last field. `_parse_engines` reads
   `_optional(table, "vscode_paid", "engines.vscode_paid", dict, {})` and passes
   `vscode_paid=VscodePaidConfig.from_table(raw, "engines.vscode_paid")`. Every place that
   rebuilds `EnginesConfig` (the default-pool rebuild in `parse_config`, `:691-695` at
   `d3b4a388`, or its `dataclasses.replace` form after lane `rmq-r01-queue-config`) carries
   `vscode_paid` through; use `dataclasses.replace` if the rebuild still names fields one by one.
4. **The declaration check.** In `parse_config`, after the engine lists are known: when
   `"vscode-paid"` is in `engines.enabled` or in any `[phases.*].engines` list, and
   `engines.vscode_paid.complete` is False, raise
   `ConfigError("engines.vscode_paid.provider", "must be set when vscode-paid is declared (ADR-0046 §8)")`
   if `provider` is empty, else the same with `.model`. Declaring `vscode` needs nothing.
5. `src/vibey/domain/interfaces/config_interface.py` gains
   `@runtime_checkable class VscodePaidConfigInterface(Protocol)` with read-only properties
   `provider: str`, `model: str`, `complete: bool`, copying `TelemetryConfigInterface`'s layout (`:31-36`).

## Where to change
- `src/vibey/domain/config.py` (edit_file only: the file is over 700 lines).
- `src/vibey/domain/interfaces/config_interface.py`.
- New: `tests/domain/test_vscode_paid_config.py` (provenance line 1 copied from `tests/domain/test_config.py`).

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}, "engines": {"enabled": ["vscode-paid"], "vscode_paid": {"provider": "anthropic", "model": "m"}}})` succeeds, and `engines.vscode_paid.provider == "anthropic"`.
- [ ] Declaring `vscode-paid` with no table raises `ConfigError` whose `path` is `engines.vscode_paid.provider`; with a provider and no model, `engines.vscode_paid.model`.
- [ ] Declaring it only under `[phases.build] engines` is checked the same way.
- [ ] `vscode` declares with no table.
- [ ] `isinstance(config.engines.vscode_paid, VscodePaidConfigInterface)`.
- [ ] Every existing test in `tests/domain/test_config.py` passes unedited.
- [ ] 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_vscode_paid_config.py`:
- `test_vscode_paid_declared_with_provider_and_model_parses`
- `test_vscode_paid_without_a_provider_names_the_provider_key`
- `test_vscode_paid_without_a_model_names_the_model_key`
- `test_vscode_paid_named_in_a_phase_is_checked_too`
- `test_vscode_declares_without_a_table`
- `test_vscode_paid_values_are_stripped_and_satisfy_the_interface`
- `test_default_pool_rebuild_keeps_the_vscode_paid_table` (no `enabled` key, a
  `[engines.vscode_paid]` table present → it survives the rebuild).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_vscode_paid_config.py tests/domain/test_config.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Passing the provider and model to the runner (`loops-vscode-vibey-wiring`), and the runner's
  own paid mode (`loops-vscodeloop-doctor`).
- A "paid IDE declared without a name resolves to vscode-paid" key (gap B2); not in ADR-0046's set.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscode-engine-ids`, `loops-config-engine-names`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
