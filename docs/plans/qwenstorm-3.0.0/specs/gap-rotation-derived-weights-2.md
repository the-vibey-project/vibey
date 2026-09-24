## Title
feat(config): `[engines.evidence]` declares the band within which measured evidence may move rotation weights

## Why
`gap-rotation-derived-weights-1` added the pure rule `EvidenceWeighting` and its band
`EvidenceBand(floor=0.5, ceiling=1.5, min_samples=20, success_share=0.5)`. 12.c
(`src/vibey_tools/gh/docs/doctrines.md:455`) says a value that could be a key is "a decision
taken away from the next adopter". So the band, and the window of runs it reads, are declared in
`vibey.toml`, each with an environment override. 8.g (`:316-324`) requires derivation "from live
evidence"; the band bounds how far evidence may move a weight.

## Required behaviour
1. `src/vibey/domain/config.py` gains
   `@dataclass(frozen=True, slots=True) class EvidenceConfig`:
   - `enabled: bool = True`;
   - `floor: float = 0.5`, `ceiling: float = 1.5`;
   - `min_samples: int = 20`;
   - `success_share: float = 0.5`;
   - `window: int = 50`, the most recent measured runs per engine that are read.

   `__post_init__` applies `EvidenceBand`'s rules plus `1 <= window <= 1000`, raising
   `ConfigError("engines.evidence.<field>", ...)`. The method `band(self) -> EvidenceBand`
   builds the pure band. A `from_table(cls, table, path)` classmethod follows
   `ClaudeloopLocalConfig.from_table`'s pattern (`config.py:70-`).
2. `EnginesConfig` (`:111-114`) gains `evidence: EvidenceConfig = field(default_factory=EvidenceConfig)`.
   `_parse_engines` (`:403-422`) reads `[engines.evidence]`, the same way it reads
   `claudeloop_local` at `:416-421`.
3. Environment overrides are applied where the config loader applies other `VIBEY_*`
   overrides (`src/vibey/infrastructure/config_loader.py`; follow the existing pattern):
   `VIBEY_ENGINES_EVIDENCE_ENABLED`, `…_FLOOR`, `…_CEILING`, `…_MIN_SAMPLES`,
   `…_SUCCESS_SHARE`, `…_WINDOW`. The environment beats the file, and the file beats the default.
4. `engines-pool` (#321) rewrites `_parse_engines`. Apply this lane on top of its version.

## Where to change
- `src/vibey/domain/config.py` (edit_file).
- `src/vibey/infrastructure/config_loader.py` (edit_file, the overrides).
- Tests: append to `tests/domain/test_config.py`, and to the config-loader test file
  (`grep -rln "config_loader" tests/infrastructure`).

## Acceptance criteria
- [ ] No table gives `EvidenceConfig()`, and `.band() == EvidenceBand()`.
- [ ] `[engines.evidence] floor = 0.8` gives `band().floor == 0.8`. `floor = 1.2` raises
      `ConfigError` naming `engines.evidence.floor`.
- [ ] `VIBEY_ENGINES_EVIDENCE_WINDOW=10` beats a file's `window = 50`.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
- `tests/domain/test_config.py`: `test_engines_evidence_defaults`, `test_engines_evidence_parses_and_validates` (parametrized).
- Config-loader tests: `test_engines_evidence_environment_overrides`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading measurements (`-3`), applying factors (`-4`), and docs.

Commit as `feat(config): declare the rotation evidence band`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
