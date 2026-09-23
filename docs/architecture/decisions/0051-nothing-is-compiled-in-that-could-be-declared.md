# 0051 — Configuration is declared in TOML, never written into a source file, and a derived value beats both

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrine 12.h which this record implements, and 12.c, 10.f · **Related:** ADR-0018, ADR-0020 · **Evidence:** the QwenStorm toolchain on 2026-09-23 — five tools carrying `MAIN = Path("/Users/adam/git/vibey")`, a sixth carrying a `/private/tmp` literal, and a `lane-refresh` run that reported "0 lane(s), 0 needed the new base" over 31 stale lanes

**Owes:** nothing new as conduct — 12.h is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

The operator's instruction was direct: never hard-code a path anywhere; make it configurable
through TOML; and anything that can be generic and configurable through TOML must be.

12.c already carried the principle — "a hard-coded value that could have been a key is a
decision taken away from the next adopter, silently" — and the storm toolchain violated it in
six files anyway. That gap between a ratified rule and the tree is the thing worth recording:
12.c says configurability is required, and says nothing about where the key goes or that a
literal is never an acceptable home for one. A rule with no named form is a rule people agree
with and do not apply.

The failure mode is what makes this expensive rather than untidy. A wrong absolute path does
not raise. It addresses a directory that is not there, and every tool built to survey a
directory answers "nothing here" — which is indistinguishable from a healthy tree. On
2026-09-23 `lane-refresh.py` was invoked through the planning worktree rather than the runtime
root and reported `0 lane(s), 0 needed the new base` while 31 lanes sat five commits stale. The
tool ran, printed, exited zero, and measured nothing. That is the same defect the storm spent
the previous night finding eleven of, arriving through a path instead of a parser.

## Decision

Anything that can be generic and configurable through a declared configuration file is, and it
is never made less so. The file is TOML, and the reason is not aesthetic: `pyproject.toml`,
`.vibey-gh.toml` and `vibey.toml` already exist, `tomllib` is in the standard library from
3.11, and a second format is a second parser to trust, a second syntax to learn and a second
place to look for the answer to "where is this configured".

**Derivation outranks configuration; both outrank a constant.** A value derived from the tree
cannot drift out of agreement with the tree. A declared key can — somebody moves a directory
and the file still says the old place. So the order is: derive it where the tree knows it,
declare it where the tree does not, and never write it into source either way. `storm_paths.repo()`
derives the repository by asking git for the common directory of a real worktree, and reads
`[paths] repo` from `storm.toml` when one is declared; the declared value wins, because an
operator who wrote it down meant it.

**The one exception is where the configuration itself lives**, and it is stated rather than
left to be discovered. A tool must find `storm.toml` before it can read a key out of it, so the
root is derived from the calling tool's own location. That is the whole of the exception.

## Consequences

The toolchain runs on a machine that is not the author's, which it could not do before. The
six literals are gone and `storm.toml` carries the one key that is genuinely site-specific.

The derivation had to be got right rather than assumed, and the first attempt was wrong in an
instructive way. `integration/` looked like the obvious place to ask git where the repository
is, and it is a full clone, so its common git directory is its own — `repo()` confidently
returned the clone, and every tool then ran `gh` and `git` against a tree with no origin/develop
and no pull requests, reporting it in the vocabulary of a broken network. The correct source is
the `tools/` symlink, which points into a real worktree.

That left two opposite rules about the same symlink, both load-bearing: `storm()` must NOT
follow it, because `lanes/` exists only where it points from, and `repo()` MUST follow it,
because the repository is reachable only where it points to. Both are written down at the point
of use, because a reader who knows only one of them will break the other.

## Alternatives considered

**Environment variables.** The first draft used `VIBEY_REPO` and `VIBEY_STORM`, and the
operator rejected it. Rightly: an environment variable is not declared in the repository, is
not reviewed in a pull request, and is not reconciled from the tree, which fails all three of
12.c's tests at once. It is configuration that leaves no trace of having been configured.

**A JSON or YAML config.** Both work and neither is already here. TOML is what this repository
declares itself in, and the cost of a second format is paid by every reader forever.

**Leave it to 12.c.** This was the status quo, and 12.c was ratified before the six literals
were written. The principle without a named form did not stop them.

**A constant with a comment saying "change this for your machine".** This is the failure with
documentation attached. It still has to be edited in a source file, it still arrives in a diff
as a code change, and on the day somebody forgets, it still reports an empty tree.
