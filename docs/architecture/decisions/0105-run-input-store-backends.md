# 0105 — Where run inputs are stored: your state folder by default, or a SeaweedFS bucket you name

**Status:** proposed · **Date:** 2026-11-23 · **Cites:** SD-01 v1.0 §4; sub-doctrines 8.b, 10.e, 10.g, 12.c · **Related:** ADR-0016, ADR-0017, ADR-0018, ADR-0104

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

ADR-0104 put each project's run inputs in one place: `inputs/<project id>/` under the person's
own state folder (`UserStateFolder.inputs()`), with the bytes stored once by SHA-256 and an
`index.jsonl` of rows. The SP-LOOPS design said v1 is one machine and that inputs do not follow
a job to another machine (Decisions 5 and 6), and `RunInputsService`'s docstring says the same.

Two things came out of running that design:

- **A worker can see an empty store and run without inputs, silently** (the Phase 3 report's
  N7 limit). The store's location depends on `XDG_STATE_HOME`, which can differ between the
  person's shell and a systemd user session. The same class of failure has other causes too:
  `[inputs]` is read from the person's own `vibey.toml`, located through `XDG_CONFIG_HOME`, so a
  worker with another config folder reads no `[inputs]`; a wrong bucket or prefix does the same.
- **The operator asked for a configurable store location with a `local` or `seaweedfs` backend**
  (decision D2 of 2026-11-23), so several workers can read one project's inputs.

The evidence on the canon, searched on 2026-11-23: sub-doctrine 8.b enumerates **Files →
self-hosted, free Nextcloud** and **blob storage → Garage (the S3 protocol)**. Both exist in
code: `[files]` with `NextcloudFilesAdapter` and `[blob]` with `GarageBlobAdapter`, whose S3
SigV4 signer is the family's only one. The repository named SeaweedFS nowhere. A SeaweedFS
input store is a third storage surface beside the two, so it touches 8.b (the enumerated
sovereign defaults) and 12.c (generic and configurable).

## Operator rulings (approved 2026-11-23)

The SP-LOOPS Phase 3c plan (`docs/superpowers/plans/2026-11-23-sp-loops-phase3c-store-handoff-doctor.md`)
surfaced five rulings. The operator approved the recommended option for each:

- **OR-1 (scope).** `"seaweedfs"` is an opt-in store; `local` stays the default. This record
  amends spec Decisions 5 and 6 for store reads only: a BUILD run may read its inputs over the
  network from an endpoint the person configured. Nothing else in the one-machine scope
  changes. The considered alternative, a SeaweedFS store on the same machine only, would not
  let two workers share a project's inputs, which is what D2 asked for.
- **OR-2 (canon).** SeaweedFS is a **sibling** of Garage for object storage, as OpenProject is
  beside Plane, and Garage stays the blob default. Rejected: SeaweedFS replacing Garage as the
  blob default (nothing measured says Garage fails), and a generic `store = "s3"` value
  (rejected for now only because SeaweedFS is the one target the operator named; the adapter
  speaks plain S3, so a later generic value is a rename, not a rewrite).
- **OR-3 (authentication).** **S3 SigV4** against SeaweedFS's S3 gateway, signed by the
  signer the family already ships (extracted from `GarageBlobAdapter`, not written again:
  10.e). The alternative was the filer HTTP API, whose native append would suit `index.jsonl`;
  as understood without a real SeaweedFS to check, the filer authenticates with a JWT signed by
  a shared key and has no basic auth, so it would need a proxy in front of it.
- **OR-4** (the wheel's marketplace) and **OR-5** (the handoff input pin is a handoff check,
  not gate rule R11, until a `WARN` gate mode exists) belong to the same plan and are recorded
  in its ledger; they are not storage decisions.

## Decision

1. **`[inputs] store` selects the backend: `"local"` (the default) or `"seaweedfs"`.** The
   keys sit in the same `[inputs]` table as the limits, parsed by the same
   `RunInputsSettings.from_table`, so one known-key set covers the table, and a project's
   `[inputs]` is still never applied. `local` takes an optional absolute `store_dir`, which
   takes the state-folder variable out of the local case; `seaweedfs` needs `endpoint` and
   `bucket` and takes `prefix` (`vibey/inputs`), `region` (`us-east-1`), `access_key_env`
   (`VIBEY_INPUTS_ACCESS_KEY`), `secret_key_env` (`VIBEY_INPUTS_SECRET_KEY`) and
   `timeout_seconds` (10). Every default is the settings value's, never a constant in the code
   that reads it (ADR-0018). A key that would do nothing for the chosen backend is refused, so
   a typo cannot hide.
2. **`[inputs]` holds no credential.** A key named `access_key`, `secret_key`, `password` or
   `token` is refused without echoing its value. The two credentials come only from the
   environment variables `[inputs]` names, and they never appear in a log, an error, a URL or
   `vibey doctor` output. Plain `http` is accepted only for a loopback host.
3. **The SeaweedFS store speaks the S3 API over `httpx`, path-style.** Objects are
   `<prefix>/<project id>/objects/<2 hex>/<digest>`; S3 has no append, so each index row is its
   own object, `<prefix>/<project id>/index/<ns:020d>-<uuid>.json`, and ListObjectsV2 key
   order is add order. The bucket is never created (least authority: the credentials may be
   scoped to one bucket). A listing is paged until it is no longer truncated, and a listing body
   over 1 MiB or carrying a DOCTYPE or ENTITY is refused before it is parsed (10.g: no limit or
   cross-check runs over an unknown subset). Bytes whose digest or length does not match their
   row are refused. Requests go only to the endpoint's host, never through a redirect. A store
   that answers nothing, times out or answers 5xx raises the new retryable
   `InputStoreUnavailable`; a refused credential is an `InputStoreError` naming the variables.
4. **The ledger, not the store, is the authority on which inputs exist.** When a BUILD run
   starts, every input the ledger records as added for the project must be in the store the run
   reads from, or the run fails before the engine starts, and the failure names the resolved
   store. Rows in the store that the ledger never recorded are withheld and counted, so a third
   party who can write a shared bucket cannot plant an input into a project's runs. This closes
   the N7 limit for both backends.
   Fix round 1 (review I2-I4) made the match exact and the reading lazy: rows are matched to
   recorded adds one to one, in ledger order, on digest, kind, size and the SHA-256 of the name
   (the add event's `name_digest`; the ledger still holds no name), so a planted older version of
   a file, a re-kinded paste or a planted size is withheld rather than given. An add writes the
   object, then the record, then the row; a row that fails after its record is cancelled by a
   `vibey_run_input_failed` correction, and the same bytes added again fulfil an add left without
   a row. A project nothing was added to reads no store, and the worker composes its store on
   first use, so a broken `[inputs]` table, or credential variables a service manager does not
   pass, fail only the runs that have inputs to give.
5. **`vibey doctor` says which store is in force, where its configuration came from, and
   whether it answers** (a `run-inputs` section). Doctor is a person's explicit act, so its one
   network probe is not a run fetching on its own.
6. **Every store call runs off the worker's event loop** (`asyncio.to_thread`), so a remote
   store never stalls the lease heartbeat.

## The 8.b amendment, drafted for ratification

This record does not change the canon. Under Article II.3 the operator ratifies a sub-doctrine
by merge, and nothing here is self-ratified. The draft below is what the operator's merge of a
later change to `src/vibey_tools/gh/docs/doctrines.md` would carry, replacing the
**Configuration** bullet of 8.b:

> - **Configuration** defaults to **self-hosted Infisical**, the **cache** to
>   **Redis**, the **bus** to **RabbitMQ**, **blob storage** to **Garage** (the S3
>   protocol) and **security events** to **Wazuh**, each running in the operator's
>   own cluster. **SeaweedFS** (FOSS and self-hostable, reached through its S3
>   gateway) is a sibling sovereign option for object storage, opt-in where a surface
>   declares it — first for run inputs (`[inputs] store = "seaweedfs"`); it never
>   replaces Garage as the blob default. Their hosted equivalents are declared-only.

## Consequences

- With `store = "seaweedfs"`, a BUILD run reads its inputs over the network from an endpoint
  the person configured. That bends the global rule that a run never fetches on its own, and
  it is bounded by OR-1: only the store read, only from the endpoint the person named.
- A shared store makes a project's inputs readable by every worker holding the endpoint and
  the credentials; that is the point of D2, and the bucket's own access policy is its bound.
- `[files]` (`password`) and `[blob]` (`secret_key`) still accept credentials in `vibey.toml`,
  which contradicts Decision 2. Bringing them in line is a follow-up, not this record's change.
- Not verified while writing this record: SeaweedFS's S3 gateway behaviour (SigV4 identities,
  ListObjectsV2 continuation, path-style addressing) and the filer's authentication model.
  Every test runs against an in-memory S3 behind `httpx.MockTransport`; an operator run against
  a real `weed server -s3` is the outstanding evidence.
