---
name: devex-api-sdk-and-docs
description: "Use when designing an API or SDK a developer will call, or writing and restructuring the documentation they read: method placement and discoverability, consistency, defaults, autocomplete, time-to-first-call, idempotency keys, API versioning and deprecation policy, Diataxis (tutorial, how-to, reference, explanation), README first screen, executable docs tested in CI, docs style, and docs feedback. Triggers on API usability, SDK design, time to first call, Stripe-style versioning, deprecation, Diataxis, README, docs-as-code. Companion to the other developer-experience skills."
---

# Developer Experience: API and SDK Design, and Documentation

> **Part 3 of 5** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: API and SDK design; Documentation. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-interfaces-onboarding-and-agents`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

## API and SDK design

The strongest evidence here is experimental: in Myers & Stylos's usability studies, finding a method was 2.4 to 11.2 times faster when it sat on the object developers expected, and requiring a factory or helper object slowed people down. Robillard & DeLine found documentation to be a top obstacle in learning APIs.

- **Put methods where people look.** Place the action on the type that owns the data; test placement with a quick think-aloud study of five developers.
- **Be consistent.** Same verb, same argument order, same error shape everywhere.
- **Make the default work.** The one-line call should do the common thing; options are additive.
- **Optimize for autocomplete.** Descriptive names, typed parameters, and doc comments that appear in the editor.
- **Design time-to-first-call.** Track how long a new user takes to make a successful request; the [Nordic APIs write-up](https://nordicapis.com/why-time-to-first-call-is-a-vital-api-metric/) explains the metric.
- **Make writes safe to retry.** Idempotency keys, as Stripe does.
- **Version deliberately.** [Stripe's date-based versioning](https://stripe.com/blog/api-versioning) pins each account to the version it started on and lets it upgrade on its own schedule; whatever scheme you pick, publish it.
- **Deprecate with notice.** Announce, warn at runtime with a link to the migration guide, give a dated removal window, and keep a changelog readers can subscribe to.
- **Combine two review methods.** Heuristic evaluation and think-aloud testing found mostly independent problems, so neither replaces the other.

## Documentation

Split docs by the reader's need, lead with something that runs, and keep examples tested.

| Type | Reader's question | Rule |
| --- | --- | --- |
| Tutorial | "Teach me" | One guided path to a working result in minutes; no choices |
| How-to guide | "Help me do X" | Steps for one goal; assumes basic knowledge |
| Reference | "What exactly is X?" | Complete, accurate, generated from code where possible |
| Explanation | "Why is it this way?" | Background and trade-offs; no steps |

This is the Diátaxis model. I read it only through secondary sources (the diataxis.fr site could not be fetched), and its value rests on practitioner adoption rather than controlled studies.

- **README first screen:** what it is, one install command, one runnable example, where to go next.
- **Executable docs:** run code samples in CI (doctests, or snippet tests) so examples never rot.
- **Style:** second person, active voice, present tense, one idea per sentence, descriptive link text (Google's developer documentation style guide is the usual reference).
- **Search and navigation:** every page answers one question, has a stable URL and links to the next step.
- **Versioning:** docs match the released version, with a clear switcher.
- **Feedback:** a visible "was this useful" control and an edit link that goes straight to a pull request.
- **Copy-paste friendly:** commands without prompt characters, and sample output shown separately.
