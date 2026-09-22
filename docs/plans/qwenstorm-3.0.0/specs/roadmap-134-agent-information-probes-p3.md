## Title
feat(preflight): an information probe reads whether the current cycle's specification and the declared secrets are at hand

## Why
Issue #134, "Proposed child issues" 5, and Scope 1 "information: required inputs present and
fresh (spec, docs, credential validity through the secrets surface)" (rewrite
`issue-audit/updates/134.md`). vibey-gh's own vocabulary says what measures this coordinate:
information availability is "required inputs at hand: specification, docs, credentials"
(`src/vibey_tools/gh/vibey_gh/feasibility.py:110`). The default path needs it at
`interview`, `feature-branch`, `develop-validation` and `main-validation` (`:262-320`). Today
the conductor bridge never measures it, so it is `unknown` on every run.

Sub-doctrines:
- 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): measure it.
- 10.f (`:419`): what cannot be read stays `unknown` with its reason.
- 9.b (`:349`): the probe is a class with its interface beside it, reading only declared ports.

The inputs exist behind ports:
- the project's phase and cycle: `ProjectStore.get`, `src/vibey/application/interfaces/projects.py:18-19`;
- the accepted specification of a cycle: `DesignSpecRepository.load`,
  `src/vibey/application/interfaces/design.py:61-66`. The file repository returns `None` when
  the cycle has none (`src/vibey/infrastructure/db/design_spec_repository.py:36-39`);
- credentials: `SecretsPort.get_secret`, `src/vibey/application/interfaces/secrets.py:8-13`.
  A missing key raises `KeyError`, in `infrastructure/secrets/in_memory.py:15-18` and in
  `openbao.py:48-50`. OpenBao raises `RuntimeError` when it cannot answer (`openbao.py:51`,
  `:54-55`), and urllib raises `OSError`.

"Validity" here is presence in the secrets manager: the port can show a key is held, not that
a service still honours it. Whether a grant is honoured is agency, the vibey-gh agency probe's
(`roadmap-134-agency-probe`).

DESIGN writes the specification, so before BUILD its absence is not a shortfall. The probe
reports `unknown` there rather than blocking a run at `interview` for an input that phase
produces.

## Required behaviour
New `src/vibey/application/information_probe.py`:
1. `SPEC_PHASES: Final[frozenset[Phase]] = frozenset({Phase.BUILD, Phase.REVIEW, Phase.DEPLOY_DESIGN, Phase.DEPLOY_EXECUTE, Phase.DEPLOY_REVIEW, Phase.DEPLOY})`,
   with a docstring: the phases that consume an accepted specification
   (`src/vibey/domain/phase.py:17-28`). It is a constructor argument so an adopter's pipeline
   can differ (12.c).
2. `class InformationProbe` (implements `FeasibilityProbeInterface`, lane `-p2`):
   - `__init__(self, *, projects: ProjectStore, specs: DesignSpecRepository, secrets: SecretsPort, required_secrets: Sequence[str] = (), spec_phases: frozenset[Phase] = SPEC_PHASES) -> None`,
     stored as `self._projects`, `self._specs`, `self._secrets`,
     `self._required = tuple(required_secrets)` and `self._spec_phases`.
   - `async def read(self, project_id: UUID) -> tuple[CoordinateReading, ...]`: returns
     exactly one reading, `(await self._availability(project_id),)`.
   - `async def _availability(self, project_id: UUID) -> CoordinateReading`. Every reading is
     `CoordinateReading("information", "availability", value, source)`. The first rule that
     applies decides, in this order:
     1. `project = await self._projects.get(project_id)` is `None`: value `None`, source
        `f"unmeasured — project {project_id} is not in the project store"`.
     2. `project.phase not in self._spec_phases`: value `None`, source
        `f"unmeasured — DESIGN writes the specification; project {project.name} is in {project.phase.value}, so its inputs are measured from BUILD on"`.
     3. `await self._specs.load(project_id, project.cycle)` is `None`: value `0.0`, source
        `f"Run DESIGN for cycle {project.cycle}: no accepted specification is stored for it."`.
     4. Try `await self._secrets.get_secret(key)` for each key of `self._required`, in
        order. `KeyError` collects the key as missing. `(RuntimeError, OSError)` as `exc`
        collects `f"{key} ({exc})"` as unreadable. Never put a secret's value into a source
        (SD-01 §1; 7.c's floor).
     5. Any missing: value `0.0`, source
        `f"Store the missing secret(s) in the secrets manager: {', '.join(missing)}."`.
     6. Otherwise any unreadable: value `None`, source
        `f"unmeasured — the secrets manager could not be read for: {'; '.join(unreadable)}"`.
     7. Otherwise: value `1.0`, source
        `f"cycle {project.cycle}'s specification is stored; {declared}"`. `declared` is
        `f"{len(self._required)} required secret(s) present"`, or, when none are declared,
        `"no required secrets declared ([secrets] required)"`.

     A missing secret outranks an unreadable one: one measured shortfall decides, as
     vibey-gh's Kleene AND does (`feasibility.py:496-502`).
3. `src/vibey/application/interfaces/information_probe_interface.py`:
   `@runtime_checkable class InformationProbeInterface(FeasibilityProbeInterface, Protocol)`,
   with the docstring "The conductor's information probe (#134): whether the inputs the
   project's current phase needs are at hand." Copy the shape of
   `src/vibey/application/interfaces/budget_source_interface.py:19-20`: a Protocol that extends
   the port it mirrors and adds nothing.
4. `tests/fakes/registry.py` (lane `fakes-registry`): `EXEMPT` gains
   `InformationProbeInterface: ExemptReason.CLASS_CONTRACT`. The port it mirrors,
   `FeasibilityProbeInterface`, already has its fake (`-p2`).

## Where to change
- New `src/vibey/application/information_probe.py` and
  `src/vibey/application/interfaces/information_probe_interface.py`. Line 1 of each is the
  provenance header, copied byte-for-byte from `src/vibey/application/preflight.py:1`.
- `tests/fakes/registry.py` (one entry).
- New `tests/application/test_information_probe.py`, using the registered fakes:
  - `InMemoryProjectRepository` (`tests/fakes/projects.py`, lane `fakes-projects`). Move a
    project INTAKE → DESIGN → BUILD with `transition(project_id, expected=…, to=…)`.
  - `InMemoryDesignSpecRepository` (`tests/fakes/design.py`, lane `fakes-design`).
  - `InMemorySecrets` (`src/vibey/infrastructure/secrets/in_memory.py`).
  - For the unreadable case only, a test-local `_UnreachableSecrets(SecretsPort)` whose two
    methods raise `RuntimeError("OpenBao API error 503: Service Unavailable")`. It is
    substituted through the constructor, with no patching.
- The spec used is
  `DesignSpec(objective="greet", constraints=(), non_goals=(), criteria=(), nfrs=(), walking_skeleton="hello")`
  (`src/vibey/domain/spec.py:40-46`).
- No production wiring here (`-p4`).

## Acceptance criteria
- [ ] BUILD with the cycle's spec stored and no declared secrets reads `1.0`.
- [ ] BUILD without the cycle's spec reads `0.0`, and the source starts `Run DESIGN for cycle 1`.
- [ ] A declared secret absent from the manager reads `0.0`, and the source names it. An
      unreadable manager reads `None`, and the source says `could not be read`.
- [ ] DESIGN, or an unknown project, reads `None` with its named reason.
- [ ] No reading's source contains a secret's value.
- [ ] `tests/fakes/test_port_parity.py` passes, and 100% branch coverage of `src/vibey/application/`.

## Tests to write first (TDD)
`tests/application/test_information_probe.py` (default tier):
- `test_a_stored_spec_with_no_declared_secrets_is_at_hand`: the reading is
  `("information", "availability", 1.0)`, and the source contains `no required secrets declared`.
- `test_a_missing_spec_is_a_measured_shortfall`.
- `test_a_missing_required_secret_is_a_measured_shortfall`: required
  `("forge-token", "openbao-root")`, with only `forge-token` set to `"s3cret-value"`. The value
  is `0.0`, the source names `openbao-root`, and `"s3cret-value" not in source`.
- `test_every_required_secret_present_is_at_hand`: both set. The value is `1.0`, and the source
  contains `2 required secret(s) present`.
- `test_an_unreadable_secrets_manager_leaves_it_unknown`: `_UnreachableSecrets`, required
  `("forge-token",)`. The value is `None`, and the source contains `could not be read` and
  `forge-token`.
- `test_before_build_the_spec_is_not_yet_due`: the project is in DESIGN with no spec. The
  value is `None`, and the source contains `measured from BUILD on`.
- `test_an_unknown_project_is_unmeasured`: `uuid4()`. The value is `None`, and the source
  contains `is not in the project store`.
- `test_the_spec_phases_are_a_constructor_argument`: `spec_phases=frozenset({Phase.DESIGN})`,
  with the project in DESIGN and the spec stored. The value is `1.0`.
- `test_one_reading_per_read`: `len(await probe.read(pid)) == 1`.
- `test_the_probe_satisfies_its_ports`: `isinstance(probe, InformationProbeInterface)` and
  `isinstance(probe, FeasibilityProbeInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_information_probe.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/application tests/fakes
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The `[secrets] required` key and wiring the probe into `build_app` (`-p4`).
- Checking that a credential still works against its service (agency; `roadmap-134-agency-probe`).
- Information stability and reliability (staleness series, truth of the inputs).
- Docs freshness, and writing readings to the ledger (the gaps.md §D1 measure lanes).
- CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
