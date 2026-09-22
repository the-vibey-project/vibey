## Title
docs(design): draft the ADR for fitting the duration dilation φ from graded runs, when it is trusted, and how T(o) and the repair gradient are emitted

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 4: "**φ measured**: the dilation each
shortfall imposes on duration is fitted from predicted-versus-actual records. Only then is `T(o)`
computed and the repair ranking emitted as the gradient `−∇_d T`"; Acceptance: "φ is fitted from at
least N graded predictions, and N is recorded. Until then the report says "no gradient yet", as
today"; "Proposed child issues" 8: "Design needed first — fitting φ and emitting the gradient. Which
regression, how many graded runs before it is trusted, and how it is shown"). The original ask
requires "The repair ranking is the gradient, not a heuristic list".

The tree holds two unreconciled halves (integration clone, verified):
- `vibey-gh estimate` refuses: "φ is unspecified ... so nothing here computes `T(o)` or the repair
  gradient" (`src/vibey_tools/gh/vibey_gh/feasibility.py:31-33`), and its report says so
  (`REPAIR_REASON`, `vibey_gh/estimate_report.py:46-50`; `"repair": {"ranking": None, ...}` at `:118`).
- `vibey-gh forecast` applies a *configured*, unfitted φ: `PhiConfig` (`vibey_gh/delivery_estimate.py:288-305`),
  `φ_i = ((1-floor)/max(x_i-floor, ε))^exponent` (`:534-541`), multiplied into the time band
  (`:468-472`) from `[estimate.forecast] phi_*` (`vibey_gh/config.py:1356-1359`,
  `vibey_gh/cli.py:854-861`), and lists "first repair candidates" sorted by dilation (`:618-621`) —
  the heuristic list the ask forbids passing off as a gradient.
- The one graded estimator exists (`vibey_gh/estimation.py:140-195`: least squares with refusals,
  `grade`, `track_record`), but it has graded nothing: the published forecast shows `graded: 0` and
  "materials measured: 0/18" (`docs/estimate.md:14-16`).

This is a real design gap, not an operator question, so it is a spike. Sub-doctrines that bind the
answer: 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`, measurements drive defaults "never from
assumption"), 10.f (`doctrines.md:419`, "no gradient yet" until evidence exists), 10 (`doctrines.md:371-383`)
and 10.d (`doctrines.md:395-410`, an impossible job names its coordinate first), 7.c
(`doctrines.md:82-91`, every graded run in the ledger), 10.e (`doctrines.md:417`, one estimator and
one φ, never two), 12.c (`doctrines.md:455`, N and the regression's constants are keys), and 9.c
(`doctrines.md:351`, a claim of convergence needs evidence). vibey-gh stays stdlib-only
(`src/vibey_tools/gh/pyproject.toml:30`).

The deliverable is one draft ADR. No code changes.

## Required behaviour
1. Write exactly one file:
   `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-134-phi-gradient.md`.
   Change no file in the lane's clone; commit nothing.
2. Read end to end, and cite with verified `path:line` anchors: the φ note and `MEASURED_BY`
   (`feasibility.py:26-36`, `:93-119`), `DEFAULT_STAGES` (`:253-321`); `PhiConfig`,
   `_coordinate_phi`, `calculate` and `_first_repairs`, `_track_record` (`delivery_estimate.py`);
   `GradedEstimator.fit/predict/grade/track_record` (`estimation.py:151-195`) and its
   `nonnegative` refusal (`:143-174`); `REPAIR_REASON`, `STAGE_DURATION_REASON`, `COST_REASON` and
   `as_dict`'s `duration`/`cost`/`repair` (`estimate_report.py:38-50`, `:106-118`); the duration the
   estimate does compute (`vibey_gh/operation_estimate.py:135-138`); the forecast ledger's
   append-only digest chain (`vibey_gh/estimate_ledger.py:159-192`) and the billing reader's
   `elapsed_seconds` from event times (`:124-127`); the rule that a projection never re-enters as
   a measurement (`vibey_gh/fitloop.py:77-79`); `docs/estimate.md:14-16`.
3. Weigh at least these options, each against: identifiability with the data that exists or will
   exist, stdlib-only, 10.e (reuse `GradedEstimator` or name the capability gap it must be taught),
   whether the resulting ranking depends on evidence, and what "trusted" can mean:
   - (A) keep the configured `PhiConfig` constants (today's forecast; not fitted);
   - (B) one pooled exponent fitted on the log scale, `ln(T_actual / T0) = b + k · Σ_i z_i`, with
     the existing `GradedEstimator` (x = `Σ z_i`, y = the log ratio);
   - (C) one exponent per material (six), by ridge-regularised least squares shrunk toward the
     pooled exponent, solved in stdlib (normal equations by Gaussian elimination, an active set
     keeping every exponent ≥ 0);
   - (D) one exponent per coordinate (eighteen) by non-negative least squares;
   - (E) a non-parametric φ per coordinate (binned or isotonic).
   The ADR must state plainly that under (A) or (B), with one shared transform, `−∇_d T` orders the
   coordinates by value alone, whatever the evidence, and say whether that meets "the gradient,
   not a heuristic list".
4. `## Decision` recommends one option and states exactly, under these four sub-headings:
   - `### The regression` — the model (`T(o) = T0(o) · Π_i φ_i(d_i)`), the transform `z_i` (reuse
     `_coordinate_phi`'s floor and ε, `delivery_estimate.py:534-541`, or say why not), the
     estimator and its stdlib implementation (the class, module, interface and in-memory fake to be
     built, e.g. `PhiFitter` in `vibey_gh/phi_fit.py`), how a negative exponent is refused (a
     shortfall never shortens a run), and how it reuses `GradedEstimator` or names the gap.
   - `### When the fit is trusted, and how N is recorded` — the rule (a minimum number of graded
     runs as a declared `[estimate.phi]` key with its proposed default and the reasoning for it,
     plus any error test against φ ≡ 1, e.g. leave-one-out), exactly which fields are recorded
     with every emission (at least `n`, the required N, the errors compared, the fitted constants,
     and a digest of the graded records used), where they are recorded (7.c), and how a prediction
     never grades the fit that produced it (the `fitloop.py:77-79` principle).
   - `### How T(o) and the repair ranking are emitted and shown` — where `T0` comes from and what
     `T(o)` is while `T0` is unknown; the partial derivative `∂T/∂d_i` for a measured coordinate
     under the chosen model; the ordering (measured feasibility shortfalls first, as 10 and 10.d
     require, then the gradient by magnitude, then unknown coordinates as "measure first" — an
     unknown has no derivative); the exact JSON fields added to `OperationEstimate.as_dict()`
     (`duration`, `repair`) and the text lines of `lines()`; and how `DeliveryEstimator`'s
     `first_repair` (`delivery_estimate.py:618-621`) converges on the same ranking so there is one
     φ (10.e).
   - `### No gradient yet` — the exact report wording while the fit is untrusted, naming `n` of `N`,
     which replaces today's `REPAIR_REASON` (`estimate_report.py:46-50`).
5. `## Data this needs` lists, per graded run, every field the fit consumes — the estimate's state
   vector (value and source per coordinate) at prediction time, `T0` and its basis, the actual
   duration and how it is measured (event times, `estimate_ledger.py:124-127`), the stage reached
   and whether the path completed, a prediction id and the φ version that produced it — and for each
   field: its source, whether it exists today (with a `path:line` or "not yet"), and which #134 lane
   produces it (the probes `roadmap-134-*-probe*` / `roadmap-134-hardware-series-p3`, the billing
   export and the validation harness, #134 children 6 and 9). It states the variation the fit
   needs (a coordinate that never varies across runs has no identifiable exponent).
6. Out of the ADR's scope, and said so: the cost integral (#134 child 7), the billing export (child
   6), the validation harness's implementation (child 9), the probes themselves, and customer
   pricing (#86/#88).

## Where to change
- Create only the ADR draft above (Markdown, outside the clone).

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Fitting the duration dilation phi and emitting the repair gradient` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**`, `**Cites:**` naming 8.g (`doctrines.md:316-324`), 10.f
      (`doctrines.md:419`), 10 (`doctrines.md:371-383`), 10.d (`doctrines.md:395-410`), 7.c
      (`doctrines.md:82-91`), 10.e (`doctrines.md:417`), 12.c (`doctrines.md:455`), 9.c
      (`doctrines.md:351`) and ADR-0017 (one estimator, `estimation.py:4-10`).
- [ ] `## Context` with at least 12 verified `path:line` anchors, including `feasibility.py:31`,
      `delivery_estimate.py:534`, `estimation.py:151`, `estimate_report.py:46` and `fitloop.py:77`.
- [ ] `## Options considered` with A-E, each with consequences.
- [ ] `## Decision` with the four sub-headings of behaviour 4, each covering every point listed.
- [ ] `## Data this needs` covering behaviour 5.
- [ ] `## Consequences`.
- [ ] `## Lanes this unblocks`: a table (slug-to-be, title, one-line scope, files, depends on), each
      lane sized for a 20B lane (one source file plus its interface, and one test file), e.g. the
      fitter, the `[estimate.phi]` keys, the estimate's `T(o)` and ranking, the report's "no
      gradient yet" wording, and the forecast's convergence onto the same φ.
- [ ] `## Open decisions for the operator`: quote #134's open questions 1, 2 and 3 verbatim from
      `issue-audit/updates/134.md`, stated as unanswered here.
- [ ] `## Verification owed` (at least: the fit reproduced from the recorded runs once N is reached,
      and #134's "shown to reduce time-to-peak on a real recovery").

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 -c 'import re; from pathlib import Path; p = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-134-phi-gradient.md"); assert p.is_file(), "the ADR draft was not written"; text = p.read_text(encoding="utf-8"); assert text.startswith("# Fitting the duration dilation phi and emitting the repair gradient"), "wrong title line"; required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context", "## Options considered", "## Decision", "### The regression", "### When the fit is trusted, and how N is recorded", "### How T(o) and the repair ranking are emitted and shown", "### No gradient yet", "## Data this needs", "## Consequences", "## Lanes this unblocks", "## Open decisions for the operator", "## Verification owed", "feasibility.py:31", "delivery_estimate.py:534", "estimation.py:151", "estimate_report.py:46", "fitloop.py:77", "doctrines.md:316", "doctrines.md:419", "doctrines.md:417", "doctrines.md:455"]; missing = [h for h in required if h not in text]; assert not missing, f"missing: {missing}"; anchors = re.findall(r"[\w./-]+\.(?:py|sql|toml|md):\d+", text); assert len(anchors) >= 12, f"only {len(anchors)} path:line anchors"; options = [o for o in ("(A)", "(B)", "(C)", "(D)", "(E)") if o not in text]; assert not options, f"options not weighed: {options}"; questions = [q for q in ("**\"Billing\" in the title:**", "**Agency probes need network and credentials**", "**Which endpoints define \"network\" for each stage**") if q not in text]; assert not questions, f"open questions not quoted verbatim: {questions}"; placeholders = [w for w in ("TBD", "lorem", "TODO") if w in text]; assert not placeholders, f"placeholders left in the draft: {placeholders}"; print("ADR draft complete")'
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any code, migration or test; the probes; the cost integral, the billing export and the
  validation harness (#134 children 6, 7, 9); customer pricing (#86/#88).
- Answering any of #134's open questions.
- The tree's `docs/` and ADR directories. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
