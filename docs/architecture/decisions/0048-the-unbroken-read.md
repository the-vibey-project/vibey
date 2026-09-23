# 0048 — A job that consumes an accumulating record reads every datum in the gap, and proves its span

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrines 10.f, 10.g which this record implements, 12.b, 12.e · **Related:** ADR-0039, ADR-0040, ADR-0047 · **Evidence:** the QwenStorm run of 2026-09-22–23 and the paper's own frozen extraction at `src/vibey_tools/gh/docs/qwenloop-storm-2026-09-20.json`

**Owes:** nothing new as conduct — 10.g is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md` (`tests/meta/test_adr_counts.py`),
and a nav entry in `properdocs.yml`.

## Context

The storm accumulates evidence continuously: `progress.log` grows a line per lane start and
end, `integrated.txt` and `abandoned.txt` grow a line per settlement, each lane leaves a
`result.json` and a `lane.log`, and `bench/results.jsonl` grows a row per measurement. The
research paper's quantitative claims are drawn from exactly this kind of material — its
current figures come from a frozen extraction of thirteen run directories, cited with an
`observed_at` cutoff so a reader can reproduce them.

A periodic job that turns that stream into published figures has one failure mode that
matters more than all the others: reading *most* of it. A gap in the input does not announce
itself. The totals still add up, the rates still look plausible, and the figure is published
with a confidence the data no longer supports.

The obvious implementation has exactly that bug. "Take everything newer than the last run"
compares timestamps, and a timestamp comparison loses:

- records written in the same second as the cutoff, on either side of it depending on
  resolution and rounding;
- records that arrive out of order, which is normal when several producers append;
- records written while the job itself was running, which a naive end-of-run stamp then
  declares already consumed;
- everything, silently, if a clock moves.

None of those leave a trace. That is what makes it worse than crashing.

## Decision

A job that consumes an accumulating record reads everything written since its own last run,
and can account for the span it covered.

**The watermark is a position in the data, not a moment in time.** For an append-only stream
it is a byte offset; for a set of records it is an identity set; where the source defines a
sequence, it is that sequence. Each of these is exact where a timestamp is approximate, and
each makes "what have I already seen" a question about the data rather than about a clock.

**The watermark advances only after the data it covers is durably recorded.** A crash before
that point re-reads; a crash after it does not. This makes consumption at-least-once, and the
duplicates that follow are removed by identity, because an idempotent consumer that
occasionally repeats itself is the only safe shape — at-most-once loses records exactly when
something has already gone wrong, which is the worst moment to start losing them.

**An unreadable source is reported, never stepped over.** The run names the source and the
span it could not cover and leaves its watermark unmoved, so the next run covers the same
ground. Skipping to stay on schedule trades a visible delay for an invisible hole.

**A figure computed over an unknown subset is not evidence.** This is 10.f applied to the
input rather than to the claim. A total, a rate or a chart drawn from a read that cannot
state its own span asserts a precision it does not have, and is more misleading than no
figure, because a missing figure invites the question and a wrong one settles it.

## Consequences

Consumers here carry a little machinery they would otherwise not need: a durable watermark
beside the data, an identity for every record, and a de-duplicating append. That cost is
accepted because the alternative is not "slightly less accurate" — it is a published number
nobody can tell is wrong.

It also constrains what a periodic job may do to the research paper. Regenerating a derived
figure from a ledger whose span is provable is ordinary bookkeeping and is automated under
12.e. Rewriting a dated extraction in place is not: the paper cites
`qwenloop-storm-2026-09-20.json` *as of* a cutoff, and a file that silently becomes a
different measurement under the same name destroys the reproducibility the citation exists to
provide. New evidence is a new record with its own cutoff, and the frozen one stays frozen —
an instance of the ledger being append-only rather than an exception to it.
