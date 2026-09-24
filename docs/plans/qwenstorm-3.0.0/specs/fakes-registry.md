## Title
test(fakes): one registry says which fake stands in for every port, and a meta test fails when a port has none

## Why
The operator's standard is that the test harness "always needs to create comprehensive fakes for
all interfaces at all times". Sub-doctrine 9.b says substitution happens at the declared seam,
never by patching an import.

Today that is convention, and it has gaps:
- `tests/fakes/test_port_parity.py:25-30` checks 4 ports.
- `src/vibey/application/interfaces/` declares about 90 Protocols.
- The shared fakes are split between `tests/fakes/__init__.py` and `tests/application/fakes.py`.
- 155 private doubles are scattered over 56 files (`FakeLedger` is written 7 times).
- The root tests call `monkeypatch.setattr` about 50 times and `mock.patch` about 93 times,
  and use `MagicMock` about 146 times.

This lane makes the rule mechanical, with no fake written yet:
1. A registry maps each port to its fake, or to a reasoned exemption, or to the lane that
   owes it (`PENDING`).
2. A parity test checks structure and signatures, and refuses stubs.
3. A ratchet freezes today's patch counts, so they can only go down.

Draft amendment A2 in `specs/ADR-test-harness-fakes-amendment.md` describes this.

## Required behaviour
1. **Split the shared fakes.** Keep every existing name importable.
   - `tests/fakes/queue.py` gets `FakeJobRepository`, `FakeHumanGateRepository`, `make_job`
     and `_with`, moved verbatim from `tests/application/fakes.py:16-311`.
   - `tests/fakes/engines.py` gets `FakeEngineHealthRepository` and
     `FakeRotationCursorRepository`, moved verbatim from `tests/fakes/__init__.py:18-92`.
   - `tests/fakes/__init__.py` re-exports all six names.
   - `tests/application/fakes.py` becomes a shim:
     `from tests.fakes.queue import FakeHumanGateRepository, FakeJobRepository, make_job`,
     plus `__all__`. 36 test modules import from these two paths, and none of them changes.
2. **`tests/fakes/registry.py`** holds data only: no functions and no logic.
   - `class ExemptReason(StrEnum)` with the members:
     - `VALUE_CONTRACT`: the Protocol describes a record, not a service;
     - `CLASS_CONTRACT`: an ADR-0016 mirror of one concrete class that the tests use as it is;
     - `PURE_POLICY`: the real implementation does no I/O, so the tests use it.
   - `@dataclass(frozen=True) class FakeRegistration`, with:
     - `port: type`;
     - `build: Callable[[], object]`, a zero-argument factory returning a fresh fake;
     - `note: str = ""`.
   - `REGISTRY: tuple[FakeRegistration, ...]`, seeded with:
     - `JobRepository → FakeJobRepository`, `HumanGateRepository → FakeHumanGateRepository`,
       `EngineHealthRepository → FakeEngineHealthRepository`,
       `RotationCursorRepository → FakeRotationCursorRepository`;
     - the twelve production in-memory surfaces, each as its own fake: `BlobPort → InMemoryBlob`,
       `BusPort → InMemoryBus`, `CachePort → InMemoryCache`,
       `ConfigStorePort → InMemoryConfigStore`, `DocsPort → InMemoryDocs`,
       `EmailPort → InMemoryEmail`, `FilesPort → InMemoryFiles`,
       `MessagingPort → InMemoryMessaging`, `SecretsPort → InMemorySecrets`,
       `SiemPort → InMemorySiem`, `SmsPort → InMemorySms`, `IssueTrackerPort → InMemoryTracker`
       (`src/vibey/infrastructure/<surface>/in_memory.py`).
   - `EXEMPT: Mapping[type, ExemptReason]`, seeded with:
     - every Protocol in `application/interfaces/class_contracts.py`. The `*RecordInterface`,
       `EnqueueRequestInterface`, `SelectionInputsInterface` and `RunOutcomeInterface` are
       `VALUE_CONTRACT`. `VerifyIndependencePolicyInterface` is `PURE_POLICY`. The rest are
       `CLASS_CONTRACT`;
     - every Protocol in `ledger_publication_interface.py`. `SearchTokenizerInterface` is
       `PURE_POLICY`. `LedgerExporterInterface` and `LedgerSiteBuilderInterface` are
       `CLASS_CONTRACT`. The rest are `VALUE_CONTRACT`;
     - `FeasibilityAssessmentInterface` and `StartupPreflightReportInterface` (`VALUE_CONTRACT`);
     - `ConductorPreflightInterface`, `EngineHealthServiceInterface`,
       `EngineSelectorInterface`, `SpendMeteringLedgerInterface`,
       `LedgerBudgetSourceInterface` and `WorkerLoopInterface` (`CLASS_CONTRACT`);
     - `BriefProducer` (`PURE_POLICY`: `DeterministicBriefProducer`,
       `application/brief_producer.py:20`).
   - `PENDING: Mapping[str, str]` maps a port's `__qualname__` to the slug of the lane that owes
     its fake:
     - `fakes-deploy`: `CloudClientPort`, `DeploymentSpecStore`, `DeploymentConsentStore`;
     - `fakes-build`: `BudgetSource`, `SkillsContextCompiler`, `BuildProvisioner`,
       `BuildWorktrees`, `GateRunner`, `IntegrationBranch`, `IntegrationLock`,
       `VerifyWorktrees`, `WorkPlanProducer`;
     - `fakes-design`: `DesignProvider`, `DesignQuestionProvider`, `DesignSpecReader`,
       `DesignSpecRepository`, `ResearchProvider`, `SpecSynthesizer`;
     - `fakes-engines`: `EngineProvider`, `EngineAdapter`, `RunFeasibilityEvaluatorInterface`,
       `PreflightHealthServiceInterface`;
     - `fakes-ledger`: `BuildLedger`, `DesignLedger`, `PhaseLedger`, `LedgerReader`,
       `HandoffStore`;
     - `fakes-ledger-publication`: `LedgerSearch`, `LedgerShardStore`, `LedgerSiteWriter`;
     - `fakes-observability`: `Logger`, `NotificationSink`, `TelemetrySpan`,
       `TelemetryTracer`, `TelemetryMetrics`, `Clock`;
     - `fakes-projects`: `ProjectStore`, `ProjectTransitioner`;
     - `fakes-job-wakeup`: `JobHandler`, `JobHandlerFactory`, `JobReadyNotifier`;
     - `fakes-review-visual`: `AutomatedReviewRunner`, `ReviewArtifactWriter`,
       `VisualInventoryProducer`, `VisualInventoryRepository`.
   - `DRIVER_SEAMS: tuple[type, ...]` holds the infrastructure-level seams that must be
     registered too. It is seeded with `vibey.infrastructure.interfaces.CommandExecutor`
     (`src/vibey/infrastructure/interfaces/__init__.py:72`), whose entry in `PENDING` is
     `fakes-process-executor`. Later lanes append their seams here.
3. **`tests/fakes/test_port_parity.py`** keeps its test and its name, and adds these:
   - `test_every_application_port_is_accounted_for`: import every module of
     `vibey.application.interfaces` (`pkgutil.iter_modules`). Collect each class defined in
     that module with `getattr(cls, "_is_protocol", False)` true. Each must be exactly one of:
     a `REGISTRY` port, an `EXEMPT` key, or a `PENDING` key. The failure message names the
     port and says "add a fake to tests/fakes and register it, or exempt it with a reason".
   - `test_every_driver_seam_is_registered_or_pending`.
   - `test_pending_names_a_lane`: every value matches `^(fakes|harness-T\d\d)-[a-z0-9-]+$`.
   - `test_fake_satisfies_its_port` (parametrized over `REGISTRY`): `isinstance(build(), port)`.
   - `test_fake_signatures_match_the_port` (parametrized). The port's members are the
     non-underscore names in `vars(c)`, for every `c` in `port.__mro__` with
     `c.__dict__.get("_is_protocol")`. For each callable member:
     - the parameter names and kinds are equal (`inspect.signature`);
     - a port parameter with a default has a default on the fake;
     - `inspect.iscoroutinefunction` agrees.
     A property member only needs to exist on the fake.
   - `test_fakes_are_not_stubs`: an AST walk of `tests/fakes/*.py`, excluding `test_*.py`.
     - No module imports `unittest.mock`.
     - In each class named in `REGISTRY`, no method body is only `...`, only `pass`, only
       `return None`, or only `raise NotImplementedError(...)`, not counting a docstring.
     - Production in-memory classes (under `src/`) are checked the same way, by reading
       `inspect.getsource(type(fake))`.
4. **`tests/meta/test_patching_ratchet.py`** plus `tests/meta/patching_baseline.json`.
   - The test AST-walks every `tests/**/*.py` except `tests/meta/patching_baseline.json` and
     counts three things per file:
     - `setattr`: calls whose function is the attribute `setattr` on a name `monkeypatch`;
     - `patch`: calls to `patch`, `mock.patch`, `patch.object`, `patch.dict` or
       `mock.patch.object`;
     - `mock`: references to the names `MagicMock`, `AsyncMock`, `Mock`, `NonCallableMock` or
       `create_autospec`.
   - `monkeypatch.setenv`, `delenv`, `chdir` and `syspath_prepend` are not counted: the
     environment is a declared seam.
   - The baseline is `{"<posix path>": {"setattr": n, "patch": n, "mock": n}}`, holding only
     files with a non-zero count, with keys sorted.
   - `test_patch_counts_equal_the_baseline` fails in two cases:
     - when any count differs from the baseline, in either direction. A decrease must be
       written down, which is the ratchet;
     - when a file missing from the baseline counts anything.
     The message prints the corrected JSON entry.
   - Generate the baseline by running the counter once. Add a `__main__` guard to the test
     module that prints the JSON, run it with `uv run python -m tests.meta.test_patching_ratchet`,
     and commit its output.

## Where to change
- `tests/fakes/__init__.py`, `tests/application/fakes.py`, `tests/fakes/test_port_parity.py`.
- New: `tests/fakes/queue.py`, `tests/fakes/engines.py`, `tests/fakes/registry.py`,
  `tests/meta/test_patching_ratchet.py`, `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] Every test that imported from `tests.application.fakes` or `tests.fakes` passes untouched
      (`uv run pytest -q -p no:cacheprovider tests/application tests/fakes tests/system`).
- [ ] Deleting one `PENDING` line makes `test_every_application_port_is_accounted_for` fail,
      naming the port. Check this by hand, then restore the line.
- [ ] Adding `x = MagicMock()` to any test file fails the ratchet. Check this by hand, then revert.
- [ ] `FakeJobRepository` passes the parity and not-a-stub tests as it is today. Its semantic
      gaps are `fakes-queue-gates`'s job.

## Tests to write first (TDD)
The tests are behaviours 3 and 4. Write `test_every_application_port_is_accounted_for` first,
and fill `EXEMPT` and `PENDING` until it passes.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application tests/system

## Out of scope
- Writing new fakes or changing fake behaviour (later lanes).
- Converting any test away from patching (later lanes lower the baseline).
- Tenant packages (each tenant lane adds its own registry and ratchet).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-harness-decouple`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every importer of `tests.application.fakes` and
  `tests.fakes`. R16 and R25 list `tests/fakes/test_port_parity.py` under "must keep
  passing", and it still does: this lane only adds tests to it.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`.
  - Substitution happens at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. It never happens through `monkeypatch.setattr`,
    `mock.patch` or `MagicMock` (sub-doctrine 9.b).
  - Every fake is registered in `tests/fakes/registry.py`, and its `PENDING` entry is
    removed. Every converted file's numbers in `tests/meta/patching_baseline.json` are
    lowered, never raised.
  - A test that needs a real service is marked `integration`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
