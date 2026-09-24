## Title
test(vibey-bootstrap): the transports, service bus, alerts and webhooks take their SDK clients by injection, and in-memory fakes replace the coverage-fill mocks

## Why
vibey-bootstrap's `test/coverage_fill/` holds 16 modules written to reach coverage by
patching SDK entry points and module attributes. The largest are:
- `test_alerts_dispatcher_fill.py`: 36;
- `test_transports_cloud_fill.py`: 31 (`azure.eventhub`, `azure.kusto.ingest`, and
  `vibey_bootstrap.transports.adx` and `.nosql`);
- `test_closing_gaps_fill.py`: 27;
- `test_consumer_wrapper_fill.py`: 25;
- `test_locks_masking_webhook_fill.py` and `test_long_tail_fill.py`: 21 each;
- `test_transports_sql_blob_fill.py`, `test_transports_core_fill.py` and
  `test/v3/test_transport_contracts.py`: 19 each;
- `test/servicebus/test_consumer_wrapper.py`: 21.

They exercise real branches through fake-by-patch. This lane moves them onto injected clients
backed by in-memory fakes, transport by transport. It follows the pattern of lanes 1 and 2, and
of R04's `vibey_bootstrap.amqp.memory.InMemoryAmqpClient`, which ships in the package.

## Required behaviour
1. **One client factory per external SDK,** declared as an interface beside the transport
   that uses it, with the production default doing today's lazy import:
   - the Event Hubs producer;
   - the Kusto ingest client;
   - the Cosmos and Mongo client (the `nosql` transport);
   - the Blob service client;
   - the SQL engine (the `sql` transport already uses SQLAlchemy URLs; inject the engine factory);
   - the Service Bus receiver and sender (the consumer wrapper);
   - the alert dispatcher's HTTP client (the webhooks).
2. **`test/fakes/`** gains an in-memory fake per factory, with real behaviour:
   - `InMemoryEventHub` records batches, and enforces the batch size limit the transport relies on;
   - `InMemoryKustoIngest` records ingestions, and can fail on cue;
   - `InMemoryDocumentStore` implements the insert and find subset the `nosql` transport
     uses. `mongomock` remains an alternative only where the transport's code needs query
     operators the fake would have to reimplement; say which;
   - `InMemoryBlobService` holds containers and blobs, and raises `ResourceExistsError` on
     duplicate create;
   - `InMemoryServiceBus` provides queues with peek-lock, `complete`, `abandon`,
     `dead_letter`, a delivery count, and a lock expiry driven by an injected clock;
   - `RecordingAlertHttp` routes URLs to statuses.
   Register each one.
3. **Convert, file by file, in this order.** Stop when the lane's budget is spent, and list
   what remains in the commit body. The ratchet makes the remainder visible and keeps it from
   growing:
   1. `test/servicebus/test_consumer_wrapper.py` and `test_consumer_wrapper_fill.py`;
   2. `test_transports_cloud_fill.py` and `test_transports_sql_blob_fill.py`;
   3. `test_alerts_dispatcher_fill.py` and `test_locks_masking_webhook_fill.py`;
   4. `test/v3/test_transport_contracts.py`. Make it a real contract suite: each transport
      over its in-memory fake always, and over the real SDK only under `integration`
      (Azurite, a local emulator, credentials).
4. Lower the baseline for every converted file.

## Where to change
- The transport, service bus and alert modules under `vibey_bootstrap/` (constructor keywords with production defaults, plus interfaces).
- `test/fakes/*`, the converted test modules, `test/fakes/test_port_parity.py`, `test/patching_baseline.json`.

## Acceptance criteria
- [ ] The four groups in behaviour 3 are converted, or the commit body lists precisely which files remain and why.
- [ ] The package suite passes at its coverage level with no emulator running.
- [ ] `test/v3/test_transport_contracts.py` runs every transport over its fake in the default run.

## Tests to write first (TDD)
- `test/fakes/test_bus_fakes.py`:
  - `test_service_bus_peek_lock_complete_abandon_dead_letter`
  - `test_service_bus_lock_expiry_redelivers_and_counts`
- `test/fakes/test_storage_fakes.py`:
  - `test_blob_service_duplicate_container_raises`
  - `test_event_hub_enforces_batch_limit`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/bootstrap && pytest test/ --cov=vibey_bootstrap --cov-report=term
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `vibey_bootstrap.amqp` (R04, T21 own it; its `InMemoryAmqpClient` is registered here only if already present).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-bootstrap-2`, **`rmq-r04-bootstrap-amqp`**. R04 adds the
  in-package AMQP double and the extra this lane must not collide with.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected root tests, and R04's and T21's AMQP tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).
  - This is the largest tenant lane. The ordered list in behaviour 3 is its split, and a follow-up lane can finish the list from the baseline.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
