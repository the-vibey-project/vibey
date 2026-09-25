# 0062 — The Beauty Law and its bar

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrine 12.k, drafted in the change that carries this record and awaiting the operator's ratifying merge (Constitution Article II.3); sub-doctrines 10.f, 12.c, 12.e, 12.g and 12.h · **Related:** ADR-0020, ADR-0059, ADR-0063 · **Evidence:** `develop` at `0a2f856e`, read 2026-09-25

**Owes:** the conduct is sub-doctrine 12.k, drafted in the same pull request for the
operator's ratifying merge (ADR-0020: the record argues, the canon states). This record
also owes the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.
Both are done in the change that carries it. Every check the bar names that does not exist
yet is owed by the client-suite lanes, and is named under *Consequences*.

## Context

On 2026-09-25 the operator ruled, in their words:

> "ALWAYS FULLY COMPREHENSIVE, FULLY UP TO DATE, INSANELY BEAUTIFUL, INSANELY
> SOPHISTICATED, INSANELY GORGEOUS, INSANELY WOW-FACTOR PRODUCING and INSANELY POWERFUL
> AND FUN FOREVER AMEN!"

They added that beauty and user-friendliness come first, and made a client suite a gate on
the 3.0.0 release: a desktop app, mobile and web apps, the VS Code extension raised to the
same standard, and one system of notifications and sounds.

Nothing in the canon said this. On `develop` at `0a2f856e`:

- There was **no design system.** The docs site's dark palette lives in three copies of
  `vibey.css` that have drifted apart. The paper has its own 17-colour light palette. The
  extension uses VS Code's variables and nothing of its own.
- There was **no checkable standard** for any surface a person uses: no contrast rule, no
  first-run target, no requirement that empty and error states be designed.
- **Nothing decided when a surface was good enough to ship.** The gates measure
  correctness, coverage and types. None of them looks at a screen.

A ruling like this one can fail in two opposite ways. Left as a slogan, nobody can hold a
change to it. Turned entirely into automated checks, it hands the judgement of beauty to a
machine, and a machine cannot make that judgement. 12.e forbids exactly that.

## Decision

1. **The conduct is canon.** Sub-doctrine 12.k, *beauty is the first measure*, is filed under
   12 (*Humans first*). It quotes the ruling verbatim, puts beauty and user-friendliness
   first on every surface a person touches, and ships nothing that is not fully
   comprehensive, current and a joy to use. It keeps the judgement of beauty with a human
   and has automation surround it (12.e). The parent is the operator's call at the merge:
   9 (*The vibe*) is the alternative. 12 was chosen because the rule is about what the
   machine owes the person in front of it, which is 12's subject, while 9 is about
   momentum in the work itself.
2. **The bar is a document, and every item is checkable.**
   [`docs/design/beauty-bar.md`](../../design/beauty-bar.md) states eleven items, BB-1 to
   BB-11. Each has a rule and a check, and each check is marked *machine*, *reviewer*, or
   both:
   - BB-1 one token-based design system;
   - BB-2 dark and light themes, with Light, Dark and System modes (System by default,
     live, and kept per device), an addition the operator made the same day;
   - BB-3 WCAG 2.2 AA, screen readers, keyboard, reduced motion and dynamic type;
   - BB-4 under 60 seconds from install to first result, with a guided first run;
   - BB-5 purposeful motion at 60 fps;
   - BB-6 every empty, error and loading state designed;
   - BB-7 the parity matrix;
   - BB-8 a release gallery signed off by the operator;
   - BB-9 dependency and platform currency checked by CI;
   - BB-10 notifications and sounds as one system;
   - BB-11 a stable channel from `main` and a nightly channel from `develop` on every GUI
     platform, installed side by side with distinct IDs and icons, stable always the
     default: an addition the operator made the same day.

   The canon cites the bar rather than restating it, so the bar can be refined in a pull
   request without a new ratification. What cannot move without one is the rule that
   there is a bar and a person closes it.
3. **An unchecked item is not a met item.** Where the automated check an item names does
   not exist yet, the item is reported as unchecked, never as passed (10.f).
4. **The operator's sign-off closes the gate.** BB-8 is the one item no machine can pass.
   The gallery is generated, the sign-off is recorded against the exact release commit, and
   a sign-off for any other commit does not count.
5. **Tolerances are declared.** The currency window in BB-9 and the reference devices in
   BB-5 are configuration (12.c, 12.h), not constants in a check.

## Consequences

- **Most checks do not exist yet.** The design tokens and their drift test (BB-1, BB-2) are
  the design-system lane's. The parity meta test (BB-7) needs `@vibey/core`'s command
  table. The first-run timer, frame traces and accessibility audits (BB-3 to BB-5) arrive
  with each client. BB-9's currency check and BB-10's notification tests are owed too.
  Until each lands, the release gate reports its item as unchecked.
- **Existing surfaces fail the bar today.** The docs site has no light theme and three
  drifted stylesheets, and the extension has no walkthrough. That is the honest starting
  point, not a regression.
- **The bar costs time.** Designed states, two themes and a gallery per release are real
  work on every surface. The ruling accepts that cost. 12.g still applies: the checks must
  stay fast, and a check made faster by measuring less is a weaker gate.
- **A human is in the release path by design.** A release cannot ship while the operator
  is away and the gallery is unsigned. That is the point of 12.e's line, not a defect in
  the automation.

## Alternatives considered

- **An ADR alone, no canon.** Rejected: the rule binds future decisions and is about
  conduct, so 12.b and ADR-0020 require it in the canon.
- **Put the whole bar in the canon.** Rejected: thresholds such as 60 seconds or 60 fps
  are mechanism, and would need a ratification to tune. The canon states the law and cites
  the bar.
- **Let automated checks alone pass a release.** Rejected by 12.e: whether a thing is
  beautiful could reasonably differ between careful people, so it stays with a human.
