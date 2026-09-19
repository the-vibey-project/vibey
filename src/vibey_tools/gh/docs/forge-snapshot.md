# Forge snapshot

A repository's code is in git, and git travels: clone it anywhere and nothing is lost. The
rest of a project does not travel like that. Its issues, its pull requests and the reviews on
them, its labels, milestones and releases live in the forge's database, and leave only on the
forge's terms. `vibey-gh forge-snapshot` reads that state out of GitHub and writes it to plain
files the project owns.

This page is the reference for what those files contain. It is written so that someone who
has never seen this tool, holding only the files, could read them.

## What a snapshot is, and is not

A snapshot is a directory of [JSON Lines](https://jsonlines.org/) files, one per kind of
artifact, plus a `manifest.json` that says what happened to every kind. Every line is one
**record**: a small, forge-neutral envelope wrapped around the forge's own JSON for one
artifact, exactly as the forge returned it.

It is the first slice of [vibey#136](https://github.com/the-vibey-project/vibey/issues/136),
and it is deliberately narrow:

- **Read-only.** It never writes to the forge. Every call is a `GET` listing.
- **GitHub only.** A second forge is a second reader, and a later slice.
- **Files only.** Nothing goes into the vibey ledger yet. That writer needs the storage tiers
  of vibey#114, and will take these same records, already sealed, unchanged.
- **Native payloads.** Only the envelope is neutral. A payload is never translated, so no
  meaning is lost to a mapping a later slice might want to draw differently.

## Taking one

```bash
vibey-gh forge-snapshot --out forge-state
```

| Option | Meaning |
|---|---|
| `--out DIR` | Required. The snapshot directory. Created when missing; appended to when not. |
| `--repo OWNER/NAME` | The repository. Without it, `$GH_REPO`, then the repository `gh` finds in the current directory. |
| `--classes a,b,c` | Only these artifact classes (the names in [the table below](#the-files)). Without it, all of them. |
| `--since MOMENT` | Capture from an ISO 8601 moment (`2026-09-18`, `2026-09-18T12:00:00Z`) rather than from the beginning. A moment with no offset is read as UTC. `--since resume` uses the resume point the last manifest recorded. |
| `--per-page N` | Items per listing page, 1 to 100. Default 100, GitHub's maximum. |
| `--clock-skew SECONDS` | How far this machine's clock may run ahead of the forge's. Default 300. See [resuming](#resuming-and-why-a-rerun-is-safe). |

It needs the [GitHub CLI](https://cli.github.com/) at version 2.48 or later (for
`gh api --paginate --slurp`), authenticated with read access to the repository. Draft
releases are only listed to an account with push access; without it they are simply not
returned.

The exit status is `0` when every selected class was captured, `1` when at least one could
not be looked at (the others are still written, and the manifest says which), and `2` when
the arguments name no capture at all: an unknown class, an empty selection, a moment that is
not one, a page size out of range, a negative clock allowance, or a repository that is not
`owner/name`.

**What it costs.** One API call per listing page, and one per change request for its
reviews, because GitHub lists reviews one pull request at a time. Measured on this
repository on 2026-09-18: a full capture took two minutes and held 264 entries from the
issue listing (pull requests' issue sides among them), 219 pull requests, 152 reviews, 335
review comments, 87 comments, 18 labels, 11 releases and 11 tags. Resuming from its cursor a
few minutes later took under five seconds.

## Resuming, and why a rerun is safe

Every class that can be bounded by a moment keeps a **cursor** in the manifest: the moment a
later capture of it can start from without missing anything. After a walk that covered
everything since the previous cursor, the cursor moves to the latest of three moments:

- the previous cursor;
- the latest update time the forge reported among what it walked, in the forge's own clock;
- the moment the capture began, by this machine's clock, set back by `--clock-skew` (five
  minutes by default) in case that clock runs ahead of the forge's.

The third is what lets a class with nothing in it, or nothing new, be resumed at all.
Without it, a repository with no review comments would never have a resume point. The
allowance costs nothing but calls: whatever it makes a later capture read again is counted
as unchanged. A machine whose clock runs further ahead of the forge's than the allowance can
carry a cursor past an update the forge has not reported yet, so the allowance is yours to
widen, and is recorded in the manifest.

A walk that started *later* than the cursor, with `--since` past it or with any `--since` on
a class that has no cursor yet, left a stretch of history unwalked. Its cursor stays where it
was, so that the next resume starts at the gap and fills it instead of stepping over it.

The manifest's `resume_since` is the earliest of the cursors, and is `null` until every
resumable class has one:

```bash
vibey-gh forge-snapshot --out forge-state --since resume
```

A resumed capture appends to the same files and **continues the same chains**: the first
record it writes links to the last one already there. Three things make that safe to repeat:

- **Nothing identical is written twice.** Before writing, the store compares each artifact's
  content digest with the latest record it holds for that artifact. A match is counted as
  `unchanged` and not written. Rerunning a capture over a moment it has already covered
  appends nothing.
- **The cursor is inclusive.** GitHub's `since` means "updated at or after", so the artifacts
  updated at exactly the cursor are fetched again, and then counted as unchanged.
- **A class that could not be looked at does not move.** Its file is untouched and its cursor
  stays where it was, so the next resume covers the gap.

How each class is bounded by a moment:

- **Issues, comments and review comments** are filtered by GitHub itself (`since=`).
- **Change requests** cannot be: GitHub's pull-request listing has no `since`. They are paged
  by hand, most recently updated first, and the walk stops at the first one older than the
  moment instead of fetching every page to throw most away.
- **Reviews** have no update time of their own. Submitting, editing or dismissing a review
  updates its pull request, so a capture from a moment lists the reviews of every change
  request updated since then.
- **Labels, milestones, releases and tags** are small, have no such filter, and are walked
  whole every time. The unchanged check keeps that from costing any records.

Two honest limits:

- **A capture is not a transaction.** GitHub's listings are paged by position. If the forge
  changes while a capture walks it, an item can shift from a page not yet read onto one
  already read, and be missed by that capture. An item that is *updated* is always caught by
  the next resume, because its new update time is past the cursor; one that merely *shifted*
  is not. A periodic full capture (no `--since`) catches those, and costs only the records
  that actually changed.
- **Deletion is invisible.** A deleted artifact is never returned again. Nothing is written
  for it, and nothing here infers anything from its absence.

## The files

| File | Class | GitHub's name for it | Listed from | Native id | Resumable |
|---|---|---|---|---|---|
| `issue.jsonl` | `issue` | `issue` | `/repos/{repo}/issues?state=all` | `id` | yes |
| `comment.jsonl` | `comment` | `issue_comment` | `/repos/{repo}/issues/comments` | `id` | yes |
| `change-request.jsonl` | `change-request` | `pull_request` | `/repos/{repo}/pulls?state=all` | `id` | yes |
| `review.jsonl` | `review` | `pull_request_review` | `/repos/{repo}/pulls/{number}/reviews` | `id` | yes |
| `review-comment.jsonl` | `review-comment` | `pull_request_review_comment` | `/repos/{repo}/pulls/comments` | `id` | yes |
| `label.jsonl` | `label` | `label` | `/repos/{repo}/labels` | `id` | no |
| `milestone.jsonl` | `milestone` | `milestone` | `/repos/{repo}/milestones?state=all` | `id` | no |
| `release.jsonl` | `release` | `release` | `/repos/{repo}/releases` | `id` | no |
| `tag.jsonl` | `tag` | `tag` | `/repos/{repo}/tags` | `name` | no |

A few things about GitHub that the files keep rather than hide:

- **Every pull request is also an issue.** GitHub's issue listing returns pull requests
  too, and both are kept. A record in `issue.jsonl` whose payload has a `pull_request` key is
  the issue side of a change request: its reactions and comment count live only there. The
  change request itself is in `change-request.jsonl`.
- **A comment on a pull request's conversation is an issue comment.** It is in
  `comment.jsonl`. A comment on a line of its diff is a review comment, in
  `review-comment.jsonl`, and carries the `pull_request_review_id` of the review it was part
  of.
- **Asset manifests ride inside releases.** Every release payload lists its assets (name,
  label, size, content type, digest where GitHub reports one, download count and URL). The
  asset bytes are not downloaded. Download counts change without the release changing, so a
  later capture records a new version of a release whose downloads moved.
- **A class that has never had anything in it has no file.** The manifest says `captured` with
  `observed: 0`, which is a different fact from `could-not-look` and reads as one.

## A record

Every line is one JSON object in the canonical form below. Pretty-printed, one of this
repository's tags looks like this:

```json
{
  "captured_at": "2026-09-18T18:39:08Z",
  "class": "tag",
  "forge": "github",
  "native_class": "tag",
  "native_id": "vibey-v1.0.0",
  "payload": {
    "commit": {
      "sha": "4e9adf18b660a9be8b6a8a9b20b879d58325d9d4",
      "url": "https://api.github.com/repos/the-vibey-project/vibey/commits/4e9adf18b660a9be8b6a8a9b20b879d58325d9d4"
    },
    "name": "vibey-v1.0.0",
    "node_id": "REF_kwDOT4w2PLZyZWZzL3RhZ3MvdmliZXktdjEuMC4w",
    "tarball_url": "https://api.github.com/repos/the-vibey-project/vibey/tarball/refs/tags/vibey-v1.0.0",
    "zipball_url": "https://api.github.com/repos/the-vibey-project/vibey/zipball/refs/tags/vibey-v1.0.0"
  },
  "payload_sha256": "c1882e6b383efdb1cfe57914a21e04612a7d1b606f72279f1e6a2878e282790b",
  "prev": null,
  "repository": "the-vibey-project/vibey",
  "schema": "vibey.forge-record/1",
  "sha256": "1ba0cafd6d58e26d39a9be17e194767bb5d82e3ef36d191fe69473f4599918d2"
}
```

| Field | Meaning |
|---|---|
| `schema` | Always `vibey.forge-record/1`. A change to this table is a new number. |
| `forge` | The forge the record was read from: `github`. |
| `repository` | `owner/name` on that forge. |
| `class` | The forge-neutral class, which is also the file's name. |
| `native_class` | The forge's own name for the kind of object. |
| `native_id` | The forge's identifier for the object, always a string. Stable across edits, so every version of one object shares it. |
| `captured_at` | When the walk of this class began, UTC, to the second. The object was observed in this state no earlier than this moment. |
| `payload` | The forge's JSON for the object, verbatim: every field, in the forge's own names. |
| `payload_sha256` | The SHA-256 of the payload's canonical form: the content's identity. Two records with the same value hold the same content. |
| `prev` | The `sha256` of the record before this one in the same file, or `null` for the first. |
| `sha256` | The SHA-256 of the canonical form of every other field of this record, `prev` included: the record's seal. |

**Point in time.** The state of an object as of a moment is its latest record with a
`captured_at` at or before that moment. Records are only ever appended, so an earlier state
is never overwritten, only followed.

## The canonical form, and checking a chain

Every digest is taken over one serialisation: the JSON with its keys sorted at every level,
no whitespace between tokens (`,` and `:` as separators), non-ASCII characters escaped as
`\uXXXX`, encoded as UTF-8. In Python that is
`json.dumps(value, sort_keys=True, separators=(",", ":")).encode()`. It is byte for byte the
form the vibey ledger hashes its events in, so a record sealed here verifies there.

The lines on disk *are* that form, which makes a chain checkable with nothing but a standard
library. This checks one file, and prints its head, which should equal the manifest's:

```python
import hashlib, json, sys

head = None
for number, line in enumerate(open(sys.argv[1], "rb"), start=1):
    record = json.loads(line)
    seal = record.pop("sha256")
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == seal, f"line {number}: seal broken"
    assert record["prev"] == head, f"line {number}: chain broken"
    head = seal
print(head)
```

A line edited, removed or moved breaks the chain at that line. A `--verify` walk that does
this for a whole snapshot is the next slice.

The store refuses to append to a file holding anything it did not write: a line that is not
a record, a record of another repository or forge, or a line whose write never finished.
Every file is read back, and so checked, before the forge is asked anything, so a snapshot
that cannot be extended is refused with nothing written.

## The manifest

`manifest.json` is rewritten, whole, at the end of every capture. It is an index over the
class files, which remain the record; everything in it except the exclusions and the
cursors can be recomputed from them.

| Field | Meaning |
|---|---|
| `schema` | `vibey.forge-manifest/1`. |
| `record_schema` | The record schema the class files hold. |
| `forge`, `repository` | What this snapshot is of. A capture into a directory holding another repository is refused. |
| `captured_at` | When this capture began. |
| `since` | The moment this capture started from, or `null` for a full one. |
| `clock_skew_seconds` | The clock allowance this capture used for its cursors. |
| `complete` | `true` when every selected class was captured. |
| `resume_since` | Where the next capture can resume from, or `null` when some resumable class has never been captured completely. |
| `classes` | One entry for every class this command knows, selected or not. |
| `excluded` | Every artifact class this capture did not hold, each with its reason. |

Each entry in `classes`:

| Field | Meaning |
|---|---|
| `status` | `captured`, `could-not-look`, or `not-selected`. |
| `problem` | Why the forge could not be asked, word for word; empty unless `could-not-look`. |
| `captured_at` | When this class's walk began; `null` if it was not selected. |
| `observed` | How many objects the forge returned; `null` unless `captured`. |
| `appended` | Records written by this capture. |
| `unchanged` | Objects whose content matched the latest record already held. |
| `records` | Records in the file after this capture. |
| `head` | The `sha256` of the file's last record, or `null` for an empty chain. |
| `cursor` | The class's resume point, or `null` for a class that is walked whole. |

`could-not-look` covers a missing `gh`, an unauthenticated or rate-limited client, a failed
call, and an answer of the wrong shape. None of them is ever written down as a class with
nothing in it.

## What is not captured

A capture holds the nine classes above, and names everything else in the manifest's
`excluded` list with a reason, so that nothing a repository holds is dropped without saying
so. The list, as this version writes it:

| Class | Why not |
|---|---|
| `timeline-event` | Issue and change-request timelines are one call per item. The state their events produced is inside the captured payloads; the sequence of events is not. |
| `review-thread` | Whether a review thread is resolved exists only in the GraphQL API. The comments are captured; their thread's resolution is not. |
| `reaction` | Who reacted, and with what, is one call per item. The per-item totals are captured. |
| `edit-history` | Earlier versions of an edited body are not read. A later capture records a later edit. |
| `single-item-detail` | Some fields exist only when one item is fetched by number: an issue's `closed_by`, a change request's `merged_by`, mergeability, and commit, file and line counts. |
| `deletion` | A deleted artifact is never returned again, and there are no tombstones. |
| `release-asset-content` | Asset manifests are captured; asset bytes are not downloaded. |
| `commit-comment` | Comments on commits are not read. |
| `check-run` | Check runs and suites belong to commits, and are listed one commit at a time. |
| `commit-status` | Commit statuses belong to commits, and are listed one commit at a time. |
| `workflow-run` | Actions runs, jobs, logs and artifacts: a slice of their own. |
| `discussion` | Discussions exist only in the GraphQL API. |
| `project` | Projects belong to an account, not the repository, and exist only in the GraphQL API. |
| `ruleset` | Not read. vibey-gh's own are declared in `.vibey-gh.toml` and reconciled by `vibey-gh rulesets`. |
| `branch-protection` | Needs administration permission to read. |
| `repository-metadata` | Not read. The settings vibey-gh manages are declared in `[repository_profile]`. |
| `collaborator` | Needs administration permission, and is personal data. |
| `git-object` | Commits, trees, blobs and branches, `refs/pull/*` among them, are git itself: `git clone --mirror` is their lossless snapshot. Tags are captured as the forge lists them. |
| `wiki` | A git repository of its own, kept by cloning it. |
| `deployment` | Deployments and environments are not read. |
| `webhook` | Needs administration permission, and holds secrets. |
| `secret` | Write-only by design: the forge never returns a value, and nothing here asks. |
| `variable` | Actions variables are not read. |
| `security-alert` | Security alerts and advisories are permission-gated and sensitive. |
| `package` | Packages belong to the owning account. |
| `stargazer-watcher-fork` | Other accounts' relationships to the repository, not its own state. |
| `traffic` | A rolling fourteen-day window the forge discards. |
| `pages` | The Pages configuration is not read. |
| `sub-issue` | Sub-issue links and issue types are not read. |
| `pinned-issue` | Exists only in the GraphQL API. |
| `autolink` | Needs administration permission to read. |
| `deploy-key` | Needs administration permission to read. |
| `custom-property` | Set by the organisation; not read. |

A class left out with `--classes` is added to the list for that capture, with the reason
that it was not selected, and its file and chain are left exactly as they were.

## What comes next

This slice is S1 of vibey#136. The rest, in order:

- **S2, a `--verify` walk:** check every seal, every link and every manifest head, and report
  the first break in each file.
- **S3, more classes:** the exclusions above that the REST API can serve, starting with
  timelines, commit comments and repository metadata.
- **S4, the vibey ledger writer:** a second store that writes these records into the ledger,
  in a table of their own, tiered as vibey#114 describes. Blocked on #114.
- **S5, the round trip:** restore a snapshot into a clean Forgejo, capture it again, and
  compare. The acceptance proof of #136, and it needs a Forgejo to run against.
