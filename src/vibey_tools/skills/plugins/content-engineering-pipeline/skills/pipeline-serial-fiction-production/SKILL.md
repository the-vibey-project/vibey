---
name: pipeline-serial-fiction-production
description: "Use when a multi-volume or episodic work (log, letter, journal, or found-document fiction) is written as many small units and later typeset and assembled into books; triggers on canon continuity across volumes, per-entry headers and computed facts, generating chapters from drafts, a PDF that went stale after an edit, standing style rules, found-document forms, or a postmortem of a series built by hand."
---

# Serial Fiction Production

A serial is written one unit at a time (a log, a letter, a bulletin, a hearing
day) and read as a whole. Two things go wrong at scale. The canon drifts: a
name, a number or a ritual established in unit 40 is contradicted in unit 400.
And the files drift: a unit is edited, and a typeset page, a manuscript chapter
or a finished book somewhere downstream keeps the old words. Both failures are
quiet, both grow with every unit, and both are cheap to prevent early and very
expensive to find at the end.

This skill owns the layer between novel architecture
(`pipeline-novel-conversion`) and release engineering
(`pipeline-book-release-engineering`): drafting units against a canon, and making
every downstream file a pure function of the drafts. It was extracted from a
three-volume log novel of 248 logs and eleven found-document forms, whose first
full build failed in CI for every book and exposed most of the patterns below.

## The governing rule: one source, every other file derived

The draft of a unit is the only file anyone writes for that unit. Everything
downstream is generated from it, and the generation is provable:

```text
drafts ──► lint ──► per-unit manifest ──► typeset units ──► manuscript chapters ──► books
              │            │                    │                   │                │
           rules as     parameters        regenerate to a      regenerate to a    release
            a gate      in a file         temp dir, compare    temp dir, compare   gates
```

Every arrow needs three things:

1. **A generator**: a command, not a procedure. If building a unit requires
   remembering which arguments to pass, the arguments belong in a file.
2. **A `--check`**: regenerate into a temporary folder and fail on any
   difference from what is committed, naming the unit and the command that fixes
   it.
3. **A test that runs the check without the heavy toolchain**, so the chain is
   exercised on every change in seconds and CI fails before LaTeX starts.

Do not compare bytes when a build embeds a document ID or timestamps. Compare
what the reader sees (page count, text per page), and normalise what the reader
cannot see (unused macro definitions, trailing blank lines) explicitly, with the
reason written next to the normaliser, so the check never hides a real change.

## The per-unit manifest

Whatever varies per unit and is not prose (the date, computed numbers, a
cabin temperature, a print time, a form name, an attachment flag) is recorded in
one machine-readable manifest that the generator reads. A driver that sets those
per batch in a shell script, or a scratch directory, is invisible manual state:
the next person cannot regenerate a single unit.

When the manifest does not exist yet, **bootstrap it from the committed
output**, then run the drift check. That is the cheapest audit available. In the
worked example it showed that most units reproduced exactly, that two had been
edited by hand outside the generator, and that one unit still printed an old
form that every later unit had moved past.

## Computed facts

Anything a reader could check is computed from published inputs, not typed:
dates and day counts, light-time delay, orbital geometry, a journey's transfer
orbit, an anniversary, a running counter. Test the computed values the story
leans on at the specific dates it leans on them. A counter the author increments
by hand ("a thousand and twelve days open") is a number that will be wrong in
exactly one unit; derive it from one anchor, or lint it.

When the plot depends on a calendar (a window, a margin, a deadline), put the
calendar in code first and write against it. The worked example's ride home was
computed as a real transfer orbit, which exposed that light time from the ship
to each planet crosses on one specific day, a fact a character then gets to
notice.

## Canon is searched before it is written

Before drafting a unit, search the whole corpus for every name, number, date,
ritual and phrase it touches, and read the nearest earlier unit in the same
thread. Then check the author's decision documents for locked rulings. Most
continuity errors are not forgotten facts; they are facts that were never looked
up.

- **Invent as little as possible.** A new named person, date or quantity is a
  decision. If one is needed, mark it proposed in the handoff and verify it
  against the corpus: a surname, a state, a month.
- **Excerpts must reappear verbatim.** A flash-forward printed early (a
  testimony fragment, a quoted record) is a promise that the full document will
  contain those exact words. Build the later document from the earlier text, and
  diff it.
- **Record what each unit established** in one machine-readable row of the writing
  map, written when the unit is. The map is the canon ledger the next unit's
  search starts from.
- **Reconcile the decision documents with the text, honestly.** When the written
  text supersedes a locked decision, append a dated entry marked *open* for the
  author. Never rewrite the locked entry, and never let the books and the bible
  disagree silently.

## Standing rules are gates

Rules the author states in conversation (banned characters and words, no
scaffolding the reader would see, which characters appear in every unit, no
contact details, how a faith or a name is handled) are written into a linter in
the repository the first time they are stated, with tests that each rule catches
what it names.

- Run it on **every** volume. A volume that predates a rule reports its legacy
  hits as warnings, with a `--strict` switch, so the policy is explicit rather
  than accidental.
- Lint the writing map and the manifest as well as the prose: they are source
  too, and the first unescaped character in a note stops the document that
  renders them.
- A frame break (a planning label such as a chapter code, or a reference to the
  book's own structure from inside it) is an error in every unit. In the worked
  example the linter found one in the 82nd unit that every human pass had missed.

Prose-level canon (who believes what, who reads which text) cannot be linted.
It belongs in the writing map and the decision log, and in the search before
drafting.

## Found-document forms

When a work includes documents (wire copy, a journal, a hearing record, a speech
and its earlier draft, a handwritten card, a field report, a relay printout), give
each form its own builder, selected by a declared `STYLE` at the top of the
draft. The draft stays plain text; the book importer converts from the draft, not
from the typeset form, so the form can be redesigned without touching a chapter.

**Look at every form as a page before accepting it.** Ruled lines that do not meet
the text, margin notes that run off the page, and a header that reads as noise were
found only by rendering the page and viewing it. A form that cannot be shown to be
legible is not finished.

## The batch loop

Units are written in small batches, and each batch is closed the same way:

1. Gather canon for the batch (search, then read).
2. Draft, then fix what the search turns up before building.
3. Lint; build; look at one rendered page of any new form.
4. Record what each unit established in the writing map.
5. Run the full chain check; commit; push.
6. Report what was written, what was fixed, and what new canon now exists, and
   name anything unconfirmed rather than burying it.

A batch is not done because it was typeset. It is done when the drift checks
pass, because that is the only state in which the next batch starts from truth.

## Determinism across machines

A build that passes on the author's machine and fails on the CI runner has not
been engineered. Vendor anything whose packaging varies by distribution (in the
worked example, one TeX distribution shipped a font family in two packages and
the other in one, which stopped every book until the fonts were committed with
their licences and loaded by path). Pin dates. Compare page text, not bytes,
because a document ID legitimately changes with a font path. State in the
repository why each choice was made.

## Retrospective lessons made executable

| Manual discovery | Durable gate |
| --- | --- |
| The per-unit header numbers lived in a scratch script | per-unit manifest read by the generator |
| A typeset unit no longer matched its own draft | `--check` at every arrow, run as a unit test |
| A unit was hand-edited outside the generator | bootstrap the manifest from output; the first diff finds it |
| One unit kept an old form every later unit had left | the same drift check, by form |
| A planning label reached a reader | frame-break lint on every unit |
| A banned word survived 17 times in an early volume | rule applied to all volumes; legacy hits are explicit warnings |
| The writing map could not be regenerated, and had gone stale | map composed from its sources; map notes linted for LaTeX safety |
| A second, older copy of a builder diverged | one builder; the old path forwards to it |
| A flash-forward excerpt was reworded in the full record | later documents built from the earlier text and diffed |
| A date moved and three documents kept the old one | the calendar in code; tests pin the values the story needs |
| The decision documents and the text disagreed in silence | dated entries appended and marked open for the author |
| CI never ran the existing tests or the series checks | tests and chain check are the first CI steps |

## Operating procedure

1. Put the manifest, linter, generators and chain check in the repository
   before the second volume, not after the third.
2. Before each batch, search the corpus; after it, record what it established.
3. Treat every hand edit of a generated file as a bug in a generator.
4. Make the chain check the first CI step after unit tests, and trigger CI on
   changes to the source directories.
5. Rebuild and read at least one rendered page of any new form.
6. Hand the author a short list of open decisions with each batch.
7. Release through `pipeline-book-release-engineering`, which owns the gates
   from a locked manuscript to evidence.

## References

- `pipeline-novel-conversion`: architecture before prose; this skill takes over
  when the architecture exists and the units are being written.
- `pipeline-book-release-engineering`: the release graph and its gates.
- `writing-craft` (`narrative-structure`): the craft this skill assumes and does
  not teach.
