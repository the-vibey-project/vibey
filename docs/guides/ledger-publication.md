---
description: What `vibey ledger export` publishes from a project's ledger, what it always withholds, and how to check the counts before you commit the shard.
---

# What gets published from your ledger, and how to check it

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `vibey ledger export` never publishes your ledger. It writes a
> *projection* of it, a shard: the decisions, questions, answers, assumptions, findings and phase
> moves, with local paths and email addresses taken out. Engine chatter, spend, gate answers,
> devices, web searches and every unnamed kind are withheld, and everything left out is counted
> by reason. Export, read the counts, then commit. It takes a minute.

**See what a published ledger looks like first:** the [ledger explorer](../explorer/index.md)
reads exactly what this page describes, and shows what was left out beside what was kept.

This page is for the operator deciding whether to publish a project's ledger. The rule it
serves is [sub-doctrine 7.a, the searchable ledger](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/doctrines.md):
anyone, no matter who, can search the ledger, the full ledger where a deployment holds it, or the
shard a repository holds. The commands are in the [CLI reference](../reference/cli.md#vibey-ledger).

## The lesson

Daniel had the export command typed and his finger over the Enter key when he stopped.

**Daniel:** Professor, the ledger has every prompt I sent and every answer the model wrote. If I
publish it, does all that go out?

**Professor Feynman:** No. Think of a ship's log and the notice the captain pins on the harbour
board. The log has everything: the weather, the crew's grumbles, the cook's accounts. The notice
says where the ship went, what was decided and why. Nobody pins the log itself on the board.

**Daniel:** So vibey writes a notice from the log.

**Professor Feynman:** Yes, and it does it by a strict list. A kind of event goes on the notice
only if the list names it, and then only the fields the list names. Anything the list does not
mention stays in the log. That is called default-deny.

**Daniel:** How would I know what it left out? A notice with gaps looks the same as a notice with
nothing missing.

**Professor Feynman:** Good, that is the gap in my picture. vibey counts. Every event it left out
is counted by reason, every field it removed is counted, every path and email address it
replaced is counted, and those counts travel with the shard. Nothing is dropped without a number
saying so.

**Daniel:** And if someone edits the notice after I pin it?

**Professor Feynman:** Each published record carries a digest of exactly what was published, so
any reader can check it. And the shard carries your ledger's chain head, worked out over every
event, the withheld ones too. Anyone holding the full log can recompute it and confirm the notice
came from that log. That is where the harbour picture stops: a pinned notice cannot prove which
log it was copied from, and this one can.

## Do it

Checked with vibey-engine 0.4.0 on macOS. The export needs the database; the site build does not.

1. Export a project's shard. Replace `PROJECT_ID` with the id `vibey projects` prints.

   ```bash
   vibey ledger export PROJECT_ID --out ledger/greeter.jsonl
   ```

   You should see four lines: `exported N of M ledger event(s) of project ... to
   ledger/greeter.jsonl`, the withheld counts by reason, what was stripped from the published
   records, and `chain head ... at seq N, verified` (or `... published unverified` when the
   ledger's chain walk found a disagreement). The file is replaced if it exists, and its folder is
   created if it does not.

2. Read the counts before you commit. They have this shape; these two lines are what the greeter
   shard committed in this repository reports:

   ```text
   935 events withheld by policy (3 untrusted provenance, 676 engine chatter, 256 kind not allowlisted)
   from published records: 70 field(s) withheld, 22 absolute path(s) and 0 email address(es) stripped, 0 record(s) with a credential redacted
   ```

3. Commit the shard like any other file.

   ```bash
   git add ledger/greeter.jsonl && git commit -m "docs(ledger): publish the greeter shard"
   ```

4. Build the static JSON site from the shard. This needs no database, so it can run in the job
   that builds the documentation.

   ```bash
   vibey ledger site --from docs/explorer/data/greeter/shard.jsonl --out site/ledger --json-only
   ```

   You should see, for the greeter shard committed in this repository:

   ```text
   built the JSON surface of project greeter (26f89c38-c86b-4ddf-be75-c579a118e40e) in site/ledger: 174 record document(s), an index and a manifest
   ```

   followed by the two count lines above. `--json-only` is required until the human-first record
   pages are built; without it the command refuses and says so.

## Daniel's teach-back

**Daniel:** The export is a notice, not the log. An event kind is published only if the
allowlist names it, and only the named fields; everything else is withheld, and so is anything an
engine said, anything that came from outside, and where the project lives on my disk. Paths and
email addresses inside what is kept are replaced with `[path]` and `[email]`. Every omission is
counted, and the chain head lets someone with the full ledger prove the shard came from it.

**Professor Feynman:** That is it. One thing to add: answers you typed in the design interview
are published as you typed them, less paths and addresses. If an answer should stay private,
do not export.

## The words on this page

- **The ledger** is the append-only record of everything that happened to a project: every
  question, answer, decision, finding, phase move, and every turn an engine took. It lives in
  PostgreSQL and is never published directly.
- **A shard** is the file `vibey ledger export` writes: one header line, then one published record
  per line (JSON Lines). It is the part of the ledger a repository holds.
- **The publication policy** decides, event by event and field by field, what goes into a shard.
  It is *default-deny*: anything it does not name is withheld.
- **Withheld** means left out of the shard and counted. **Stripped** means replaced inside a
  published string by a token (`[path]`, `[email]`, `[REDACTED]`).

## What is published

An event is published only when its kind is on the allowlist, and then only the fields listed for
that kind (`DEFAULT_ALLOWLIST` in
[`domain/publication_policy.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/publication_policy.py)):

| Kind | Fields kept |
|---|---|
| `PhaseTransitioned` | `from`, `to`, `cycle`, `guard` |
| `DecisionRecorded` | `decision_id`, `decision`, `title`, `choice`, `rationale`, `alternatives`, `supersedes`, `next_phase`, `work_item_id`, `independent_review` |
| `QuestionAsked` | `item_id`, `question_id`, `text`, `default`, `blocking`, `stage`, `cycle` |
| `StageSettled` | `stage`, `cycle` |
| `AnswerGiven` | `item_id`, `question_id`, `answer` |
| `AssumptionStated` | `item_id`, `assumption_id`, `text`, `question` |
| `FindingRaised` | `finding_id`, `severity`, `ambiguity`, `text`, `automated` |
| `FindingResolved` | `finding_id`, `resolution` |
| `ArtifactProduced` | `artifact_id`, `artifact_type`, `title`, `cycle` |
| `ResearchGapRecorded` | `topic`, `cycle` (the reason is withheld: it can name a directory on your machine) |
| `VerdictRendered` | `complete`, `success`, `remaining_work` |
| `VisualDesign*` and `Deployment*` choices | `choice` |
| `PublishCompleted` | `kind`, `draft`, `visibility` (the URL and branch are withheld: a private repository's address is yours to share) |
| `PublishSkipped` | `reason` |
| `DeliveryEstimateRecorded` | `schema`, `recorded_at`, `source_fingerprint`, `history`, `time`, `billing`, `materials`, `track_record`, `assumptions`, `problems` |

Every other field of those events is withheld. Every event keeps its envelope (id, seq, cycle,
phase, kind, engine, job, causation and correlation ids, provenance, and time) because that is what
makes a record findable and places it in the arc of the work.

Answers you gave during the design interview are published as you typed them, less paths and
addresses. If an answer holds something that should not be public, do not export, because the
policy cannot yet be narrowed by configuration (see [Widening or narrowing](#widening-or-narrowing)).

## What is withheld

- **Engine chatter, always.** Prompts, model output and tool calls (`TurnRequested`,
  `TurnCompleted`, `ToolInvoked`), the kinds every engine's traffic lands on, are withheld whole,
  whatever the allowlist says.
- **Anything from outside.** An event with `untrusted` provenance carries text vibey did not
  write, such as a web page read during research or an issue body, and is withheld whole, so the
  site never re-serves a stranger's words under your project's name.
- **Every kind not on the list.** The policy names each kind it withholds (`WITHHELD_KINDS`), and
  `tests/domain/test_publication_policy.py` fails when a kind is on no list, or on two, so a new
  kind is never published or withheld by oversight. Today the list is:
  - `SessionSeeded` (seed prompts), `TranscriptRecorded` (turn text) and `FileEdited` (diffs);
  - `CapacityRejected`, `SavePointCreated` and the handoff kinds `HandoffInitiated` and
    `HandoffAccepted` (your provider accounts, repository and engine rotation);
  - `BudgetSpent` (your spend) and `BudgetCapChanged` (the caps you set with `vibey budget`, and
    the account that set them);
  - the ULTRA controls `UltraStarted`, `UltraStopped`, `UltraPassCompleted` and
    `UltraNoCapChanged` (they name the account and device);
  - the failover kinds `EngineFailedOver`, `EngineProbed` and `EngineHandedBack` (which engines
    and accounts ran out, and when they were probed; ADR-0070);
  - the hybrid dispatch kinds `EngineSlotWaitStarted`, `EngineOverflowSelected` and
    `EngineDispatchMeasured` (your engines, their slots and your paid cap; ADR-0079);
  - `GateAnswered` (what you answered a gate with, and the account that answered) and
    `GateWithdrawn` (a gate closed by `vibey abandon`, and the account that abandoned);
  - `GateNotified` and `GateNoticeUndeliverable` (whether, and over which of your channels, you
    were told a gate was waiting);
  - `JobFailed` (a failure's detail quotes whatever the handler raised, tool and model output
    included);
  - `HubDevicePaired` and `HubDeviceRevoked` (which devices could reach the hub, and with which
    scopes);
  - the queue's `JobPriorityBumped`, `JobPriorityUnbumped`, `JobPriorityRefused` and
    `QueueReaped`;
  - `WebSearched` and `WebFetched` (who used web search and fetch, and which hosts a fetch
    reached: your own record of what left the computer);
  - `LoopCapabilitiesSnapshotted` (digests and counts of your own plugins and MCP server
    configuration).
- **`repo_path`, never.** Where the project lives on your machine is not published under any
  rules; a rule set that tries to allow it is refused.
- **Absolute paths and email addresses** inside a published string are stripped: `/Users/…`,
  `~/…`, `C:\…`, `\\server\…` and `file://…` become `[path]`, and `name@example.com` becomes
  `[email]`. Relative paths (`src/vibey/cli/main.py`), URLs and version pins (`vibey@1.1.0`) are
  kept. A key inside a published value that is itself a path or an address is withheld with its
  value.
- **`_redactions` is published**, for every published kind, so a reader can tell that a field was
  redacted, where and why, instead of meeting a bare `[REDACTED]`. It is a list of entries, each
  with exactly two fields: `path`, the RFC 6901 JSON Pointer to what was redacted, and `class`,
  why. It **never** contains a value, a hash of a value or its length: any other field of an entry
  is withheld and counted, and so is an entry that is not a pointer and a class of the usual
  shape. Where a segment of a path is itself private (the last one of a `private-detail-key`
  entry, since a payload keyed by an email address or a phone number is redacted *because of its
  key*, or any segment that is itself an address or a path) it is published as `[private]` and
  counted as a replaced path, so you learn that something private sat at that depth and not what.
  A record with nothing redacted has no `_redactions` field, not an empty one.
- **Credentials**, last: the same patterns that keep secrets out of the ledger
  (`infrastructure/ledger/redact.py`) run again over what the policy kept.

## The billing projection

`vibey ledger export PROJECT_ID --billing --out .vibey/billing-ledger.jsonl` writes a different,
operator-only projection for [`vibey-gh forecast`](delivery-estimate.md). It keeps only
`TurnCompleted.cost_usd`, `BudgetSpent.dollars` and `BudgetSpent.turns`, plus the bare kinds the
forecast counts (`PhaseTransitioned`, `CapacityRejected`, `HandoffInitiated`, `ToolInvoked`,
`FileEdited`, `ArtifactProduced`) with no payload. It reads no caps, so it withholds
`BudgetCapChanged` too, and it does not keep `_redactions`: it publishes cost, not payloads. Do
not commit it to a public repository unless you mean to publish your spend.

## How to check what was left out

`vibey ledger export` prints the counts, and the shard carries them into the published site's
`manifest.json`. Each record's own document (`records/<event_id>.json`) says what was removed from
inside it.

A published record's `digest` is the digest of what was published, so a reader can check every
record, and a withheld field cannot be recovered by guessing it and hashing. A record the policy
did not change has the same digest it has in the ledger. The shard's chain head is your ledger's,
over every event including the withheld ones: anyone holding the full ledger can recompute it and
confirm the shard came from that ledger.

To look things up in the full ledger on your own machine, use `vibey ledger search` (by record
id, digest, actor, time, kind or payload text) and `vibey ledger show`.

## Widening or narrowing

The policy is one value, `PublicationRules` in
[`domain/publication_policy.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/domain/publication_policy.py):
the allowlist, the chatter kinds, the withheld provenances, the tokens and whether `_redactions` is
published (`publish_redactions`, on by default; withholding it is a decision a rule set states).
Every shard names the exact rules that made it by their fingerprint (`policy.fingerprint`), so a
change of rules is visible in the next export.

There is no configuration key for the rules. Changing what is published today means changing that
file, through a reviewed pull request.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `unknown project ...` | The id is not a project in this database. | Run `vibey projects` and copy the id. |
| `Invalid value for --json-only: the human-first record pages are not built yet` | `vibey ledger site` was run without `--json-only`. | Add `--json-only`. |
| `invalid shard FILE: ...` | The file is not a shard written by `vibey ledger export`, or it was edited. | Export it again; do not hand-edit a shard. |
| The chain head line ends `published unverified` | The ledger's chain walk found disagreements, so the head is published but not vouched for. | Investigate the ledger before you publish; the line says how many disagreements were found. |
| A count you did not expect, such as many `kind not allowlisted` | Most of a run's events are operational kinds that are never published. | This is normal. Read the list above to see which kinds those are. |

## Where next

- [The ledger explorer](../explorer/index.md), to see a published shard and what was left out.
- [Keep a tamper-evident record](outcomes/keep-a-tamper-evident-record.md), for how the ledger
  itself stays append-only.
- [Publishing a finished project](publishing.md), which records `PublishCompleted` and
  `PublishSkipped`, both published without the URL and branch.

## Say it in one line

vibey publishes a counted, default-deny projection of a project's ledger, never the ledger itself,
and a chain head lets anyone holding the full ledger prove the shard came from it.
