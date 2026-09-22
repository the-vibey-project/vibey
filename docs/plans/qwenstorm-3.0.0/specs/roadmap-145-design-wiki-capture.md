## Title
docs(adr): draft wiki capture: a mirror of `<repo>.wiki.git` inside the snapshot directory, joined to the manifest and to `--verify`

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 8, and Scope §3
"wiki (a clone of the separate wiki git repository)") marks this "Design needed first — wiki
capture. A mirror clone of `<repo>.wiki.git` into the snapshot directory, and whether
`has_wiki` (default `False`, `config.py:1047`; this repository's `[repository_profile]` does
not override it) changes." The gap, verified at integration `4317cff6`:
- The wiki is excluded: `("wiki", "The wiki is a git repository of its own.")`
  (`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:159`; docs row
  `src/vibey_tools/gh/docs/forge-snapshot.md:301`, "kept by cloning it"). The same reasoning
  already covers git objects: "`git clone --mirror` is their lossless snapshot"
  (`forge_snapshot.py:158`, `docs/forge-snapshot.md:300`).
- `has_wiki: bool = False` (`src/vibey_tools/gh/vibey_gh/config.py:1047`), loaded with the same
  default (`config.py:1877`); the root `.vibey-gh.toml` `[repository_profile]` (`:116-122`)
  does not set it, and vibey-gh's own sets `has_wiki = false`
  (`src/vibey_tools/gh/.vibey-gh.toml:113`). The profile is reconciled into the forge
  (`vibey_gh/install.py:325-339`), so changing the default would switch wikis on in every
  adopter's repository.
- vibey-gh has no git seam yet; `fakes-tenant-gh-1` adds `GitRunnerInterface` and
  `ScriptedGitRunner` (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/fakes-tenant-gh-1.md`).

Ratified law: 7.c, what the ledger does not hold is a gap (`src/vibey_tools/gh/docs/doctrines.md:82-91`);
8.b, documentation defaults to BookStack and the codebase's own docs, "never to a hosted or
paid wiki" (`doctrines.md:143-146`); 8.h, anything on the host works on Arch Linux and macOS
(`doctrines.md:326-333`); 10.f, a wiki that could not be fetched is "could not look"
(`doctrines.md:419`); 12.c (`doctrines.md:455`).

## Required behaviour
The lane writes exactly one file, the draft ADR at the absolute path
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-145-wiki-capture.md`, with
`write_file`. It changes no file in its clone and commits nothing.

This lane runs after `roadmap-136-snapshot-verify` and `roadmap-136-capture-repo-metadata`.
Before writing, read every file:line below in the integration clone (your working directory)
and cite only lines you read; where a line has moved, cite where the text is now. Find
`def verify`, `def _verify_file`, the `repository-metadata` entry of `CLASSES` and `_redacted`
in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` with
`grep -n "def verify\|def _verify_file\|repository-metadata\|def _redacted" src/vibey_tools/gh/vibey_gh/forge_snapshot.py`
and cite the lines it prints. Also read: `forge_snapshot.py:158-159`;
`src/vibey_tools/gh/vibey_gh/interfaces/forge_snapshot_interface.py` (`ChainVerdict`,
`SnapshotStoreInterface`); `src/vibey_tools/gh/docs/forge-snapshot.md:201-203`, `:240-255`
(the manifest), `:300-301`; `src/vibey_tools/gh/vibey_gh/config.py:1034-1047`, `:1877`;
`.vibey-gh.toml:116-122`; `src/vibey_tools/gh/.vibey-gh.toml:107-114`;
`src/vibey_tools/gh/vibey_gh/install.py:325-339`; `src/vibey_tools/gh/pyproject.toml:30`; the
doctrine lines above; `/private/tmp/claude-501/storm/qwenstorm-3.0.0/issue-audit/updates/145.md`
and `…/136.md`; `…/specs/fakes-tenant-gh-1.md`.

The ADR carries these parts, in this order, each heading exactly as written:
1. First line: `# The wiki is captured as a mirror of its own git repository inside the snapshot, and verified with it`
   (no number). Then one line holding `**Status:** proposed`, `**Date:**` (the day you write
   it) and `**Cites:**` naming 7.c, 8.b, 8.h, 10.f, 12.c with their `doctrines.md:<line>`
   anchors and vibey ADR-0016.
2. `## Context` — the facts above, each with its file:line.
3. `## Options considered` — at least these three, each with consequences:
   - **A. A mirror of `<repo>.wiki.git` in `<DIR>/wiki.git`**, plus a `wiki` class whose
     records hold the mirror's refs, so the snapshot's chain, cursor-free walk and manifest
     cover it like any class. Lossless: git history is the wiki's history.
   - **B. Read pages through a forge API.** GitHub has no REST or GraphQL API for wiki pages;
     Forgejo has one. A page API loses history and diverges per forge.
   - **C. Keep the exclusion.** The wiki stays a gap 7.c says to close.
4. `## Decision` — recommend A, argued from the evidence; if something you read contradicts it,
   keep A and record the contradiction under `## Verification owed`.
5. `## The mirror` — precisely: the clone URL is derived from the captured repository object
   (`clone_url` with `.git` replaced by `.wiki.git`), never typed into configuration; the first
   capture runs `git clone --mirror <url> <DIR>/wiki.git`, later captures run
   `git -C <DIR>/wiki.git fetch --no-prune <url> "+refs/*:refs/*"`, so no commit the snapshot
   once held becomes unreachable (a force-push on the forge does not erase it here); git runs
   through `GitRunnerInterface` (`fakes-tenant-gh-1`), credentials come from `gh auth
   git-credential`, and nothing new is added to `dependencies = []`
   (`pyproject.toml:30`). Host facts: `git` on Arch Linux (`pacman -S git`) and macOS (Xcode
   command line tools or Homebrew) behaves the same for these commands; the default tests use
   `ScriptedGitRunner` and a local bare repository, and one opt-in `network`-tier test
   (`VIBEY_GH_NETWORK_TESTS=1`) clones a real wiki (8.h).
6. `## The has_wiki default` — recommend keeping `RepositoryProfileConfig.has_wiki = False`
   (`config.py:1047`): 8.b makes BookStack and the codebase's own docs the documentation
   surfaces and a hosted wiki at best a declared relay (`doctrines.md:143-146`), and the
   profile is reconciled into the forge (`install.py:325-339`), so a `True` default would
   switch wikis on everywhere. Capture never reads the declared profile: it reads the forge's
   own `has_wiki` from the `repository-metadata` record.
7. `## The manifest and verify` — the `wiki` class and its manifest entry: `captured` with one
   record whenever the mirror's refs changed (payload `{"refs": {<ref>: <sha>, …}}`, native id
   `refs`), `could-not-look` when the fetch fails, and, when the forge's `has_wiki` is false,
   `captured` with `observed == 0` and nothing fetched (the forge's own answer that there is no
   wiki, never an assumption). `--verify` walks `wiki.jsonl` like every class file and adds one
   verdict for `wiki.git`: every sha in the latest refs record exists in the mirror
   (`git cat-file -e`) and `git fsck --no-dangling` passes; a failure is a `ChainVerdict` with
   the problem. Point in time (`docs/forge-snapshot.md:201-203`): the refs record at or before
   the moment names the commit to read.
8. `## Consequences`.
9. `## Lanes this unblocks` — a table whose header row is exactly
   `| Slug-to-be | Title | Scope | Size |`, one row per lane, each sized for one 20B lane. At
   least: `roadmap-145-capture-wiki` (the class, the mirror through `GitRunnerInterface`,
   depends on `fakes-tenant-gh-1`), `roadmap-145-verify-wiki` (the `wiki.git` verdict), and
   `roadmap-145-wiki-network-proof` (the opt-in network test on Arch Linux and macOS).
   Forgejo's wiki URL follows the gaps.md §L8 lane; name it as a later row, not a lane here.
10. `## Open decisions for the operator` — quote #136's open question 3 verbatim, because a
    wiki is people's text too:
    > **Public or private?** Captured comments include people's text. The public ledger shard
    > (7.a) needs a policy for what is published versus kept in a private tier.

    The ADR does NOT answer it: the mirror is held in the snapshot directory and is not
    published anywhere until it is answered.
11. `## Verification owed` — what the lanes must prove: a mirror fetch after a force-push keeps
    the old commit; `--verify` catches a deleted object; the `has_wiki: false` path makes no
    git call; the network proof on both operating systems.

## Where to change
- Create only `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-145-wiki-capture.md`
  (outside the clone). Its first line is the title above; ADR drafts carry no provenance header.
- No file in the clone changes. Nothing is committed.

## Acceptance criteria
The ADR's required sections, each checked by the script below:
- [ ] A number-less `# ` title line; `**Status:** proposed`, `**Date:**`, `**Cites:**`.
- [ ] `## Context`, `## Options considered`, `## Decision`, `## The mirror`,
      `## The has_wiki default`, `## The manifest and verify`, `## Consequences`,
      `## Lanes this unblocks`, `## Open decisions for the operator`, `## Verification owed`,
      in that order.
- [ ] `## The mirror` names `--mirror`, `.wiki.git` and `GitRunnerInterface`;
      `## The has_wiki default` cites `config.py:1047`; `## The manifest and verify` names
      `ChainVerdict` and `fsck`.
- [ ] The lanes table has the exact header row and at least 3 rows.
- [ ] #136's open question 3 is quoted verbatim under `## Open decisions for the operator`.
- [ ] At least 12 lines cite a `file:line` anchor.
- [ ] `git status --porcelain` in the clone is empty.

## Tests to write first (TDD)
None in the clone. The check script below is the test; write the ADR until it passes.

## Checks the lane must run (all must pass)
```bash
python3 -c '
from pathlib import Path
adr = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-145-wiki-capture.md")
assert adr.is_file(), "the ADR file does not exist"
text = adr.read_text(encoding="utf-8")
lines = text.splitlines()
assert lines[0].startswith("# ") and not lines[0][2:3].isdigit(), "first line is a number-less title"
for needle in ("**Status:** proposed", "**Date:**", "**Cites:**"):
    assert needle in text, "missing " + needle
headings = ["## Context", "## Options considered", "## Decision", "## The mirror",
    "## The has_wiki default", "## The manifest and verify", "## Consequences",
    "## Lanes this unblocks", "## Open decisions for the operator", "## Verification owed"]
positions = []
for heading in headings:
    assert heading in lines, "missing heading " + heading
    positions.append(lines.index(heading))
assert positions == sorted(positions), "headings out of order"
def section(start, end):
    return text.split(start, 1)[1].split(end, 1)[0]
mirror = section("## The mirror", "## The has_wiki default")
for needle in ("--mirror", ".wiki.git", "GitRunnerInterface"):
    assert needle in mirror, "the mirror section does not name " + needle
assert "config.py:1047" in section("## The has_wiki default", "## The manifest and verify")
manifest = section("## The manifest and verify", "## Consequences")
assert "ChainVerdict" in manifest and "fsck" in manifest, "verify joins the wiki"
lanes = section("## Lanes this unblocks", "## Open decisions for the operator")
assert "| Slug-to-be | Title | Scope | Size |" in lanes.splitlines(), "lanes table header"
assert len([row for row in lanes.splitlines() if row.startswith("| roadmap-")]) >= 3, "3 lane rows"
flat = " ".join(line.lstrip("> ").strip() for line in section("## Open decisions for the operator", "## Verification owed").splitlines())
question = "**Public or private?** Captured comments include people\x27s text. The public ledger shard (7.a) needs a policy for what is published versus kept in a private tier."
assert question in flat, "#136 question 3 is not quoted verbatim"
print("ADR structure OK")
'
test "$(grep -cE '[A-Za-z0-9_./-]+\.(py|sql|md|toml):[0-9]+' /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-145-wiki-capture.md)" -ge 12
test -z "$(git status --porcelain)"
```

## Out of scope
- Implementing any lane; changing `has_wiki` or `[repository_profile]`; Forgejo wiki capture
  (after the gaps.md §L8 lane); security alerts (blocked on #145 open question 4); the
  `@vibey` mention.
- Answering #136 open question 3.
- Any file in the clone: code, `docs/`, CHANGELOG.
- Do not push, do not commit.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
