## Title
feat(engines): rename the qwenloop engine id to sovereignloop behind an alias that never touches stored text

ADR-0046 lane L06 (slug `loops-engine-id-sovereignloop`).

## Why
- **The law.** Sub-doctrine 8.c names `sovereignloop` as "what `qwenloop` becomes"
  (`src/vibey_tools/gh/docs/doctrines.md:196-234`), and 8.b makes it the default engine
  (`:127-134`). ADR-0046 §7 (`specs/ADR-two-loops.md:255-261`) and its Migration table (`:398`,
  `:400`) set the mechanism:
  - `EngineId.SOVEREIGNLOOP = "sovereignloop"` replaces `QWENLOOP`, which stays a Python enum
    alias until lane L09;
  - `EngineId("qwenloop")` resolves through `_missing_`;
  - `ENGINE_ID_ALIASES = {"qwenloop": EngineId.SOVEREIGNLOOP}`; `known()` (acting consumers)
    resolves it, `parse()` (preserving readers) never does;
  - the CRD enum holds every member plus every alias key.
- **Stored text is sacred.** Each ledger chain link hashes the event's engine text
  (`src/vibey/domain/ledger_chain.py:3-8`, the field at `:156`), and the ledger is append-only
  (7.c, `doctrines.md:82-91`). So a stored `qwenloop` must read back byte for byte, forever
  (ADR-0046 `:90-96`).
- **The gaps, at integration `d3b4a388`:**
  - `EngineId.QWENLOOP = "qwenloop"` (`src/vibey/domain/engine.py:32`).
  - `StoredValueParser` has no alias table (`src/vibey/domain/stored_value.py:85-97`).
  - The CRD enum has no `sovereignloop` (`deploy/helm/vibey/templates/crd-vibeyproject.yaml:78`),
    and its binding test compares members only (`tests/meta/test_crd_engine_enum.py:20-24`).
  - `ActorResolver.resolve` matches members only (`src/vibey/domain/ledger_query.py:106-122`),
    so `vibey ledger search --actor qwenloop` would stop finding history.
- **A preserving reader the design sheet missed.** `LedgerRecordCodec.from_fields` reads
  `engine_id` with `EngineId(text)` (`src/vibey/domain/ledger_record.py:99-101`, through `_member`
  at `:135-141`). Once `_missing_` exists, a handoff-ledger line, a published shard record or a
  cold-tier record (`src/vibey/infrastructure/ledger/tier_manager.py:84`) holding `qwenloop`
  would decode to `SOVEREIGNLOOP` and re-encode as `sovereignloop`, breaking the chain link it
  was hashed under. This was reproduced on a scratch copy of `d3b4a388`. This lane closes it.

## Required behaviour
1. **`src/vibey/domain/engine.py`.**
   - Add `from types import MappingProxyType` to the imports (after `from enum import StrEnum`).
   - In `class EngineId`, replace the line `    QWENLOOP = "qwenloop"` (`:32`) with:
     ```python
         SOVEREIGNLOOP = "sovereignloop"
         # The rename wave's alias (ADR-0046 §7); lane L09 removes it.
         QWENLOOP = "sovereignloop"
     ```
     `QWENLOOP` is then a Python enum alias: `EngineId.QWENLOOP is EngineId.SOVEREIGNLOOP`, and
     iterating `EngineId` yields `SOVEREIGNLOOP` once and never `QWENLOOP`.
   - After `CLAUDELOOP_LOCAL = "claudeloop-local"` (still inside the class) add:
     ```python

         @classmethod
         def _missing_(cls, value: object) -> "EngineId | None":
             """A legacy spelling constructs its current member (ADR-0046 §7), so every
             consumer that *acts* on an id -- `EngineId(name)` on a flag or a config key --
             keeps working. Preserving readers use `ENGINE_ID_PARSER.parse`, which never
             resolves an alias."""
             if isinstance(value, str):
                 return ENGINE_ID_ALIASES.get(value)
             return None
     ```
   - Directly after the class (before `class EngineTier`) add:
     ```python
     ENGINE_ID_ALIASES: Final[Mapping[str, EngineId]] = MappingProxyType(
         {"qwenloop": EngineId.SOVEREIGNLOOP}
     )
     """Legacy engine-id spellings and the member each now names (ADR-0046 §7, Migration).
     `known()` and `EngineId(...)` resolve them; `parse()` never does, so stored text is kept
     verbatim. Kept forever: the ledger holds these spellings for good."""
     ```
   - `ENGINE_ID_PARSER` (`:73-76`) becomes
     `StoredValueParser(EngineId, UnrecognizedEngineId, aliases=ENGINE_ID_ALIASES)`; its
     annotation and docstring are unchanged.
   - `UnrecognizedEngineId.members` (`:65`) is **not** edited. It is built from member values, so
     `"qwenloop"` is no longer a member and `UnrecognizedEngineId("qwenloop")` constructs.
2. **`src/vibey/domain/stored_value.py`, `class StoredValueParser`.**
   - `__init__` (`:85-87`) becomes:
     ```python
         def __init__(
             self,
             members: type[M],
             unrecognized: Callable[[str], U],
             *,
             aliases: Mapping[str, M] | None = None,
         ) -> None:
             self._members: Mapping[str, M] = {member.value: member for member in members}
             self._unrecognized = unrecognized
             self._aliases: Mapping[str, M] = dict(aliases) if aliases is not None else {}
     ```
   - `known` (`:94-97`) returns the member, else `self._aliases.get(raw)`; add one docstring
     sentence: "A legacy spelling in `aliases` is resolved here, for consumers that act on the id."
     ```python
             member = self._members.get(raw)
             return member if member is not None else self._aliases.get(raw)
     ```
   - `parse` (`:89-92`) is **unchanged**: it never consults `_aliases`.
3. **`src/vibey/domain/interfaces/stored_value_interface.py`**: the `known` docstring (`:34`)
   becomes `"""The member, or None for a value this vibey does not know. Resolves a declared
   legacy spelling (alias); `parse` never does."""`. No signature changes.
4. **`src/vibey/domain/ledger_query.py`, `ActorResolver.resolve`.** Import
   `ENGINE_ID_ALIASES` beside `EngineId` (`:31`). After the member loop (`:110-112`) and before
   the provenance loop (`:113`) add:
   ```python
           for legacy in ENGINE_ID_ALIASES:
               if needle == legacy:
                   return Actor(ActorScope.ENGINE, legacy)
   ```
   So `resolve("qwenloop")` is `Actor(ActorScope.ENGINE, "qwenloop")` and legacy events are still
   found by their stored text. The error message (`:116-121`) is unchanged.
5. **`src/vibey/domain/ledger_record.py` (the missed preserving reader).** Import
   `ENGINE_ID_ALIASES`, `StoredEngineId` and `UnrecognizedEngineId` beside `EngineId` (`:22`). In
   `from_fields`, replace the `engine_id=self._optional(...)` argument (`:99-101`) with
   `engine_id=self._optional(fields, "engine_id", lambda key: self._engine(fields, key)),` and add
   this method directly before the `@staticmethod` line above `_optional` (`:142-143`):
   ```python
       def _engine(self, fields: Mapping[str, object], key: str) -> StoredEngineId:
           text = self._text(fields, key)
           if text in ENGINE_ID_ALIASES:
               # A legacy spelling is stored text, kept verbatim (ADR-0046 §7): the ledger
               # chain hashes it, so resolving the alias here would break the chain.
               return UnrecognizedEngineId(text)
           return self._member(fields, key, EngineId)
   ```
   Every other engine text behaves as today: a member reads as its member, anything else is
   refused with `'engine_id' has no member ...`.
6. **CRD** (`deploy/helm/vibey/templates/crd-vibeyproject.yaml:78`): the enum becomes exactly
   `enum: [claudeloop, codexloop, cursorloop, agyloop, opencode, sovereignloop, qwenloop, claudeloop-local]`.
   The Helm goldens do not render this template (it is guarded by `operator.enabled`), so no
   golden changes.
7. **Binding test** (`tests/meta/test_crd_engine_enum.py`): import `ENGINE_ID_ALIASES` beside
   `EngineId` (`:13`); the assertion (`:24`) becomes
   `assert sorted(declared) == sorted({*(engine.value for engine in EngineId), *ENGINE_ID_ALIASES})`.
8. **Expected-text updates, and nothing else.** Every writer now stores and prints
   `sovereignloop` where it stored `qwenloop`, because `EngineId.QWENLOOP.value` is now
   `"sovereignloop"`. Update exactly these expectations (verified by running the suite without the
   database, and by reading the database-bound tests), and list each one in the commit body:
   - `tests/infrastructure/engines/golden/qwenloop_{trivial,low,standard,high,max}.txt`: rename
     each file with `git mv` to `sovereignloop_<effort>.txt`, **contents unchanged** (the binary is
     still `qwenloop` until lane `loops-tenant-legacy-paths`). `test_argv.py:31-38` builds the
     golden name from `descriptor.engine_id.value`, and `:41-45` counts one file per descriptor
     and effort.
   - `tests/infrastructure/engines/test_local_engines.py`,
     `test_every_enabled_engine_gets_an_adapter_carrying_its_overlay` (`:166-175`):
     `{"FOR": "qwenloop"}` becomes `{"FOR": "sovereignloop"}`.
   - `tests/infrastructure/test_cluster_preflight.py`,
     `test_an_allow_listed_engine_that_takes_no_key_is_judged_on_presence_alone` (`:198-203`):
     `"(qwenloop takes no API key)"` becomes `"(sovereignloop takes no API key)"`.
   - `tests/cli/test_operational_commands.py` (integration tier: `pytestmark` at `:25` and a
     PostgreSQL autouse fixture at `:34`):
     - `test_doctor_lists_the_sovereign_engine_when_it_is_switched_on` (`:984-997`):
       `assert "qwenloop" in res.output` becomes `assert "sovereignloop" in res.output`;
     - `test_doctor_omits_the_sovereign_engine_when_it_is_off` (`:1000-1006`):
       `assert "qwenloop" not in res.output` becomes `assert "sovereignloop" not in res.output`
       (otherwise it passes vacuously);
     - `test_worker_sweeps_qwenloop_when_the_feature_is_on` (`:1535-1565`):
       `"no recorded conformance for qwenloop"` becomes `"no recorded conformance for sovereignloop"`,
       and `== ("qwenloop",)` becomes `== ("sovereignloop",)`.
   - `tests/cli/test_sovereign_provider_options.py` (integration tier: `:32`, `:114`),
     `test_research_without_evidence_parks_a_research_evidence_gate` (`:273-333`):
     `assert recorded["engine_id"] == "qwenloop"` (`:331`) becomes `== "sovereignloop"`.
   - Lane `engines-pool` lands first and edits some of these tests. Find each one by its test name
     and quoted text, not by line. If engines-pool added a test whose assertion compares a printed
     or stored engine id with the literal `"qwenloop"`, apply the same one-literal replacement and
     list it.
   - **Leave every other `"qwenloop"` literal alone.** They are provider names
     (`--provider qwenloop`), feature keys (`[features] qwenloop`, `VIBEY_FEATURE_QWENLOOP`),
     config strings, or legacy inputs the alias must keep accepting
     (`implementer_engine_id: "qwenloop"` in `tests/application/test_engine_selection.py:318`,
     `:533`, `:554`, `:576`, which passes **unedited** because `known("qwenloop")` is
     `SOVEREIGNLOOP`).
   - **Stop rule:** if any other test fails, and the fix is not one such literal replacement, stop
     and report the test and its failure. Do not change production code to make it pass.

## Where to change
- `src/vibey/domain/engine.py` (167 lines), `src/vibey/domain/stored_value.py` (97),
  `src/vibey/domain/ledger_query.py` (223), `src/vibey/domain/ledger_record.py` (159): use
  `edit_file` only.
- `src/vibey/domain/interfaces/stored_value_interface.py`: one docstring line, `edit_file`.
- `deploy/helm/vibey/templates/crd-vibeyproject.yaml`: one line, `edit_file`.
- `tests/meta/test_crd_engine_enum.py`: two lines, `edit_file`.
- The expected-text updates and golden renames in behaviour 8.
- New test file `tests/domain/test_engine_aliases.py`. Line 1 is the provenance comment, copied
  byte for byte from line 1 of `tests/domain/test_engine.py`. For a ledger event, copy the
  `_event` helper of `tests/domain/test_ledger_record.py:23-42`.
- The pattern for an alias-aware shared parser is `ENGINE_ID_PARSER` itself (`engine.py:73-76`).

## Acceptance criteria
- [ ] `EngineId.QWENLOOP is EngineId.SOVEREIGNLOOP`, `EngineId("qwenloop") is EngineId.SOVEREIGNLOOP`,
      and `"qwenloop" not in {e.value for e in EngineId}`
      (`test_the_legacy_spelling_constructs_the_current_member`).
- [ ] `ENGINE_ID_PARSER.known("qwenloop") is EngineId.SOVEREIGNLOOP` and
      `ENGINE_ID_PARSER.parse("qwenloop") == UnrecognizedEngineId("qwenloop")`
      (`test_known_resolves_the_alias_and_parse_keeps_the_text`).
- [ ] A ledger record holding `"engine_id": "qwenloop"` reads as `UnrecognizedEngineId("qwenloop")`
      and writes back `"qwenloop"`
      (`test_a_ledger_record_keeps_a_legacy_engine_spelling_verbatim`).
- [ ] `ActorResolver().resolve("QWENLOOP ") == Actor(ActorScope.ENGINE, "qwenloop")`.
- [ ] `tests/meta/test_crd_engine_enum.py` passes with the CRD listing
      `sovereignloop` and `qwenloop`.
- [ ] `ls tests/infrastructure/engines/golden | grep -c '^sovereignloop_'` prints `5`, and
      `ls tests/infrastructure/engines/golden | grep -c '^qwenloop_'` prints `0`.
- [ ] `git diff HEAD~1 -- tests/application/test_engine_selection.py tests/live` is empty.
- [ ] The whole default tier passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_engine_aliases.py` (pure: no database, no I/O):
- `test_sovereignloop_is_the_member_and_qwenloop_its_python_alias`:
  `EngineId.SOVEREIGNLOOP.value == "sovereignloop"`, `EngineId.QWENLOOP is EngineId.SOVEREIGNLOOP`,
  `"QWENLOOP" in EngineId.__members__`, and `list(EngineId).count(EngineId.SOVEREIGNLOOP) == 1`.
- `test_the_legacy_spelling_constructs_the_current_member`: `EngineId("qwenloop")` and
  `EngineId("sovereignloop")` are both `EngineId.SOVEREIGNLOOP`.
- `test_an_unknown_value_is_still_refused`: `EngineId("nope")` and `EngineId(1)` raise
  `ValueError` (the second covers `_missing_`'s non-string branch).
- `test_known_resolves_the_alias_and_parse_keeps_the_text`: `known("qwenloop") is
  EngineId.SOVEREIGNLOOP`; `known("nope") is None`; `parse("qwenloop") ==
  UnrecognizedEngineId("qwenloop")`, its `.value` and `str()` are `"qwenloop"`;
  `parse("sovereignloop") is EngineId.SOVEREIGNLOOP`.
- `test_the_legacy_text_is_not_a_member_value`: `"qwenloop" not in UnrecognizedEngineId.members`;
  `UnrecognizedEngineId("sovereignloop")` raises `ValueError`.
- `test_every_alias_names_a_member_and_is_not_itself_a_member_value`: for each key and value of
  `ENGINE_ID_ALIASES`, the value is an `EngineId` and the key is not a member value.
- `test_the_alias_table_is_read_only`: assigning `ENGINE_ID_ALIASES["x"] = EngineId.CLAUDELOOP`
  raises `TypeError` (`# type: ignore[index]` on that line).
- `test_a_parser_without_aliases_resolves_nothing_extra`:
  `StoredValueParser(EngineId, UnrecognizedEngineId).known("qwenloop") is None`.
- `test_the_ledger_actor_resolver_finds_legacy_engine_text`: `ActorResolver().resolve("qwenloop")`
  and `resolve(" QWENLOOP ")` equal `Actor(ActorScope.ENGINE, "qwenloop")`;
  `resolve("sovereignloop") == Actor(ActorScope.ENGINE, "sovereignloop")`.
- `test_a_ledger_record_keeps_a_legacy_engine_spelling_verbatim`: take
  `fields = {**LEDGER_RECORDS.to_fields(_event()), "engine_id": "qwenloop"}`; `event =
  LEDGER_RECORDS.from_fields(fields)`; `event.engine_id == UnrecognizedEngineId("qwenloop")`; and
  `LEDGER_RECORDS.to_fields(event) == fields`.
- `test_a_ledger_record_still_refuses_an_unknown_engine`: the same with `"engine_id": "nope"`
  raises `InvalidLedgerRecord` matching `"'engine_id' has no member 'nope'"`; with
  `"sovereignloop"` it reads as `EngineId.SOVEREIGNLOOP`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands. The two CLI files are
integration-tier tests: they need that database themselves.

    uv run ruff format src/vibey/domain/engine.py src/vibey/domain/stored_value.py src/vibey/domain/interfaces/stored_value_interface.py src/vibey/domain/ledger_query.py src/vibey/domain/ledger_record.py tests/meta/test_crd_engine_enum.py tests/domain/test_engine_aliases.py tests/infrastructure/engines/test_local_engines.py tests/infrastructure/test_cluster_preflight.py tests/cli/test_operational_commands.py tests/cli/test_sovereign_provider_options.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/meta tests/infrastructure/engines tests/infrastructure/ledger tests/infrastructure/test_cluster_preflight.py tests/application
    uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py tests/cli/test_sovereign_provider_options.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/live tests/application/test_engine_selection.py

## Out of scope
- The descriptor's binary, state directory and done marker (`qwenloop`, `.qwenloop`,
  `QWENLOOP_TASK_FULLY_COMPLETE`): lane `loops-tenant-legacy-paths`.
- Config names (`DEFAULT_ENGINES`, `KNOWN_ENGINES`, `[features] qwenloop`, `[qwenloop]`): lanes
  `loops-config-engine-names` and `loops-config-sovereignloop-table`.
- `--provider qwenloop`, the environment names and the chart: later rename lanes.
- Removing the `QWENLOOP` alias (lane `loops-drop-qwenloop-alias`, L09). `_missing_` and
  `ENGINE_ID_ALIASES` stay forever.
- Any SQL or data migration: stored rows are never rewritten (ADR-0046 Migration, `:398`).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject, and list
  every expected-text update and golden rename in the body.

**Depends on:** `engines-pool`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
