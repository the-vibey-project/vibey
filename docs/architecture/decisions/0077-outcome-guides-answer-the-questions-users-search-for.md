# 0077 — Outcome guides: the project answers the questions its users search for

**Status:** proposed · **Date:** 2026-09-30 · **Extends:** ADR-0076 (discoverability and the first hour are deliverables) · **Cites:** doctrines 1 and 7; sub-doctrines 7.b, 7.d, 10.f and 12.e · **Related:** ADR-0032, ADR-0033, ADR-0040 · **Evidence:** `develop` at `8ebf396dc`, read 2026-09-30 · **Canon:** none; this record proposes no sub-doctrine

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record and for the guides;
`docs/llms.txt` regenerated from that nav. All are in the change that carries this record.

## Context

ADR-0076 made the first screen and the first hour deliverables: a stranger learns what
vibey is and how to give it a first contribution. It did not answer the question most
visitors arrive with, which is neither "what is this?" nor "how do I contribute?" but "can
this do the thing I need?". People search for outcomes — running coding agents without
sending code to a vendor, capping what agents spend, keeping an audit trail, reviewing an
agent's change before it merges — and the answers were in the repository, spread across a
CLI reference of more than a thousand lines, a configuration reference, a measured
requirements page, seventy-six decision records and a research paper. Measured at
`8ebf396dc`:

- **Each answer existed in pieces.** The sovereign path's hardware floor is in
  `docs/reference/system-requirements.md`, its switch in `docs/reference/cli.md`
  (`vibey worker --engines`), its reason in ADR-0038 and ADR-0064, and its limit — a
  single local engine reviewing its own work — in ADR-0035. No page put them in the order
  a person acts in.
- **The guides were written for people who already knew the system.** `docs/guides/` held
  operator recipes named after components (Kubernetes, Ollama, the Sabbath), not after
  what a reader wanted to achieve.
- **Nothing held a practical page to its evidence.** The first screen's links are checked
  (`tests/meta/test_first_screen.py`); a guide's were not.

The readers are not one audience, and the order matters. First come open-source developers
who might use vibey and then contribute to it; then practitioners and teams who need one of
these outcomes delivered; then engineering evaluators deciding whether to adopt it. A page
written for the evaluator first reads like a brochure to the developer; a page written for
the developer first, with its evidence and limits in plain view, serves the evaluator
better than a brochure would.

## Decision

**The documentation answers the outcomes its users search for, one guide per outcome,
under `docs/guides/outcomes/`, with an index titled "What do you want to do?".** The six
guides at this record's date answer: running coding agents entirely on your own hardware;
capping agent spending and seeing where it went; keeping a tamper-evident record of what an
agent did; reviewing an AI-built change before it can merge; whether an agent can deploy
without holding cloud secrets; and using vibey in a regulated environment. The deployment
guide was reshaped while it was written: it began as "how to deploy without storing
secrets", and the code showed opt-in Azure stages that hold no credential and wait for
consent, but no workload identity, no `what-if` before consent and no recorded real-Azure
run. So its answer is "partly, and not yet for production", with those gaps as its limits.

1. **Every outcome guide has the same shape.** Its title is the question a practitioner
   searches for. The next block is a one-sentence **short answer** a search engine or an
   AI reader can quote whole, and the same sentence is the page's `description:` front
   matter, so the page's meta description and its line in `docs/llms.txt` are that answer.
   Then the steps, as commands that exist; then **The evidence**, each claim beside the
   code, test, decision record, reference section or paper section that proves it; then
   **Limits**, stated plainly; and last **Improve this guide**, which names the page's own
   file and starts from the first-hour path in `CONTRIBUTING.md`, because contributors
   come first. A guide reads in under five minutes; depth is one link down.
2. **The audience order is fixed.** Open-source developers who might use and contribute,
   then practitioners and teams who need the outcome, then evaluators. It shows in the
   order of every guide — what to run before what proves it — and in the order of the
   index, which leads with the outcome a developer reaches for first and ends with the
   regulated-environment checklist an evaluator brings to an assessment.
3. **A guide never claims what the code does not evidence.** A capability is written only
   when the code does it at the guide's date, and then with its link. Where vibey stops,
   the guide says so in the same plain voice ("vibey records X; mapping X to a control is
   the adopter's call"). No guide claims a compliance status or certification — SOC 2,
   FedRAMP, HIPAA, ISO 27001 or any other — that the repository does not itself map; a
   guide may list the mechanisms a reader would bring to such an assessment, each with its
   evidence, and must say it is not an attestation. An outcome vibey does not genuinely
   deliver gets no guide, or a guide reshaped to the part it does deliver.
4. **The guides describe vibey, never a person.** They say what the software does and how
   to use it. They advertise no individual or service and carry no testimonials, adopter
   lists or figures invented to look popular (the same line ADR-0076 draws under 4.a).
5. **Findable the honest way.** Question-shaped titles and quotable answers are how a page
   matches the words people search with (7.d). No keyword lists, hidden text or doorway
   pages; the index and the guides sit in the site navigation after the beginner's
   on-ramp and before the reference, and both first screens link the index.

**What checks it.** `tests/meta/test_outcome_guides.py` holds every guide to the shape a
machine can check: a question for a title; a short answer identical to the `description:`
and short enough that `docs/llms.txt` does not cut it; the evidence, limits and improve
sections, in order, with *Improve this guide* last and linking the first hour; a prose
length under the five-minute ceiling; every link landing — a page, an anchor that names a
heading, or a path in this tree behind a GitHub URL; and the index and the navigation
listing every guide. `tests/meta/test_llms_txt.py` fails until the index an AI reader
fetches lists the new pages. Whether a guide's sentences are true of the code — the claim
matches the linked line, the limit is really the limit — is judged on every pull request
by the exact-head review, because a regular expression can find a link but not weigh it.

## Consequences

**Good.** A developer who arrives with a problem finds the commands, the proof and the
catch on one page, and one link from contributing a fix. A team lead or evaluator sees the
same page with its evidence and its limits in plain view, which is what an assessment
starts from. Answer engines get a sentence they can quote that is also true.

**Bad.** Six more pages restate, in order, facts owned elsewhere, and restated facts drift.
The link check catches a moved heading; it cannot catch a changed default that a guide
quotes in prose. The review gate is the guard there, and a stale guide is a good first
issue rather than a hidden one. Every new guide is one more nav entry and one more
regeneration of `docs/llms.txt`.

**Neutral.** The shape is generic: any page under `docs/guides/outcomes/` is held to it
from the moment it exists, with nothing to register.

## Alternatives rejected

- **Answers in a FAQ on the README.** The README already carries *Questions people ask*
  for the first questions; an outcome needs steps, evidence and limits, which would bury
  the first screen ADR-0076 protects.
- **One page per audience** (a developer page, a team page, an evaluator page). The same
  facts three times, drifting three ways, and an evaluator page is the brochure this record
  refuses.
- **Landing pages written to rank.** A page whose purpose is search rather than a reader
  is a doorway page, which 7.d forbids.
- **Checking the prose by pattern** (forbidden words, required phrases). A list of words
  cannot tell a claim from its negation; the structure and the links are checked by
  machine, and the truth of each sentence by review.

## Rule status

The conduct this record applies — the problem first, every public surface findable and
serving the newcomer first, every claim evidenced — is already doctrine 1, sub-doctrines
7.b, 7.d and 10.f, and the open door ADR-0076 proposes as 7.e. The decision above is
mechanism under that law, so it proposes no sub-doctrine and changes no canon text; a
ratified canon change would yank every earlier release under the Constitution, Article V.4.
