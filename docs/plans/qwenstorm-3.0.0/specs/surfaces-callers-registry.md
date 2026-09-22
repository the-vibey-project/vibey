## Title
test(meta): every sovereign surface port names its production callers, or the lane that owes its first one

## Why
`issue-audit/gaps.md` K2: "vibey's operations actually use their sovereign surfaces" (8.b) — and
today none does. `surfaces-consumer-notifications` gives the messaging surface its first caller;
the other ten surfaces still have none, and nothing would notice if they stayed that way. The
fakes wave solved the same problem for fakes with a registry and a meta test that fails when a
port is unaccounted for (`specs/fakes-registry.md`). This lane does that for callers: each
surface port is either **called** by named production modules, or **pending** with the slug of
the lane that owes its first caller. A pending entry is a stated gap (10.f), not a silent one,
and a new caller that nobody listed also fails the test, so the list cannot rot. It also guards
8.f's "nothing opens a second path to a surface beside its lane": a production module outside the
composition root and the lane package may reach a surface only through its port.

## Required behaviour
1. **`tests/meta/test_surface_callers.py`** (new), data at the top of the module:
   - `CALLED: dict[str, tuple[str, ...]]`: surface → the production modules (dotted names) that
     call its port. Seeded with `"messaging": ("vibey.infrastructure.notify.matrix",)`.
   - `PENDING: dict[str, str]`: surface → the slug that owes its first caller, seeded with
     `tracker: "surfaces-consumer-tracker-work-items"`, `docs: "surfaces-consumer-docs-publish"`,
     `secrets: "surfaces-consumer-secrets-credentials"`, `files: "surfaces-consumer-files-deliveries"`,
     `email: "surfaces-consumer-notify-email"`, `sms: "surfaces-consumer-notify-sms"`,
     `configuration: "surfaces-consumer-config-store"`, `cache: "surfaces-consumer-cache"`,
     `blob: "surfaces-consumer-blob-artifacts"`, `siem: "surfaces-consumer-siem-findings"`.
   - `METHODS: dict[str, tuple[str, ...]]`: surface → the port method names from
     `vibey.domain.surface_catalogue.CATALOGUE.for_surface(...)`, computed, not typed out.
   - `EXCLUDED_PACKAGES`: the modules that may name surface methods without being callers — the
     ports (`vibey.application.interfaces`), the adapters' own packages
     (`vibey.infrastructure.{tracker,docs,secrets,files,email,sms,messaging,config_store,cache,bus,blob,siem}`),
     `vibey.infrastructure.surface_lanes`, and `vibey.bootstrap`.
2. **Tests:**
   - `test_every_surface_is_called_or_pending`: every `SurfaceName` value is in exactly one of
     `CALLED` and `PENDING`; the bus is in neither (8.f exempts it).
   - `test_pending_names_a_lane`: every value matches `^surfaces-consumer-[a-z0-9-]+$`.
   - `test_listed_callers_call_the_port`: each module in `CALLED[s]` exists and its AST has a call
     whose attribute name is one of `METHODS[s]`.
   - `test_no_unlisted_caller`: AST-walk every module under `src/vibey` not in
     `EXCLUDED_PACKAGES`; a call whose attribute name is one of a surface's **distinctive**
     method names (every method except the cache's `get`, `set` and `delete`, which are too
     common; for the cache, a call on an attribute named `cache`, such as `resources.cache.get(...)`)
     must come from a module listed in `CALLED` for that surface. The failure names the module,
     the line and the surface, and says "list it in CALLED, or reach the surface through its port".
   - `test_a_pending_surface_has_no_caller_yet`: a surface in `PENDING` has no caller by the
     scan above (so moving it to `CALLED` is required once its lane lands).
3. The module has no logic outside tests and the three data tables (a helper class for the AST
   scan is fine).

## Where to change
- New `tests/meta/test_surface_callers.py` only.

## Acceptance criteria
- [ ] The five tests pass at this commit.
- [ ] Adding `await x.send_email("a", "b", "c")` to any non-excluded module fails `test_no_unlisted_caller` naming it (check by hand, then revert).
- [ ] Deleting the `PENDING` line for `docs` fails `test_every_surface_is_called_or_pending` naming `docs` (check by hand, then restore).

## Tests to write first (TDD)
The five tests in behaviour 2.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Writing the pending callers (each is its own lane, owed to K2's epic). Production code.
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-consumer-notifications`, `surfaces-catalogue`.
- **Must keep passing unchanged:** every test in `tests/meta/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
