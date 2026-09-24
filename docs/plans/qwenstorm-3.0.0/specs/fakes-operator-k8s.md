## Title
test(fakes): the kopf handlers take their composition from kopf's memo, and an in-memory apps API answers the surface health checks

## Why
The kopf handlers in `src/vibey/infrastructure/operator/handlers.py` must be module-level
functions, because kopf registers them by decorator. They reach their collaborators in two
ways that tests can only change by patching:
- `on_create` and `reconcile` (`:137-184`) call `build_app()` directly. So
  `tests/infrastructure/test_operator_handlers.py` (14 tests, `pytestmark = integration`)
  needs PostgreSQL.
- `on_surface_create` and `reconcile_surface_cron` (`:259-284`) call `reconcile_surface(...)`
  with the default `client_factory=_apps_client` (`:197-203`: `load_incluster_config()` then
  `AppsV1Api()`). `tests/infrastructure/test_operator_surface_handlers.py:100-130` patches
  `kubernetes.config.load_incluster_config`, `kubernetes.client.AppsV1Api` and
  `vibey.infrastructure.operator.handlers.reconcile_surface`.

kopf has a declared way to hand handlers shared objects. `kopf.run(memo=kopf.Memo(...))`
seeds each resource's `memo`, and handlers receive it as the `memo` keyword. Using it is
substitution at a declared seam. `deployment_health` and `reconcile_surface` already accept
`client_factory`; only the handlers ignore it.

## Required behaviour
1. **`class OperatorComposition`** in `handlers.py`, with an interface in
   `src/vibey/infrastructure/operator/interfaces/handlers_interface.py`:
   - `open_app: Callable[[], AbstractAsyncContextManager[AppResources]]`, defaulting to
     `build_app`. The operator is outside `cli/`, so it cannot use `CliComposition`. It keeps
     its own, in the same shape;
   - `apps_client: Callable[[], AppsApiInterface]`, defaulting to `InClusterAppsClient()`
     (behaviour 6).
   A module constant `DEFAULT_COMPOSITION` holds the default instance.
2. **`AppsApiInterface`** (same interface file) declares the one call used,
   `read_namespaced_deployment_status(name: str, namespace: str) -> Any`. Add
   `vibey.infrastructure.operator.interfaces` to `.importlinter`'s
   `infrastructure-interfaces-declare-only` `source_modules`.
3. **Every handler takes `memo: kopf.Memo | None = None`**, and resolves
   `composition = getattr(memo, "composition", None) or DEFAULT_COMPOSITION`:
   - `on_create` and `reconcile` use `composition.open_app()`;
   - `on_surface_create` and `reconcile_surface_cron` pass
     `client_factory=composition.apps_client` to `reconcile_surface`.
   `run(namespace=None)` passes `memo=kopf.Memo(composition=DEFAULT_COMPOSITION)` to `kopf.run`.
4. **`tests/fakes/k8s.py` — `class InMemoryAppsApi`** (`AppsApiInterface`):
   - `deployments: dict[tuple[str, str], tuple[int | None, int | None]]`, which is
     `(namespace, name) -> (available, desired)`;
   - `read_namespaced_deployment_status(name, namespace)` returns an object with
     `.status.available_replicas` and `.spec.replicas`, or raises the scripted exception
     (`fail(namespace, name, exc)`). An unknown deployment raises an exception shaped like
     `kubernetes.client.ApiException` (status 404). Build it without importing kubernetes, as
     a small class with `status=404`;
   - `reads` records every call.
5. **Registry.** Register `AppsApiInterface → InMemoryAppsApi()`, and add it to `DRIVER_SEAMS`.
6. **`_apps_client` becomes `class InClusterAppsClient`**, whose instance is the default
   `apps_client`:
   - `__init__(self, *, load_config: Callable[[], None] | None = None, api: Callable[[], AppsApiInterface] | None = None)`;
   - `__call__` resolves `None` to `kubernetes.config.load_incluster_config` and
     `kubernetes.client.AppsV1Api`, imported inside the method as today, calls
     `load_config()` and returns `api()`.
   A test covers it by injecting two recording callables, with no import patched.
   **Switch the surface-handler tests:** `test_operator_surface_handlers.py` passes
   `memo=kopf.Memo(composition=OperatorComposition(apps_client=lambda: api))` with an
   `InMemoryAppsApi`, and its three `patch(...)` blocks go.
7. `tests/infrastructure/test_operator_handlers.py` (PostgreSQL) is **not** switched here.
   `fakes-tui-system` moves it onto the fake app once `fakes-bootstrap-seam` exists. This lane
   only adds `memo=` to its calls if the handlers' new keyword requires it. It does not: the
   keyword defaults to `None`.

## Where to change
- `src/vibey/infrastructure/operator/handlers.py`, new `src/vibey/infrastructure/operator/interfaces/`, `.importlinter`.
- New `tests/fakes/k8s.py`, `tests/fakes/test_fake_k8s.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/infrastructure/test_operator_surface_handlers.py`.

## Acceptance criteria
- [ ] `grep -c "patch(" tests/infrastructure/test_operator_surface_handlers.py` prints `0`.
- [ ] A surface with one healthy and one missing Deployment reports both conditions from `InMemoryAppsApi`.
- [ ] 100% `infrastructure/` coverage. `lint-imports` passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_k8s.py`:
- `test_apps_api_reports_replicas`
- `test_apps_api_unknown_deployment_is_a_404`
- `test_apps_api_scripted_failure`

In `tests/infrastructure/test_operator_surface_handlers.py`:
- `test_handlers_default_to_the_production_composition`
- `test_memo_composition_reaches_reconcile_surface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/test_operator_surface_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `vibey operator` CLI command's `patch("vibey.infrastructure.operator.run")` (`fakes-cli-composition`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `.importlinter` (append one line).
- **Must keep passing unchanged:** `tests/infrastructure/test_operator_handlers.py` (integration), the chart goldens, and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
  - The kopf handlers stay module functions. kopf requires it, and each carries that reason at its definition.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
