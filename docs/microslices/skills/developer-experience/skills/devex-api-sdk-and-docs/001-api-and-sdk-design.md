---
id: skill-api-and-sdk-design-cf8d7a15ef
purpose: api and sdk design
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-api-sdk-and-docs/SKILL.md
requires: []
links: ["skill-documentation-64c297e083"]
---

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
