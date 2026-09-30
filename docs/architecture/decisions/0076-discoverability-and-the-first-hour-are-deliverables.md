# 0076 — Discoverability and the first hour are deliverables

**Status:** proposed · **Date:** 2026-09-30 · **Extends:** ADR-0032 (the paper and the book, findable everywhere), ADR-0033 (governance in plain sight) · **Cites:** doctrines 1, 2, 5 and 7; sub-doctrines 7.b, 7.d, 10.e, 10.f, 12.c and 12.e · **Related:** ADR-0017, ADR-0018, ADR-0020, ADR-0047 · **Evidence:** `develop` at `4714d092c` (the 3.2.0 release), read 2026-09-30 · **Canon:** proposes sub-doctrine 7.e — *the open door*, under doctrine 7 (the never-lost reader), carried on its own branch for the operator's ratification

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry; `docs/llms.txt` regenerated from that
nav. All three are in the change that carries this record.

## Context

vibey is free and open-source software, and open source lives or dies by two moments a
maintainer never sees: the moment a stranger finds the project, and the hour after, in
which they decide whether to give it their first contribution. The canon already speaks
to both. Doctrine 1 puts the problem first; doctrine 5 orders the arc from the zero-code
beginner up; 7.b puts the project's law one link from every surface; 7.d makes every
word findable by search engines and by AI readers, with the machine-readable layer
declared and reconciled rather than hand-set. What the repository lacked was the
machinery that makes those rules hold on the surfaces a newcomer actually meets.
Measured at `4714d092c`:

- **The README's first screen was metadata.** Eight badges came first, then a pointer
  to a research paper of four thousand lines. The problem the project solves arrived on
  the fifteenth line. Nothing on the first screen linked the Constitution, which 7.b
  requires of every README.
- **Nobody could quote what vibey is.** The package summary, the repository description
  and the site description each said "a queue-based, six-phase conductor" — accurate,
  and made of words no one searches for. The README said what vibey does for you ("the
  layer that does the babysitting") but never named the kind of thing it is in the words
  a search would match: an orchestrator for AI coding agents.
- **The published site repeated itself.** release-surfaces gave every page canonical
  links, social cards, JSON-LD, a sitemap and a root `llms.txt`, but every page carried
  the same site-wide description, the home page carried two, and `llms.txt` named the
  channels and the offline forms without naming a single page.
- **The contributor guide started in the middle.** `CONTRIBUTING.md` opened with the
  environment a regular needs and left a newcomer to assemble a path from sixteen
  sections. The bug template suggested version 0.6.0 as a placeholder, three majors
  stale. No surface pointed at an issue a first-timer could take.
- **Public figures were held by nothing.** The paper's empirical figures are regenerated
  and drift-checked, but the README and the guides quote what tests do by hand, and
  nothing checked that the tests still do it. `CITATION.cff`, which GitHub
  prints as "Cite this repository", gave the release date of an older version through
  three releases because no machinery wrote it.
- **Package and repository metadata named nothing a search filters by**: no keywords,
  no classifiers, and repository topics such as `agents`, `orchestration` and
  `mit-license`.

None of this was wrong in the sense of being false. It was work nobody could find, which
7.d says is indistinguishable from work nobody did.

## Decision

**Being found, and turning a newcomer into a contributor within an hour, are
deliverables of this repository: specified, built, and checked like any feature.** Six
commitments follow.

1. **The first screen has a contract.** The README and the documentation landing page
   open, in order, with the problem in words anyone recognises; one definitional
   sentence — *"vibey is a free, open-source orchestrator for AI coding agents"* — that a
   search engine or an AI reader can quote whole; the zero-code explanation; who the
   project is for; proof points, each linking to the test, decision record or file that
   proves it; a way to try it; and the path to a first contribution and to the law.
   Badges and document links follow; nothing below the fold is dropped. The two copies
   say the same thing.
2. **One definition, everywhere it fits.** The package summary, the repository
   description and the site description state what vibey is in the same words, shaped to
   each surface's length.
3. **The machine-readable layer is generated or declared, never hand-set.**
   `docs/llms.txt` is generated from the `properdocs.yml` nav by `scripts/llms_txt.py`,
   which reads the nav with vibey-gh's own `NavReader` and the channel, the governance
   source and the offline forms through vibey-gh's own configuration (10.e). A page's
   `description:` front matter becomes its meta description through `docs-theme/`; the
   publishing workflow keeps a description a page already has, and names the language
   and the licence in the structured data where `[project]` declares them. Keywords live
   in `[documentation]`, the description and topics in `[repository_profile]`, and
   classifiers in each `pyproject.toml` — all reconciled from the file (12.c).
4. **Claims are evidenced and held to their evidence.** A figure a public page quotes
   from a test is read out of that test and checked (`test_published_figures`); a
   first-screen link that does not land fails the build; the version bump writes the
   citation's release date beside its version (10.f, 12.e).
5. **The first hour is a written path.** `CONTRIBUTING.md` opens with *Your first hour*:
   from a fork to a pull request in five timed steps, a first test that needs no
   database, the chaos test once PostgreSQL is up, and a short list of good first
   changes led by the good-first-issue and help-wanted searches. The templates meet a
   first-timer halfway.
6. **Hard engineering is told as case studies.** A case study tells one property of the
   system as a story — problem, the fixes that fail, the design, the evidence, the cost
   — with every claim linked to its source. The first is *How vibey survives a crashed
   agent*, in the nav under *Case studies*, between the guides and the reference so the
   beginner's on-ramp still comes first.

**What checks it.** `tests/meta/test_first_screen.py` holds both first screens to the
contract a machine can check: the problem before the project's name, the same
definition in both, a first-hour path, a governance link, a counted ADR total, and every
first-screen link landing. `tests/meta/test_llms_txt.py` runs `scripts/llms_txt.py
--check` and names any nav page the index lacks. `tests/meta/test_published_figures.py`
reads the chaos test's constants and holds every page that quotes them. A vibey-gh
template test compiles the publishing step's metadata code. The prose itself — whether
the opening survives a reader with no context, whether it states the problem first,
whether the arc serves the beginner first — is judged on every pull request by the
exact-head review's `opening_accessible`, `opening_bluf` and `audience_order`
judgments, which a machine can gather evidence for but a model, not a regex, must weigh.

**What it does not do.** It invents nothing to look popular: no testimonials, adopters,
download counts or star counts, which would be false witness under 4.a. It adds no page
written for a search engine rather than a reader, and no keyword list longer than the
words that are true (7.d forbids both).

**Gaps it records rather than papers over.**

- *Labels.* No file in this repository declares its issue labels, and vibey-gh
  reconciles only the labels its own automation manages. The first-hour guide and the
  README therefore link GitHub's default `good first issue` and `help wanted` searches
  instead of creating labels by hand. Declaring labels as code is owed to a later change
  that teaches vibey-gh to reconcile them (10.e).
- *Decision records keep their title as their description.* Front matter on a Markdown
  file renders as a table at the top of the page on GitHub, which is where most readers
  meet a decision record, so the records carry no `description:`; `llms.txt` lists them
  by title, and the titles state the decisions.
- *The hour is a target, not a measurement.* No newcomer's first hour has been timed.
  The guide says which step runs long and why.
- *The structured data names the maintainer as author,* as `[documentation] author`
  declares; changing that is the operator's call.

## Consequences

**Good.** A stranger who lands on the README, the docs site, the PyPI page or the
repository page reads the same definition first, and every proof point on that screen
is one click from its evidence. An AI reader gets a page-by-page index that cannot fall
behind the site. A would-be contributor has one path, with commands, from a fork to a
pull request. The figures the project quotes about itself are checked against the tests
that produce them.

**Bad.** Every nav change now carries one more command, `python scripts/llms_txt.py`, and
the build fails until it is run — deliberately (12.e), but it is a step. The first
screen is longer than a bare title and a badge row. The case study and the frequently
asked questions are prose that can go stale where no test reaches; the review gate is
their guard. A change to `pyproject.toml` metadata reaches the PyPI page only with the
next release.

**Neutral.** The publishing workflow's changes are generic: any repository that adopts
vibey-gh gets a page's own description kept, a structured-data record that names its
language and licence when `[project]` declares them, and its own `llms.txt` linked from
the root index when its docs ship one.

## Alternatives rejected

- **A separate marketing landing page.** A second page written to rank would drift from
  the README and read as a doorway, which 7.d forbids. The README is the landing page and
  the docs home mirrors it.
- **A hand-written `llms.txt`.** It would be stale by the next nav edit, silently — the
  failure 7.d names. Generating it in the publishing workflow from the built site was
  also rejected: the index would then appear in no pull request's diff and be reviewed by
  no one, where a generated file committed beside its generator is reviewed with the nav
  change that moved it.
- **`description:` front matter on every page, decision records included.** Rejected for
  decision records for the reason under *Gaps*; the mechanism is there for any page where
  the trade is worth it.
- **Deleting the figures so they cannot drift.** Rejected for the reason
  `tests/meta/test_adr_counts.py` gives: a number that tells a reader something is worth
  one test.

## Rule status

The decision above is mechanism. The conduct behind it — that every public surface
serves the newcomer first, is findable by people and machines, is legible in one screen,
and is one step from a first contribution, with every claim on it evidenced — binds
future decisions and survives a rewrite of any file named here, so under ADR-0020 it is
proposed as sub-doctrine **7.e — the open door**. It is carried on a separate branch,
because a ratified change to the canon yanks every earlier release (Constitution,
Article V.4); the operator can merge this record and its mechanism without the law, and
ratify the law when they choose.
