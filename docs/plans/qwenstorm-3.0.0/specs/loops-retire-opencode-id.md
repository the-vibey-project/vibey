## Title
feat(engines)!: retire the opencode engine id — stored text reads verbatim, nothing writes it

ADR-0046 lane L38c (slug `loops-retire-opencode-id`).

## Why
ADR-0046 §9 (`specs/ADR-two-loops.md:291`): L38 "retires the engine id: a stored `opencode` reads
verbatim, is never written, and `known("opencode")` is `None`, which is a correct no-op exclusion
because nothing can run it". The Migration table (`:399`): stored engine id `opencode` — "read
verbatim; never written — **forever**". Readers are forward-compatible and writers strict
(`src/vibey/domain/stored_value.py:10-24`, vibey#275/#287): once `OPENCODE` is not an `EngineId`
member, `ENGINE_ID_PARSER.parse("opencode")` is `UnrecognizedEngineId("opencode")` — the ledger's
hash chain covers the stored text and still verifies (`domain/ledger_chain.py:5-6`).

Every member needs a descriptor, classifier, four fixtures, an event map and argv goldens, so they
leave together with the member (`tests/infrastructure/engines/test_descriptors.py:39-42`,
`test_classify.py:24-54`, `test_loop_events.py:378-384`, `test_argv.py:41-45`; integration `d3b4a388`).

## Required behaviour
0. **Gate (ADR-0046 §9: live conformance first).** Unless
   `grep "V-VS CONFORMANCE: PASS" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`
   prints a line naming Arch Linux and a line naming macOS, change nothing and report
   `gated: vscode has not passed live conformance on both OSes`.
1. **`src/vibey/domain/engine.py`**: delete `OPENCODE = "opencode"` from `EngineId`. Add after
   `ENGINE_ID_ALIASES`:
   ```python
   RETIRED_ENGINE_IDS: Final[frozenset[str]] = frozenset({"opencode"})
   """Engine ids a release retired (ADR-0046 §9). Stored rows keep them verbatim, forever;
   nothing writes them; `EngineId(...)` and `known(...)` refuse them."""
   ```
   `_missing_` must not resolve a retired id (it returns None for it, so `EngineId("opencode")`
   raises ValueError).
2. **Descriptors** (`infrastructure/engines/descriptors.py`): delete the `OPENCODE` descriptor
   (`:242-287` at `d3b4a388`) and its entry in `DEFAULT_DESCRIPTORS` (`:409`), and update the
   `descriptors.py` comment that mentions OpenCode's zero pricing only if it no longer applies
   (the `VSCODE_PAID` comment from lane `loops-vscode-engine-ids` cites "the OpenCode precedent":
   reword it to stand alone: "a paid provider's price is metered from the run's own usage events").
3. **Classifier** (`infrastructure/engines/classify.py`): delete `_OPENCODE_CAPACITY_BY_ERROR_NAME`
   and `_classify_opencode` (from `:167`), the `EngineId.OPENCODE` entry of `_CLASSIFIERS` (`:221`)
   and of the four fixture maps (`:244`, `:274`, `:297`, `:316`), and the docstring mention at `:14`.
4. **Event map** (`infrastructure/engines/loop_events.py`): delete the `EngineId.OPENCODE` block (`:193-206`).
5. **Cluster preflight** (`infrastructure/cluster_preflight.py`): nothing names `EngineId.OPENCODE`
   after lane `loops-retire-opencode-refusals`; confirm with grep.
6. **Ledger actors** (`src/vibey/domain/ledger_query.py`, `ActorResolver.resolve`): after the
   alias loop added by lane `loops-engine-id-sovereignloop`, resolve each `RETIRED_ENGINE_IDS`
   text to `Actor(ActorScope.ENGINE, <text>)`, so `vibey ledger search --actor opencode` still
   finds history.
7. **CRD binding** (`tests/meta/test_crd_engine_enum.py`): assert
   `sorted(declared) == sorted({*(e.value for e in EngineId), *ENGINE_ID_ALIASES, *RETIRED_ENGINE_IDS})`.
   The CRD enum keeps `opencode`.
8. **Tests that exist only for OpenCode** — delete exactly these (they test deleted code):
   - `tests/infrastructure/engines/golden/opencode_{trivial,low,standard,high,max}.txt`;
   - `tests/infrastructure/engines/test_argv.py::test_opencode_resume_keeps_the_vibey_run_id` (`:107-125`);
   - `tests/infrastructure/engines/test_classify.py`: every `test_opencode_*` function (`:164-275`);
   - `tests/infrastructure/engines/test_descriptors.py::test_opencode_has_no_portable_cli_effort_control` (`:77-83`),
     and `EngineId.OPENCODE` from the exclusion set at `:25` (it becomes `{EngineId.CODEXLOOP}`);
     if `test_the_local_descriptors_are_exactly_the_local_tier` (`:165-173`) still asserts a
     LOCAL descriptor inside `DEFAULT_DESCRIPTORS`, it now asserts `{EngineTier.PAID}`;
   - `tests/infrastructure/engines/test_loop_events.py`: the `EngineId.OPENCODE` entries of
     `_EXPECTED_MAPS` (`:363-372`) and `_TURN_BOUNDARIES` (`:405`);
   - `tests/infrastructure/test_cluster_preflight.py::test_without_an_allow_list_can_report_every_engine_keyed`
     (`:143-150`): replace `EngineId.OPENCODE: ("OPENCODE_CONFIG",)` by
     `EngineId.CLAUDELOOP_LOCAL: ("CLAUDELOOP_LOCAL_TOKEN",)` and the environment key
     `"OPENCODE_CONFIG": "mounted"` by `"CLAUDELOOP_LOCAL_TOKEN": "mounted"`, keeping the test's
     intent (a deployment-supplied key map is honoured by the generic port) and its assertions
     with the engine name changed accordingly.
   Stop rule: any other failing test → stop and report.

## Where to change
- `src/vibey/domain/engine.py`, `src/vibey/domain/ledger_query.py`,
  `src/vibey/infrastructure/engines/descriptors.py`, `classify.py`, `loop_events.py` (edit_file each).
- The tests and goldens in behaviour 8; `tests/meta/test_crd_engine_enum.py`.
- New test: `tests/domain/test_retired_engine_ids.py`.

## Acceptance criteria
- [ ] `ENGINE_ID_PARSER.parse("opencode") == UnrecognizedEngineId("opencode")`, and `ENGINE_ID_PARSER.known("opencode") is None`.
- [ ] `EngineId("opencode")` raises `ValueError`; `EngineId("qwenloop") is EngineId.SOVEREIGNLOOP` still.
- [ ] `ActorResolver().resolve("opencode") == Actor(ActorScope.ENGINE, "opencode")`.
- [ ] `grep -rn "EngineId.OPENCODE\|descriptors import OPENCODE\|_classify_opencode" src tests` prints nothing.
- [ ] The whole default tier passes; 100% branch coverage on `domain/` and `infrastructure/`.

## Tests to write first (TDD)
`tests/domain/test_retired_engine_ids.py`:
- `test_a_stored_opencode_reads_verbatim`
- `test_a_retired_id_is_never_known`
- `test_a_retired_id_cannot_be_constructed`
- `test_aliases_still_resolve_after_retirement`
- `test_ledger_actor_resolves_a_retired_engine_text`
- `test_retired_and_member_texts_are_disjoint` (no retired id is a member value or an alias key)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/engines tests/infrastructure/test_cluster_preflight.py tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `opencodeloop` tenant and its packaging (`loops-remove-opencode-tenant`).
- Any SQL: stored rows are never rewritten (append-only ledger; health/cursor rows go stale and
  are skipped, ADR-0046 Migration).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally as `feat(engines)!: …` with a `BREAKING CHANGE:`
  footer: "the opencode engine id is retired; stored rows keep it and read it verbatim".

**Depends on:** `loops-retire-opencode-infra`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
