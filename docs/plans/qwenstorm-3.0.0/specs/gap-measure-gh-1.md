## Title
feat(vibey-gh): an append-only, digest-chained measurement log in the family-neutral measurement format

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every lane, and the
merge train, the review gate and promotion are vibey-gh's lanes. vibey-gh cannot reach vibey's
ledger: it declares `dependencies = []` and a tenant never imports `vibey` (CLAUDE.md), and it
often runs where no database exists (a CI runner, a push hook). The family already has the
shape for this: the delivery-estimate ledger, an append-only JSONL file whose records carry a
sequence number and a digest-linked predecessor (`src/vibey_tools/gh/vibey_gh/estimate_ledger.py:159-255`,
`DELIVERY_ESTIMATE_LEDGER_FORMAT = "vibey-delivery-estimate-ledger/v1"`, `:39`). This lane adds
the same for measurements. Its payload is exactly the family-neutral measurement format vibey's
codec reads and writes (`vibey.measurement/1`, lane `gap-measure-domain`), so vibey ingests it
(lane `gap-measure-log-ingest`) and vibey's own database-less processes write it
(lane `gap-measure-log-sink`). vibey may import vibey-gh; vibey-gh never imports vibey.

## Required behaviour
1. New `src/vibey_tools/gh/vibey_gh/measurement_log.py`:
   - `MEASUREMENT_LOG_FORMAT: Final = "vibey-measurement-log/v1"`,
     `MEASUREMENT_SCHEMA: Final = "vibey.measurement/1"`,
     `DEFAULT_MEASUREMENT_LOG: Final = Path(".vibey/measurements.jsonl")`, `_GENESIS = "0" * 64`.
   - `class MeasurementLog(MeasurementLogInterface)`:
     - `append(self, payload: Mapping[str, object], path: Path) -> int`:
       - `payload["schema"] == MEASUREMENT_SCHEMA` and `payload["measurement_id"]` a non-empty
         `str`, else `ValueError("a measurement log takes vibey.measurement/1 payloads with a measurement_id")`;
       - creates `path.parent`; opens `path` with `"a+"`, holds `fcntl.flock(handle, fcntl.LOCK_EX)`
         for the whole append (so the harness, a hook and a workflow step never claim one seq),
         seeks to 0 and verifies what is there exactly as `read` does;
       - if a record already carries this `measurement_id`, returns its `seq` and writes nothing
         (appending is idempotent under replay);
       - otherwise writes one line
         `json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n"`, then `flush()`
         and `os.fsync`, where `envelope = {"format": MEASUREMENT_LOG_FORMAT, "seq": n,
         "measurement_id": id, "produced_at": payload.get("ended_at"), "previous_digest": prev,
         "payload": dict(payload)}` plus `"digest"` = the sha256 of that envelope's canonical
         JSON (sorted keys, `(",", ":")` separators) — `n` is the last `seq` + 1 (1 when empty),
         `prev` the last `digest` (`_GENESIS` when empty). Returns `n`.
     - `read(self, path: Path) -> tuple[Mapping[str, object], ...]`: a missing file is `()`;
       blank lines are skipped; every other line must be a JSON object with `format ==
       MEASUREMENT_LOG_FORMAT`, `seq` the next integer (not `bool`), `previous_digest` the last
       digest, a mapping `payload`, and a `digest` equal to the recomputed one; else
       `ValueError(f"measurement log line {number}: {reason}")` naming which check failed
       ("is not JSON", "is not an object", "has format …", "has seq 3, expected 2", "breaks the
       digest chain", "has an invalid digest", "has no object payload").
     - The digest is a `@staticmethod _digest(value: Mapping[str, object]) -> str` (copy
       `estimate_ledger.py:280-282`).
2. New `src/vibey_tools/gh/vibey_gh/interfaces/measurement_log_interface.py`:
   `@runtime_checkable class MeasurementLogInterface(Protocol)` with `append` and `read`
   (copy the style of `vibey_gh/interfaces/delivery_estimate_interface.py:313-319`).
3. The module docstring says: the payload format is vibey's `vibey.measurement/1`
   (`src/vibey/domain/measurement.py`), kept family-neutral so vibey-gh needs no import of
   vibey; vibey's contract test (lane `gap-measure-log-ingest`) proves both sides agree.

## Where to change
- New `src/vibey_tools/gh/vibey_gh/measurement_log.py` and its interface file.
- New `src/vibey_tools/gh/test/test_measurement_log.py`.

## Acceptance criteria
- [ ] Three appends give seqs 1, 2, 3; `read` returns them in order; the second's
      `previous_digest` is the first's `digest`.
- [ ] Appending a payload whose `measurement_id` is already present returns the first seq and
      the file does not grow.
- [ ] Editing any byte of a line's `payload` makes `read` raise naming that line; so does
      removing line 2.
- [ ] 4 threads × 25 appends through 4 separate `MeasurementLog` instances on one path leave
      seqs 1…100 with an intact chain.
- [ ] `vibey_gh` still declares `dependencies = []`; the tenant's suite passes at its floor.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_measurement_log.py` (`tmp_path` files; no `monkeypatch.setattr`):
- `test_appends_number_and_chain`
- `test_append_is_idempotent_by_measurement_id`
- `test_a_payload_that_is_not_a_measurement_is_refused`
- `test_a_missing_log_reads_empty`
- `test_tampering_is_detected` (parametrized: payload edited, line removed, format changed,
  not JSON, a JSON array)
- `test_concurrent_appenders_never_share_a_seq`
- `test_the_log_satisfies_its_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports

## Out of scope
- Writing measurements from any command (`gap-measure-gh-2`); vibey's side (`gap-measure-log-sink`,
  `gap-measure-log-ingest`); the delivery-estimate ledger, unchanged.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(vibey-gh): an append-only, digest-chained measurement log in the family-neutral measurement format`. Do not push.

## Lane card
- **Depends on:** none (a vibey-gh tenant lane).
- **Standing constraints (every tenant lane):** the tenant's own gates and floor pass on its
  Python floor (ADR-0022); `tools-lint` runs both black and ruff format; vibey-gh stays
  dependency-free; never raise `test/patching_baseline.json` (lane `fakes-tenant-gh-1`).
- **Must keep passing unchanged:** every vibey-gh test and the protected root tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
