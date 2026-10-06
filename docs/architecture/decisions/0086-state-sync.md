# 0086 — `vibey state`: the whole database, sealed on a branch, kept in sync both ways

**Status:** accepted · **Date:** 2026-10-06 · **Cites:** sub-doctrines 10.f, 10.g, 10.h, 12.c, 12.d and 12.h · **Related:** ADR-0002, ADR-0003, ADR-0016, ADR-0048, ADR-0055, ADR-0057, ADR-0068, ADR-0085 · **Evidence:** `vibey.domain.state_sync`, `vibey.application.state_sync`, `vibey.infrastructure.state`, `vibey.cli.state`, migration `0022_state_sync.sql`, `scripts/vibey_remote.py`

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record; `docs/llms.txt`
regenerated from that nav; the continuation prompts re-rendered. All are in the change
that carries this record.

## Context

The operator asked that the local database be uploaded to GitHub and kept there: always in
sync, in both directions, encrypted, in this repository, with every step idempotent.

vibey's state is one PostgreSQL database (ADR-0002): the ledger (ADR-0003), the queue, the
gates and the rest. Today it lives on one machine. A disk that dies takes it, and a second
machine, or a GitHub-hosted runner running `vibey -w` (ADR-0085), starts from an empty
queue. Work in progress is meant to outlive the machine (10.h, ADR-0057); the database is
the one piece of it that does not.

Three things make this harder than a backup. The ledger is append-only by the database
(ADR-0055), and its hash chain runs over `seq`, so two databases that each appended events
cannot be reconciled by renumbering. Both ends change while a sync runs: a worker writes
here, and another machine or a runner pushes there. And this repository is public, so
whatever is on the branch can be read by anyone.

## Decision

1. **A snapshot is every synced row, read in one view.** `PostgresStateStore.snapshot` reads
   every table in `TABLES` (`vibey.domain.state_sync`) inside one `REPEATABLE READ`,
   read-only transaction, with `TIME ZONE 'UTC'` and `extra_float_digits = 1`. Each row is
   `to_jsonb(row)` minus its generated columns, keyed by its primary key. The snapshot also
   carries the migrations the database has applied. Three tables are never synced
   (`NOT_SYNCED`): `schema_migration`, which the migrator owns; `event_seq`, which is derived
   from the ledger it numbers; and `state_sync`, the sync's own watermark.
2. **One canonical encoding.** `CanonicalJson` sorts keys, writes no spaces, escapes to ASCII
   and keeps every number exact: a fraction is read as a `Decimal` and written back as the
   same digits, never through a `float`. Two equal snapshots are equal bytes, so whether
   anything changed is a comparison of plaintexts.
3. **A three-way merge against the last-synced commit.** For each branch, the
   `state_sync` table keeps the commit this database last agreed with (`base_commit`). The
   merge reads that commit's snapshot as the base. A row only one end changed takes that
   end's change, and a row both ends changed to the same thing takes it. A row both ends
   changed differently is settled by its table's rule:
   - `newest`, by a declared timestamp column. A missing time is the oldest. Equal times,
     or a time with an offset against one without, cannot be ordered, and are a conflict.
     A row deleted at one end and changed at the other is a conflict.
   - `mine` keeps this database's row, deletion included.
   - `theirs` takes the branch's row, deletion included.
   - `refuse` makes it a conflict.

   The declared defaults are `newest` for `project`, `job` and `triaged_ticket` (by
   `updated_at`) and `human_gate` (by `answered_at`); `mine` for `engine_health` and
   `rotation_cursor`, which describe this machine's engines; and `refuse` for
   `job_dependency`, `work_item`, `open_item`, `handoff`, `artifact` and `budget_ledger`.
   `VIBEY_STATE_CONFLICTS` overrides them per table (12.c, 12.h).
4. **The ledger is never resolved by a rule.** `event` is append-only, and no override can
   give it one: `TableSpec` refuses it. A ledger row that was changed or removed, or two
   different events at the same `(project_id, seq)`, is reported as divergence. With any
   conflict, in any table, the sync writes nothing at either end and names every conflicting
   row (10.f). Two databases that migrated differently are refused too (`SchemaMismatch`):
   the one behind runs `vibey migrate` first.
5. **Sealed with AES-256-GCM.** `AesGcmStateCipher` gzips the canonical document
   (`mtime=0`) and encrypts it under a 32-byte key with a fresh 96-bit nonce. The magic
   `VBYSTAT1` is the associated data. The sealed file is the magic, the nonce, then the
   ciphertext and tag. GCM authenticates, so a state sealed under another key, or changed
   by one bit, does not open, and is reported as unreadable rather than read as an empty or
   partial state. A fresh nonce makes the same rows sealed twice into different bytes, so
   the sync compares what it opens, never what it pushes.
6. **The branch is moved by compare-and-swap.** `GhStateRemote` keeps one file
   (`state.vibey`) on one branch (`vibey-state`), through `gh api` and git's data API, with
   no checkout. A push creates the blob, a one-file tree and a commit whose parent is the
   head the merge read. It then moves the ref with `force: false`, so GitHub moves it only
   if it is still at that head. A 409 or 422 on the ref is `RemoteMoved`. A refused blob,
   tree or commit is a failure, not a race. `gh` runs with an environment built from its
   own declaration, so the database DSN and the key never reach it.
7. **The apply is guarded.** `PostgresStateStore.apply` runs in one transaction under a
   10-second `lock_timeout`. It takes `SHARE ROW EXCLUSIVE` on every table it touches, so
   writers wait briefly and readers never do. Then it checks every changed row is still
   what the snapshot read. If one is not, a worker wrote it since, and the whole apply is
   rolled back as `StateMoved`; a deadlock or a lock timeout is `StateMoved` as well. Rows
   are written parents first and deleted children first. A column that references its own
   table (`open_item.superseded_by`) is written once every row is in. The ledger's next
   `seq` per project and every declared sequence (`job_bump_seq`,
   `triaged_ticket_bump_seq`) are advanced past what was written, never back. Every value
   travels as a bound parameter; table and column names come only from `TABLES` and the
   catalog.
8. **One cycle, retried.** `StateSyncService.sync` reads the branch head and the base,
   merges, stops on any conflict, applies the merge here, records the head as the base,
   and pushes if the merge differs from the head, recording the pushed commit as the base.
   `StateMoved` or `RemoteMoved` starts the cycle again, up to `ATTEMPTS` times (5,
   `VIBEY_STATE_ATTEMPTS`). After that it gives up and says so. The base is recorded before
   the push, so a retried merge stays three-way and never mistakes what was just pulled for
   a change made here.
9. **Idempotent, by construction.** Each step writes only what differs. The apply is
   skipped when the diff is empty. The push is skipped when the merge's plaintext equals the
   head's. The base is rewritten only when the commit changed. So a second sync straight
   after a first pulls nothing, pushes nothing and writes nothing. A cycle that died
   anywhere is completed by the next: the watermark moves only after what it marks is
   committed (10.g, ADR-0048). A base the branch no longer reaches, or a branch that is gone
   while a base is recorded, is refused by name rather than guessed past.
10. **The key is made once and never replaced.** `StateKeyStore` looks for it in
    `VIBEY_STATE_KEY`, then the macOS keychain (service `dev.vibey.state`, account
    `VIBEY_STATE_REPOSITORY` or `default`), then `VIBEY_STATE_KEY_FILE`, which it refuses
    while its mode grants its group or others anything. `vibey state key --new` writes to the keychain
    through `security -i` on stdin, so the key is never on an argument vector another
    user's `ps` could read. Elsewhere it creates the file with `O_EXCL` and mode 0600. It
    refuses while a key exists anywhere, because replacing a key makes every state sealed
    under it unreadable. `vibey state key --show` prints the key alone, for another machine
    or for the repository's `VIBEY_STATE_KEY` secret.
11. **Its own DSN and its own environment file.** The sync writes every synced table and
    its watermark, more than the application role may (ADR-0055). It connects through
    `VIBEY_STATE_PG_URL`, falling back to `VIBEY_PG_URL`. The application role is never
    granted `state_sync`. Under the supervisor the sync is an opt-in third service,
    `state-sync` (`[supervisor] state_sync = true`). It runs
    `vibey state sync --every <state_sync_interval_seconds>` through
    `vibey supervisor exec`, with its own environment file, `state-sync.env`, created from a
    commented template readable by its owner alone. The worker's file never holds that DSN.
12. **Never from the hub, never on a public runner.** `state_sync` is in
    `NEVER_FROM_THE_HUB`, and `vibey state` is in `RESERVED_COMMANDS`. The hub routes none
    of it, and refuses it as a command sent to the workflows. On the runner (ADR-0085), the
    state is restored only on a **private** repository that holds a `VIBEY_STATE_KEY`
    secret and declares no database. The runner's empty database is filled first with
    `vibey state sync --no-push`, and exported, sealed, after the command. A separate
    job, `sync-back` in `vibey-remote.yml` (`scripts/vibey_remote.py sync-back`), the only
    one with `contents: write`, imports that export into a fresh
    database and runs `vibey state sync` to push the run's changes back. The command itself
    never holds the key, the owner's DSN or a token. On a public repository the state is
    never restored, because anyone can read its runs' logs and artifacts. This is the same
    rule ADR-0085 applies to a declared database, and the run says so.

## Consequences

- Any machine with the key, the repository and `gh` can bring its database level with the
  others with one command, and `vibey supervisor` can keep it level unattended. A disk that
  dies loses at most what changed since the last sync.
- On this public repository the `vibey-state` branch is public. Its contents are
  ciphertext, and confidentiality rests on the key alone. The branch's commit times, its
  number of commits and the size of each sealed file are visible to anyone. The commit
  message is fixed and says nothing about the rows.
- Losing the key loses the branch's state: nothing can open it. Every machine and the
  repository's secret hold the same key, so it is lost only when every copy is.
- A branch that was rewritten or deleted strands the recorded base. The sync refuses until
  `vibey state forget` drops it, after which the next sync merges the two ends as a first
  sync would, against no base.
- A conflict needs a person. The sync names every conflicting row and changes nothing. Ledger
  divergence has no automatic answer, because neither side's events can be renumbered.
  Silence is not consent (12.d), so an unattended `state-sync` service reports the same
  conflict on every round until someone settles it, by changing a row or by declaring a
  rule in `VIBEY_STATE_CONFLICTS`.
- The sync's DSN can write every synced table. It is kept out of the worker's environment
  and off the hub, but it is a wider credential than the application role's, and it is the
  operator's to guard.
- Every sync that changed something is one commit on the branch, and its history is the
  state's history. The branch grows with every change, as a sequence of whole sealed
  snapshots.

## Alternatives considered

- **`pg_dump` to a release asset.** A dump is one-way: it restores into an empty database
  and cannot merge with one that also changed. It is not stable bytes either, so whether
  anything changed means restoring it. A release asset has no compare-and-swap, so two
  machines uploading at once lose one another's work, silently.
- **A separate private repository.** It would hide the ciphertext and its metadata, but the
  operator asked for this repository. It would also add a second repository, a second
  token and a second set of permissions to keep in step. Encryption carries the
  confidentiality instead, and a repository that wants it can point `VIBEY_STATE_REPOSITORY`
  at a private one.
- **Git LFS.** LFS moves large files, but the snapshot is small once gzipped. It adds a
  storage quota and a client dependency, and LFS objects have no compare-and-swap of their
  own: the ref update would still be the only guard.
- **One-way upload.** A backup of one machine would not let a second machine, or a runner,
  add work that comes back. The operator asked for two-way. With one machine, `vibey state
  sync` already behaves as an upload, and `--no-push` gives the download alone.
