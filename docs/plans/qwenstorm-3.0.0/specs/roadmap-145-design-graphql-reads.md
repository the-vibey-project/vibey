## Title
docs(adr): draft one shared GraphQL read path in the vibey-gh transport, for GitHub Discussions and Projects v2

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 7) marks this
"Design needed first — a GraphQL read path for discussions and Projects v2. One shared GraphQL
access pattern in the transport, not one per capability. Then one child each for discussions
and projects." #136 lists "discussions" among the classes a forge holds (S3, "GraphQL-only
classes after #145's GraphQL design"). The gap, verified at integration `4317cff6`:
- Four classes are excluded only because GraphQL is unread: `review-thread` ("exists only in
  the GraphQL API"), `discussion`, `project`, `pinned-issue`
  (`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:142`, `:152`, `:153`, `:170`).
- The transport has no GraphQL answer: `GhTransport` offers `run`, `json`, `probe`, `survey`,
  "each ... the extraction of a runner that exists today"
  (`src/vibey_tools/gh/vibey_gh/gh_transport.py:1-17`, `:33-115`;
  `vibey_gh/interfaces/gh_transport_interface.py:27-100`).
- GraphQL is already walked by hand, once per capability: `flatten.py`'s review-thread walk
  builds its own query, `--raw-field` variables, `errors` handling, `hasNextPage`/`endCursor`
  endings and a page bound (`src/vibey_tools/gh/vibey_gh/flatten.py:127-132`, `:152-168`,
  `:610-754`), and `github_state.upsert_comment` builds a mutation by hand
  (`src/vibey_tools/gh/vibey_gh/github_state.py:117-131`). A third and fourth copy for
  Discussions and Projects is what the issue forbids.

Ratified law: 8.b, every surface speaks one vibey-owned protocol, "Nothing in vibey's core ever
couples to a platform's native dialect" (`src/vibey_tools/gh/docs/doctrines.md:168-177`), and a
declared GitHub relays through the sovereign Forgejo (`doctrines.md:138`, `:179-186`); 10.e, the
family's one implementation, never a second (`doctrines.md:417`); 10.f, a walk that stopped
early is unknown, never complete (`doctrines.md:419`); 9.b (`doctrines.md:349`). GraphQL is
GitHub's dialect; Forgejo, the default forge, has no GraphQL API and no Discussions, which is
#145's open question 3.

## Required behaviour
The lane writes exactly one file, the draft ADR at the absolute path
`STORM/specs/ADR-roadmap-145-graphql-reads.md`, with
`write_file`. It changes no file in its clone and commits nothing.

Before writing, read every file:line below in the integration clone (your working directory)
and cite only lines you read; where a line has moved, cite where the text is now:
`src/vibey_tools/gh/vibey_gh/gh_transport.py:1-17`, `:33-47`, `:94-115`;
`src/vibey_tools/gh/vibey_gh/interfaces/gh_transport_interface.py:27-100`;
`src/vibey_tools/gh/vibey_gh/interfaces/forge_transport_interface.py:26-42`;
`src/vibey_tools/gh/vibey_gh/interfaces/forge_adapter_interface.py:37-123` (the forge-neutral
verbs; none is GraphQL); `src/vibey_tools/gh/vibey_gh/flatten.py:127-132`, `:152-168`, `:610-754`
(in particular `:660-662` `--raw-field`, `:691-695` `errors`, `:727-742` the two page endings);
`src/vibey_tools/gh/vibey_gh/github_state.py:117-131`;
`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:142`, `:152-153`, `:170`, `:200-207` (the
GitHub reader); `src/vibey_tools/gh/docs/forge-snapshot.md:284`, `:294-295`, `:312`;
`src/vibey_tools/gh/docs/adr/0001-forge-neutral-nouns.md` and
`src/vibey_tools/gh/docs/adr/0002-forgejo-is-the-sovereign-default-forge.md`; the doctrine
lines above; and `STORM/issue-audit/updates/145.md`.
Also read `STORM/specs/fakes-tenant-gh-1.md` (its
`ScriptedGhTransport`, the fake every GraphQL test will use).

The ADR carries these parts, in this order, each heading exactly as written:
1. First line: `# One GraphQL walk in the vibey-gh transport, shared by every capability that reads GitHub's GraphQL API`
   (no number). Then one line holding `**Status:** proposed`, `**Date:**` (the day you write
   it) and `**Cites:**` naming 8.b, 9.b, 10.e, 10.f, 12.c with their `doctrines.md:<line>`
   anchors, vibey ADR-0016 and ADR-0017, and vibey-gh ADR 0001 and 0002.
2. `## Context` — the facts above, each with its file:line.
3. `## Options considered` — at least these three, each with consequences:
   - **A. One `graphql` walk on the GitHub transport.** A method on `GhTransportInterface`,
     implemented once in `GhTransport`, extracted from flatten's walker as the transport's
     other answers were extracted: every capability passes a query and the path to one
     connection, and gets every node or a problem string.
   - **B. One walker per capability** (today's shape): flatten's, then discussions', then
     projects'. Each re-learns the `--raw-field`, `errors` and null-cursor lessons flatten
     records (`flatten.py:660-662`, `:691-695`, `:727-742`).
   - **C. `gh api graphql --paginate`.** It pages only the top-level connection named by
     `$endCursor`, cannot page a nested connection (a discussion's comments, a project's
     items), and still leaves `errors` handling to each caller.
4. `## Decision` — recommend A, argued from the evidence; if something you read contradicts
   it, keep A and record the contradiction under `## Verification owed`. GraphQL stays on the
   GitHub side: not on `ForgeTransportInterface` or `ForgeAdapterInterface`, whose verbs are
   forge-neutral (8.b); the snapshot envelope stays neutral and the payloads stay GitHub's.
5. `## The shared walk` — its contract, stated precisely: a signature (for example
   `graphql(query: str, variables: Mapping[str, str], connection: Sequence[str], *, pages: int)
   -> tuple[list[dict[str, Any]], str]`), where `connection` is the key path from `data` to the
   connection and the query must declare `$after: String` and select
   `pageInfo { hasNextPage endCursor }` and `nodes`; every variable sent with `--raw-field`;
   a non-empty `errors` array is a problem naming the first message; `hasNextPage` true with a
   null `endCursor` is a problem, not the end; reaching the page bound is a problem naming how
   many nodes were read; the bound is a parameter with a declared default (12.c). A nested
   connection is walked by a second call per parent node (`node(id:)`), the way the snapshot
   walks reviews and timelines one parent at a time. Tests use `ScriptedGhTransport`
   (`fakes-tenant-gh-1`), never a patched import.
6. `## Discussions` — two snapshot classes, `discussion` and `discussion-comment` (replies are
   comments of comments, a nested connection), read from `repository.discussions` with
   `updatedAt` for resuming; category and answer state kept in the payload. GitHub-only: any
   other reader answers "could not look".
7. `## Projects v2` — projects belong to a user or organisation; the repository's linked
   projects come from `repository.projectsV2`, and their items and field values from each
   project node. Reading them needs the `read:project` token scope, which `gh auth login`
   does not grant by default: a missing scope is a named "could not look", never an empty
   project list. Say how the scope is named in the problem text.
8. `## Consequences` — including that flatten's walker moves onto the shared walk (its tests
   pin today's behaviour) and that `review-thread` and `pinned-issue` become capturable.
9. `## Lanes this unblocks` — a table whose header row is exactly
   `| Slug-to-be | Title | Scope | Size |`, one row per lane, each sized for one 20B lane (one
   source file plus its interface, and one test file). At least:
   `roadmap-145-gh-graphql-walk` (the transport method, its interface and fake support),
   `roadmap-145-flatten-graphql-walk` (flatten's review-thread walk moves onto it),
   `roadmap-145-capture-discussions`, `roadmap-145-capture-discussion-comments`,
   `roadmap-145-capture-projects`, `roadmap-136-capture-review-threads`,
   `roadmap-136-capture-pinned-issues`.
10. `## Open decisions for the operator` — quote #145's open question 3 verbatim, exactly:
    > **Discussions and Projects** exist differently per forge. Forgejo has no Discussions.
    > Should vibey provide a sovereign equivalent (for example Matrix rooms, 8.b messaging
    > default), or treat Discussions as a GitHub-relay-only feature?

    The ADR does NOT answer it. Say only that capture of GitHub's Discussions records what the
    declared relay holds whichever way it is answered, and that nothing sovereign is built
    until it is.
11. `## Verification owed` — what the lanes must prove: the walk against a live GitHub under the
    opt-in `network` tier (`VIBEY_GH_NETWORK_TESTS=1`); flatten's behaviour unchanged; the
    `read:project` scope message on a token without it; GraphQL rate-limit cost per capture
    measured (8.g, `doctrines.md:316`).

## Where to change
- Create only `STORM/specs/ADR-roadmap-145-graphql-reads.md`
  (outside the clone). Its first line is the title above; ADR drafts carry no provenance header.
- No file in the clone changes. Nothing is committed.

## Acceptance criteria
The ADR's required sections, each checked by the script below:
- [ ] A number-less `# ` title line; `**Status:** proposed`, `**Date:**`, `**Cites:**`.
- [ ] `## Context`, `## Options considered`, `## Decision`, `## The shared walk`,
      `## Discussions`, `## Projects v2`, `## Consequences`, `## Lanes this unblocks`,
      `## Open decisions for the operator`, `## Verification owed`, in that order.
- [ ] `## The shared walk` names `hasNextPage`, `endCursor`, `errors` and `--raw-field`.
- [ ] `## Projects v2` names the `read:project` scope.
- [ ] The lanes table has the exact header row and at least 7 rows.
- [ ] #145's open question 3 is quoted verbatim under `## Open decisions for the operator`.
- [ ] At least 15 lines cite a `file:line` anchor.
- [ ] `git status --porcelain` in the clone is empty.

## Tests to write first (TDD)
None in the clone. The check script below is the test; write the ADR until it passes.

## Checks the lane must run (all must pass)
```bash
python3 -c '
from pathlib import Path
adr = Path("STORM/specs/ADR-roadmap-145-graphql-reads.md")
assert adr.is_file(), "the ADR file does not exist"
text = adr.read_text(encoding="utf-8")
lines = text.splitlines()
assert lines[0].startswith("# ") and not lines[0][2:3].isdigit(), "first line is a number-less title"
for needle in ("**Status:** proposed", "**Date:**", "**Cites:**"):
    assert needle in text, "missing " + needle
headings = ["## Context", "## Options considered", "## Decision", "## The shared walk",
    "## Discussions", "## Projects v2", "## Consequences", "## Lanes this unblocks",
    "## Open decisions for the operator", "## Verification owed"]
positions = []
for heading in headings:
    assert heading in lines, "missing heading " + heading
    positions.append(lines.index(heading))
assert positions == sorted(positions), "headings out of order"
walk = text.split("## The shared walk", 1)[1].split("## Discussions", 1)[0]
for needle in ("hasNextPage", "endCursor", "errors", "--raw-field"):
    assert needle in walk, "the shared walk does not name " + needle
projects = text.split("## Projects v2", 1)[1].split("## Consequences", 1)[0]
assert "read:project" in projects, "the read:project scope"
lanes = text.split("## Lanes this unblocks", 1)[1].split("## Open decisions for the operator", 1)[0]
assert "| Slug-to-be | Title | Scope | Size |" in lanes.splitlines(), "lanes table header"
assert len([row for row in lanes.splitlines() if row.startswith("| roadmap-")]) >= 7, "7 lane rows"
opens = text.split("## Open decisions for the operator", 1)[1].split("## Verification owed", 1)[0]
flat = " ".join(line.lstrip("> ").strip() for line in opens.splitlines())
question = "**Discussions and Projects** exist differently per forge. Forgejo has no Discussions. Should vibey provide a sovereign equivalent (for example Matrix rooms, 8.b messaging default), or treat Discussions as a GitHub-relay-only feature?"
assert question in flat, "#145 question 3 is not quoted verbatim"
print("ADR structure OK")
'
test "$(grep -cE '[A-Za-z0-9_./-]+\.(py|sql|md|toml):[0-9]+' STORM/specs/ADR-roadmap-145-graphql-reads.md)" -ge 15
test -z "$(git status --porcelain)"
```

## Out of scope
- Implementing the walk or any class; security alerts (blocked on #145 open question 4); the
  `@vibey` mention (`roadmap-145-vibey-mention`); Forgejo capture parity (after the gaps.md §L8
  lane).
- Answering #145 open question 3.
- Any file in the clone: code, `docs/`, ADRs under `docs/adr/`, CHANGELOG.
- Do not push, do not commit.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
