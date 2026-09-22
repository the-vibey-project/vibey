## Title
feat(domain): one pure catalogue of 8.b's four paid defaults, and the rule that an unnamed paid declaration reaches them

## Why
Sub-doctrine 8.b's *Paid defaults* paragraph (`src/vibey_tools/gh/docs/doctrines.md:188-194` at
integration HEAD `d3b4a388`) fixes, "always, no exceptions", which paid counterparty a human
reaches when they declare one without naming which: **Claude** (paidloop's default model,
through `claudeloop`), **VS Code** (the default IDE for paid loops, adapter `vscode-paid`,
`specs/ADR-two-loops.md:277`), **AWS** (the default paid cloud) and **GitHub** (the default paid
forge). The same paragraph says a default among paid options never makes paid a default over
sovereign (8.a, `doctrines.md:99-118`).

Gap C2 (`issue-audit/gaps.md:189-200`) found that nothing in the code carries these four values
and nothing resolves "declared paid, unnamed" anywhere: `DeployConfig.target` accepts only
concrete targets (`src/vibey/domain/config.py:137-140`, `:453-459`) and vibey-gh's
`PlatformConfig.kind` accepts only concrete forges (`src/vibey_tools/gh/vibey_gh/config.py:288-296`).
This lane adds the one catalogue every consumer reads, so the four values live in exactly one
place in vibey (10.e, `doctrines.md:417`) and are declared data, not constants buried in the
lanes that use them (12.c, `doctrines.md:455`). It is pure domain: no I/O, no clock.

Consumers (other lanes, not this one): `gap-deploy-target-paid` (cloud), `gap-gh-platform-paid`
(forge, through its own copy that `gap-paid-defaults-agree` holds equal), ADR-0046 §1's paidloop
lane (engine — it reads `default_for(PaidSurface.ENGINE).adapter == "claudeloop"`; this lane does
not decide the engines' declaration word, which ADR-0046 makes `paidloop`), and
`gap-paid-ide-default` (IDE, gap B2).

## Required behaviour
1. New module `src/vibey/domain/paid_defaults.py` declares:
   - `PAID_DECLARATION: Final = "paid"` — the one word that declares a paid counterparty without
     naming it. Comparison is exact (case-sensitive, no stripping).
   - `class PaidSurface(StrEnum)` with members `ENGINE = "engine"`, `IDE = "ide"`,
     `CLOUD = "cloud"`, `FORGE = "forge"`, in that order.
   - `@dataclass(frozen=True, slots=True) class PaidDefault` with fields `surface: PaidSurface`,
     `product: str`, `adapter: str`, `role: str`, and one method
     `explain(self, declared: str) -> str` returning exactly
     `f"{self.adapter} (declared {declared!r}: {self.product} is {self.role}, sub-doctrine 8.b)"`.
   - `class PaidDefaults` (the catalogue), with
     `__init__(self, defaults: Sequence[PaidDefault] = DEFAULT_PAID_DEFAULTS, *, declaration: str = PAID_DECLARATION)`.
     The constructor raises `ValueError("paid defaults must name every surface exactly once: missing <names>")`
     when a surface is absent (names comma-joined in `PaidSurface` order), and
     `ValueError("paid defaults must name every surface exactly once: <name> twice")` for the first
     duplicate. Members:
     - property `declaration -> str`;
     - property `surfaces -> tuple[PaidSurface, ...]` (in `PaidSurface` order);
     - `default_for(self, surface: PaidSurface) -> PaidDefault`;
     - `is_declaration(self, value: str) -> bool` — `value == self.declaration`;
     - `resolve(self, surface: PaidSurface, declared: str) -> str` — the surface's default
       `adapter` when `is_declaration(declared)`, otherwise `declared` unchanged.
   - `DEFAULT_PAID_DEFAULTS: Final[tuple[PaidDefault, ...]]`, exactly:

     | surface | product | adapter | role |
     |---|---|---|---|
     | ENGINE | `Claude` | `claudeloop` | `paidloop's default model, through claudeloop` |
     | IDE | `VS Code` | `vscode-paid` | `the default IDE for paid loops` |
     | CLOUD | `AWS` | `aws` | `the default paid cloud` |
     | FORGE | `GitHub` | `github` | `the default paid forge` |

   - `PAID_DEFAULTS: Final[PaidDefaultsInterface] = PaidDefaults()`.

   Declare them top to bottom in this order: `PAID_DECLARATION`, `PaidSurface`, `PaidDefault`,
   `DEFAULT_PAID_DEFAULTS`, `PaidDefaults`, `PAID_DEFAULTS` (the constructor default names
   `DEFAULT_PAID_DEFAULTS`, so it must already exist).
2. The module docstring quotes 8.b's sentence ("Where a human declares a paid counterparty without
   naming which, the default is fixed"), says the catalogue is consulted only after a human has
   written a paid declaration (a paid default is never a default over sovereign, 8.a), and says
   vibey-gh keeps its own copy of the forge value because it cannot import vibey
   (`gap-paid-defaults-agree` holds the two equal).
3. New interface file `src/vibey/domain/interfaces/paid_defaults_interface.py` declares
   `PaidDefaultInterface` (read-only properties `surface`, `product`, `adapter`, `role`, method
   `explain`) and `PaidDefaultsInterface` (properties `declaration`, `surfaces`; methods
   `default_for`, `is_declaration`, `resolve`), both `@runtime_checkable Protocol`s. Type
   `PaidSurface` and `PaidDefault` under `if TYPE_CHECKING:` only, copying
   `src/vibey/domain/interfaces/ledger_record_interface.py:9-16`. `default_for` is declared as
   returning `PaidDefaultInterface`.
4. Both Protocols are exported from `src/vibey/domain/interfaces/__init__.py`.
5. `tests/domain/test_domain_purity.py` still passes: the module imports only `dataclasses`,
   `enum`, `typing`, `collections.abc` and its interface.

## Where to change
- New `src/vibey/domain/paid_defaults.py`. Line 1 is the provenance header copied byte-for-byte
  from line 1 of `src/vibey/domain/ledger_record.py`. Copy the `Final`-instance pattern of
  `ledger_record.py:157` (`LEDGER_RECORDS: Final[LedgerRecordCodecInterface] = LedgerRecordCodec()`).
- New `src/vibey/domain/interfaces/paid_defaults_interface.py` (same header).
- `src/vibey/domain/interfaces/__init__.py` (152 lines — `edit_file` only):
  - insert, immediately before the line `from vibey.domain.interfaces.phase_timing_interface import (`
    (line 36):
    ```python
    from vibey.domain.interfaces.paid_defaults_interface import (
        PaidDefaultInterface,
        PaidDefaultsInterface,
    )
    ```
  - in `__all__`, insert `"PaidDefaultInterface",` and `"PaidDefaultsInterface",` immediately
    before `"PhaseSpendInterface",` (line 125).
- New test file `tests/domain/test_paid_defaults.py`. No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_paid_defaults.py tests/domain/test_domain_purity.py` passes.
- [ ] `git diff --stat` names only the two new source files, `domain/interfaces/__init__.py` and the new test file.
- [ ] `src/vibey/domain/*` keeps 100% branch coverage.

## Tests to write first (TDD)
New `tests/domain/test_paid_defaults.py` (pure: no database, no network, no marker, no patching).
Import from `vibey.domain.paid_defaults` and `vibey.domain.interfaces`.
- `test_the_four_paid_defaults_are_8b_s` — parametrized over the table in behaviour 1:
  `PAID_DEFAULTS.default_for(surface)` has that `product`, `adapter` and `role`.
- `test_an_unnamed_paid_declaration_resolves_to_the_fixed_default` —
  `resolve(PaidSurface.CLOUD, "paid") == "aws"`, `resolve(PaidSurface.FORGE, "paid") == "github"`,
  `resolve(PaidSurface.ENGINE, "paid") == "claudeloop"`, `resolve(PaidSurface.IDE, "paid") == "vscode-paid"`.
- `test_a_named_value_is_never_rewritten` — parametrized over `"azure"`, `"openstack"`, `"gitlab"`,
  `"Paid"`, `" paid"` and `""`: `resolve(PaidSurface.CLOUD, value) == value`.
- `test_the_sovereign_defaults_pass_through_untouched` — `resolve(PaidSurface.CLOUD, "openstack") == "openstack"`
  and `resolve(PaidSurface.FORGE, "forgejo") == "forgejo"` (8.a: nothing sovereign is ever resolved away).
- `test_explain_names_the_declaration_and_the_rule` —
  `PAID_DEFAULTS.default_for(PaidSurface.CLOUD).explain("paid") == "aws (declared 'paid': AWS is the default paid cloud, sub-doctrine 8.b)"`.
- `test_a_catalogue_must_name_every_surface_once` — `PaidDefaults(DEFAULT_PAID_DEFAULTS[:3])`
  raises `ValueError` matching `missing forge`; `PaidDefaults(DEFAULT_PAID_DEFAULTS + DEFAULT_PAID_DEFAULTS[:1])`
  raises `ValueError` matching `engine twice`.
- `test_the_declaration_word_is_configurable` — `PaidDefaults(declaration="declared-paid").resolve(PaidSurface.CLOUD, "declared-paid") == "aws"`
  and `.is_declaration("paid") is False`.
- `test_surfaces_come_in_enum_order` — `PAID_DEFAULTS.surfaces == tuple(PaidSurface)`.
- `test_the_catalogue_satisfies_its_interfaces` — `isinstance(PAID_DEFAULTS, PaidDefaultsInterface)`
  and `isinstance(PAID_DEFAULTS.default_for(PaidSurface.CLOUD), PaidDefaultInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time. The new test file needs nothing outside the process and also runs
alone with `--noconftest -n 0`.

## Out of scope
- Reading the catalogue anywhere: `[deploy] target = "paid"` (`gap-deploy-target-paid`),
  `[platform] kind = "paid"` (`gap-gh-platform-paid`), paidloop's default adapter (ADR-0046 §1's
  lane) and the paid IDE (`gap-paid-ide-default`).
- Deciding any surface's declaration word other than `"paid"` (ADR-0046 makes the engines'
  word `paidloop`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).

Commit as `feat(domain): one pure catalogue of 8.b's four paid defaults`. Do not push.

## Lane card
- **Depends on:** nothing.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/domain/test_domain_purity.py`, `tests/domain/test_config.py`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
