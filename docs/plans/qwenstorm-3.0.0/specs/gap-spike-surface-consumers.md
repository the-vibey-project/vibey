## Title
docs(adr): decide how vibey's own operations consume each sovereign surface (spike for gap K2)

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-194`) says "every operational
surface of vibey defaults to the … sovereign option". ADR-0042 built a port, an in-memory
adapter and a sovereign adapter per surface, and ADR-0043 installs the servers. But vibey itself
calls none of them: the ports are read only by `build_app` (`src/vibey/bootstrap.py:751-914`)
and by `tests/infrastructure/test_sovereign_surfaces.py`, and ADR-0047 records it as "the most
important fact in the record" (`specs/ADR-surface-lanes.md:38-46`, "Who calls them: nobody
yet"). Gap K2 lists nine consumers. The first — operator notifications through Matrix, SMTP and
Kannel — is exact now and is specified in `gap-surface-notify-config`,
`gap-surface-notify-messaging` and `gap-surface-notify-wiring`. The other eight each need design
decisions (what triggers the call, what is stored where, how a replay is made idempotent, what a
failure does), so this spike decides them in one record.

**Implementer: a large model or the operator (design, not code); the storm runner skips
gap-spike-\*.** The deliverable is the draft ADR
`STORM/specs/ADR-gap-surface-consumers.md`, in the shape
of `specs/ADR-two-loops.md` and `specs/ADR-surface-lanes.md`. Evidence is read from the
integration clone at `d3b4a388` (or later, stated); never from `/Users/adam/git/vibey`.

## Required behaviour
The ADR must decide, for each consumer: the trigger (which phase, handler or command calls
the port, at which `file:line`), the port operations used, the data mapped onto them, the
idempotency key each create or send passes once ADR-0047 lanes S04–S06 add `idempotency_key`,
where any mapping (ticket id, page id, locator) persists (through the `orm-*` seams, never raw
SQL), what a failure does to the job (never blocks it: non-negotiable 1), the config keys with
defaults and `VIBEY_*` overrides (12.c), what the in-memory adapter does in an unconfigured
deployment, and how the consumer behaves under ADR-0047's `queue` transport. Every consumer is
written against the port only, so it runs unchanged under `direct` and `queue`.

1. **Secrets from OpenBao (`SecretsPort`).** Which credentials move: the paid engines' keys
   (today inherited from the process environment, `src/vibey/infrastructure/engines/loop_process_adapter.py:162`,
   `:184`, `:385`), forge tokens (vibey-gh names an environment variable, never the value,
   `src/vibey_tools/gh/vibey_gh/config.py:291`, `:313`), and which cannot (the OpenBao token
   itself). Precedence between environment and `SecretsPort`; when values are read (start, per
   job); that they are never cached in the cache surface; what an unreachable OpenBao does
   (doctrine 10: fail loudly to a person, `doctrines.md:366-384`); redaction (7.c, `:82-91`).
   Weigh ADR-0047's security note that `get_secret` answers cross the broker
   (`specs/ADR-surface-lanes.md`, *Security impact*).
2. **Work items mirrored to Plane (`IssueTrackerPort`).** Which records become tickets
   (`WorkItem`, `src/vibey/domain/plan.py:41`; human gates), when, and whether status flows
   back. The port has only `create_ticket` and `get_ticket_status`
   (`src/vibey/application/interfaces/tracker.py:10-16`): name any verb it must gain. Where
   the item-to-ticket map is stored.
3. **Accepted specs and ADRs published to BookStack (`DocsPort`).** The trigger is design
   acceptance (`src/vibey/application/design_acceptance.py:58-87`); decide the page content,
   the page-id map, re-acceptance as `update_page`, and whether this repository's own ADRs are
   in scope. BookStack has no idempotency key (ADR-0047 §3 classes `create_page` as guarded).
4. **Visual media, review artifacts and handoff briefs in Garage (`BlobPort`).** Today they are
   files: `FileVisualInventoryRepository` (`src/vibey/infrastructure/db/visual_inventory_repository.py:27`),
   `FileReviewArtifactWriter` (`src/vibey/infrastructure/review_artifact_writer.py:13-25`),
   `FileDesignSpecRepository` (`src/vibey/infrastructure/db/design_spec_repository.py:21`), and the
   handoff ledger written into the receiving worktree
   (`src/vibey/application/handoff_orchestration.py:30`; CLAUDE.md: "the full ledger is always
   written to disk inside the receiving worktree"). Decide copy versus move, the bucket and key
   scheme, the locator recorded in the ledger, and what happens above ADR-0047's
   `inline_max_bytes` (8 MiB).
5. **Security findings to Wazuh (`SiemPort`).** Finding on reading: the three guards are not
   called by any production code. `PromptShield` (`src/vibey/domain/prompt_shield.py:31-60`),
   `scan_command` / `CommandSecurityPolicy` (`src/vibey/domain/command_guard.py:93-113`) and
   `MutationScope` (`src/vibey/domain/scope_guard.py:22-103`) are referenced only by
   `tests/domain/test_prompt_shield.py`, `test_command_guard.py` and `test_scope_guard.py`.
   Decide first where each guard is enforced (for example the gate runner's argv,
   `src/vibey/infrastructure/build/gate_runner.py:118-125`; untrusted issue and review text;
   worktree writes), whether a block fails the step or only reports, and then the audit
   document schema sent to `send_event` and its index (`[siem] index`, default `vibey-audit`,
   `src/vibey/domain/config.py:308-315`).
6. **Project configuration through Infisical (`ConfigStorePort`).** What moves: the runtime
   tables copied into the project's stored config at `vibey new`
   (`src/vibey/infrastructure/config_loader.py:103-123`)? Only non-secret keys? The key scheme,
   and how `vibey.toml` (12.c: declared in the repository) and Infisical relate without two
   sources of truth.
7. **A first real cache consumer (`CachePort`).** Choose it from ADR-0047 §10's list (values
   costing well over the lane's p99 of about 5 ms, or shared between processes: Plane,
   BookStack or Infisical answers; model-catalogue probes; rendered artefacts), the key
   prefix, the TTL, and the coherence precondition (vibey is the only writer of its keys).
   Not the process-local help-text memo (`loop_process_adapter.py:68`), which ADR-0047 keeps local.
8. **Delivered files in Nextcloud (`FilesPort`).** Define "delivered files" (the build's
   release artefacts? the DONE project's exported bundle?), the trigger (DONE, local or
   deployed), the remote path scheme, and the returned locator's use.
9. **Notifications, completed.** Record the three specified lanes as decided, and name the
   follow-ups: pass an `idempotency_key` derived from the event after S04–S06; teach the
   failure classifiers (`src/vibey/application/worker.py:98-128`,
   `src/vibey/infrastructure/db/project_repository.py:157-171`) the new result keys; record
   deliveries in the ledger (7.c) and measure them (8.g, `gap-measure-port`).

Across all nine, the ADR also decides: which consumer lands first after notifications; the
ledger events each writes (7.c: append-only, redactions recorded); the measurements each
records once `gap-measure-port` exists (8.g, `doctrines.md:316-324`); and how each passes
`vibey doctor` or `vibey surface ping` evidence that it reached a real server rather than the
in-memory adapter (10.f, `:419`).

## Where to change
Nothing in the repository. Write only
`STORM/specs/ADR-gap-surface-consumers.md`.

Required ADR sections, in order: the header line (**Status:** proposed · **Date** ·
**Cites:** 8.b, 8.f, 8.g, 7.c, 9.b, 10.e, 10.f, 12.c, SD-01 §1 · **Related:** ADR-0042,
ADR-0043, ADR-0044, ADR-0047, the notify lanes · **Evidence:** the commit read) and an
**Owes:** line; `## Context`; `## Decision` (one numbered subsection per consumer above, each
ending with its child lanes); `## Child lanes` (a table: slug, one-line scope, file(s),
dependencies); `## How each non-negotiable still holds`; `## Security impact`; `## Migration`;
`## Consequences`; `## Alternatives rejected`; `## Verification owed at implementation`.

Child lanes the ADR must name (each sized for one source file plus its interface and one test
file; split `-1`, `-2` where needed): `gap-surface-secrets-credentials`,
`gap-surface-tracker-mirror`, `gap-surface-docs-publish`, `gap-surface-blob-artifacts`,
`gap-guards-wired` (the three guards enforced in production; prerequisite of the next),
`gap-surface-siem-findings`, `gap-surface-config-store`, `gap-surface-cache-consumer`,
`gap-surface-files-delivery`, `gap-surface-notify-idempotency`,
`gap-surface-notify-failure-classifier`, `gap-surface-notify-ledger`. Any lane that persists
depends on the relevant `orm-*` lane; any lane that measures depends on `gap-measure-port`.

## Acceptance criteria
- [ ] The ADR file exists and has every required section.
- [ ] Each of the nine consumers has a trigger with `file:line`, its port operations, its
      idempotency key, its persistence (or "none"), its failure behaviour, its config keys and
      defaults, and its in-memory and `queue` behaviour.
- [ ] Every `file:line` cited resolves at the commit the header names.
- [ ] The guards finding (behaviour 5) is stated with its evidence, and `gap-guards-wired` is
      ordered before `gap-surface-siem-findings`.
- [ ] Every operator decision the ADR needs is listed under *Owes*, one line each.

## Tests to write first (TDD)
None: this is a design lane. Its tests are the checks below and a reviewer's reading.

## Checks the lane must run (all must pass)
    F=STORM/specs/ADR-gap-surface-consumers.md
    test -f "$F"
    for s in "## Context" "## Decision" "## Child lanes" "## How each non-negotiable still holds" "## Security impact" "## Migration" "## Consequences" "## Alternatives rejected" "## Verification owed at implementation"; do grep -qx "$s" "$F" || echo "MISSING: $s"; done
    grep -c "gap-surface-\|gap-guards-wired" "$F"
    cd STORM/integration && git log -1 --format=%H

## Out of scope
- Code of any kind; the three notification lanes (already specified); ADR-0047's lanes S01–S34
  (the transport); relays to paid platforms (`gap-spike-relay`).
- Filing issues, and CHANGELOG.md, docs/, the repository's ADR directory, CLAUDE.md, AGENTS.md,
  GEMINI.md and skill trees (the docs wave files the ADR once the operator accepts it).

Commit as `docs(adr): record how vibey consumes its sovereign surfaces` only if the operator
moves the draft into the repository; otherwise nothing is committed. Do not push.

## Lane card
- **Depends on:** none (it cites the notify lanes as decided).
- **Implementer:** a large model or the operator; the storm runner skips `gap-spike-*`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
