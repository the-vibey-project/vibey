# What gets published

**Bottom line:** `vibey ledger export` never publishes your ledger. It publishes a
*projection* of it — the decisions, questions, answers, assumptions, findings and
phase moves, with local paths and email addresses taken out — and it counts, by
reason, everything it left out. Nothing is dropped without a number saying so.

This page is for the operator deciding whether to publish a project's ledger. The
commands themselves are in the [CLI reference](../reference/cli.md#vibey-ledger).
The rule this serves is [sub-doctrine 7.a, the searchable ledger](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/doctrines.md):
anyone, no matter who, can search the ledger — the full ledger where a deployment
holds it, or the shard a repository holds.

## The words on this page

- **The ledger** is the append-only record of everything that happened to a
  project: every question, answer, decision, finding, phase move, and every turn an
  engine took. It lives in Postgres and is never published directly.
- **A shard** is the file `vibey ledger export` writes: one header line, then one
  published record per line. It is the part of the ledger a repository holds, and
  you commit it like any other file.
- **The publication policy** decides, event by event and field by field, what goes
  into a shard. It is *default-deny*: anything it does not name is withheld.
- **Withheld** means left out of the shard and counted. **Stripped** means replaced
  inside a published string by a token (`[path]`, `[email]`, `[REDACTED]`).

## What is published

An event is published only when its kind is on the allowlist, and then only the
fields listed for that kind:

| Kind | Fields kept |
|---|---|
| `PhaseTransitioned` | `from`, `to`, `cycle`, `guard` |
| `DecisionRecorded` | `decision_id`, `decision`, `title`, `choice`, `rationale`, `alternatives`, `supersedes`, `next_phase`, `work_item_id`, `independent_review` |
| `QuestionAsked` | `item_id`, `question_id`, `text`, `default`, `blocking`, `stage`, `cycle` |
| `AnswerGiven` | `item_id`, `question_id`, `answer` |
| `AssumptionStated` | `item_id`, `assumption_id`, `text`, `question` |
| `FindingRaised` | `finding_id`, `severity`, `ambiguity`, `text`, `automated` |
| `FindingResolved` | `finding_id`, `resolution` |
| `ArtifactProduced` | `artifact_id`, `artifact_type`, `title`, `cycle` |
| `VerdictRendered` | `complete`, `success`, `remaining_work` |
| `VisualDesign*`, `Deployment*` choices | `choice` |

Every other field of those events is withheld. Every event keeps its envelope —
id, seq, cycle, phase, kind, engine, job, causation and correlation ids,
provenance, and time — because that is what makes a record findable and places it
in the arc of the work.

Answers you gave during the design interview are published as you typed them, less
paths and addresses. If an answer holds something that should not be public, do not
export until the policy can withhold it (see [Widening or narrowing](#widening-or-narrowing)).

## What is withheld

- **Engine chatter, always.** Prompts, model output and tool calls (`TurnRequested`,
  `TurnCompleted`, `ToolInvoked`) — the kinds every engine's traffic lands on — are
  withheld whole, whatever the allowlist says.
- **Anything from outside.** An event with `untrusted` provenance carries text vibey
  did not write — a web page read during research, an issue body — and is withheld
  whole, so the site never re-serves a stranger's words under your project's name.
- **Every kind not on the list**, including `SessionSeeded` (seed prompts),
  `FileEdited` (diffs), `BudgetSpent` (your spend), `CapacityRejected`,
  `SavePointCreated`, and the handoff kinds.
- **`repo_path`, never.** Where the project lives on your machine is not published
  under any rules; a rule set that tries to allow it is refused.
- **Absolute paths and email addresses** inside a published string are stripped:
  `/Users/…`, `~/…`, `C:\…`, `\\server\…` and `file://…` become `[path]`, and
  `name@example.com` becomes `[email]`. Relative paths (`src/vibey/cli/main.py`),
  URLs and version pins (`vibey@1.1.0`) are kept. A key inside a published value that
  is itself a path or an address is withheld with its value.
- **Credentials**, last: the same patterns that keep secrets out of the ledger
  (`infrastructure/ledger/redact.py`) run again over what the policy kept.

## How to check what was left out

`vibey ledger export` prints the counts, and the shard carries them to the published
site's `manifest.json`:

```text
1 event withheld by policy (0 untrusted provenance, 1 engine chatter, 0 kind not allowlisted)
from published records: 1 field(s) withheld, 1 absolute path(s) and 0 email address(es) stripped, 0 record(s) with a credential redacted
```

Each record's own document (`records/<event_id>.json`) says what was removed from
inside it. A published record's `digest` is the digest of what was published, so a
reader can check every record, and a withheld field cannot be recovered by guessing
it and hashing. The shard's chain head is your ledger's, over every event including
the withheld ones: anyone holding the full ledger can recompute it and confirm the
shard came from that ledger.

## Widening or narrowing

The policy is one value, `PublicationRules` in
[`domain/publication_policy.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/domain/publication_policy.py):
the allowlist, the chatter kinds, the withheld provenances and the two tokens. Every
shard names the exact rules that made it by their fingerprint (`policy.fingerprint`),
so a change of rules is visible in the next export. There is no configuration key for
it yet; the per-repository opt-in (#137's next slices) is where one belongs.

## Publishing, step by step

```bash
vibey ledger export <project-id> --out ledger/greeter.jsonl
git add ledger/greeter.jsonl && git commit -m "docs(ledger): publish the greeter shard"
vibey ledger site --from ledger/greeter.jsonl --out site/ledger --json-only
```

The export needs the database; the site build does not, so it can run in the job
that builds the documentation. Human-first record pages come next; until they do,
`--json-only` is required.
