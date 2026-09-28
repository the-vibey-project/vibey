---
id: skill-20-sources-and-method-d728c97724
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-reference/SKILL.md
requires: ["skill-19-quick-reference-b094b340c4"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written as **judgment guidance rather than a catalogue** —
the 23 GoF patterns are exhaustively documented for free elsewhere and reproducing them
adds nothing. The durable material rests on the primary pattern literature (GoF, Fowler,
Hohpe & Woolf, Evans, Nygard) and on failure modes reported consistently across two
decades of practice. Three targeted searches were run in **August 2026** on the areas where
the picture could have moved: the current standing of the GoF critique, distributed-pattern
practice, and the emerging agentic pattern language.

**⚠️ A note on §2 → `patterns-foundations-gof-and-alternatives` and §16 specifically.** This is a domain with real, live disagreement
among competent practitioners, and I have tried to **give each side its strongest form
rather than adjudicate.** Where I take a position — §2.3 → `patterns-foundations-gof-and-alternatives`'s synthesis, §14's asymmetry
argument — I've marked it as the position this document takes, not as consensus.

**Search log** (August 2026): GoF relevance and critique in modern languages ·
distributed-system patterns (saga, outbox, circuit breaker, CQRS, event sourcing) in 2026
practice · LLM and agentic design patterns and their taxonomies.

**Primary and near-primary sources consulted (selected):**
- **python-patterns.guide** for the sharpest form of the "patterns as language
  deficiencies" argument; a **Microsoft archived blog post** and related commentary for the
  Smalltalk-origins rebuttal; **Fluent Python** Ch. 10 (and Ralph Johnson's quote via its
  epigraph); **Kansas State's CC 410 textbook** for the standard academic critique;
  practitioner posts from 2026 for the "post-pattern"/enlightened-simplicity framing and
  the start-simple heuristic
- **microservices.io** (Chris Richardson) for the saga and outbox definitions; 2026
  practitioner write-ups for the choreography/orchestration step heuristic, the documented
  order-loss and Event-Sourcing-for-CRUD cautionary cases, and the
  event-notification/CQRS/ES proportions; an academic survey of microservice architecture
  patterns for the circuit-breaker adoption finding
- **Anthropic's *Building Effective Agents*** framing (workflows vs. agents) as reported
  in practitioner coverage; **Databricks' agent system design patterns** documentation;
  **arXiv 2601.19752** on agentic design patterns as a system-theoretic framework, which
  notes FM/agent patterns being presented in GoF format; 2026 pattern catalogues describing
  the Ng / Anthropic / emergent taxonomy overlap

**Confidence statement.** **High confidence** in §1 → `patterns-foundations-gof-and-alternatives`, §3–§7 → `patterns-foundations-gof-and-alternatives`, `patterns-architectural`, §9–§11 → `patterns-distributed-concurrency-and-messaging`, §13–§15 → `patterns-llm-agentic-and-legacy-migration` — these rest on
the primary pattern literature and long-stable practice rather than on anything searched.
**High confidence** that the §2 → `patterns-foundations-gof-and-alternatives` debate exists in the form described, with **explicitly no
position on who is right**, because it is a values disagreement about cost and clarity that
evidence does not settle. **Moderate confidence** in §8 → `patterns-distributed-concurrency-and-messaging`'s specific heuristics — the
choreography-vs-orchestration step counts and the event-notification/CQRS/ES proportions
are **practitioner rules of thumb from individual write-ups, not measured findings**, and
should be treated as starting points rather than thresholds. The cautionary cases in §8 → `patterns-distributed-concurrency-and-messaging` are
**reported anecdotes**; I've included them because they're representative of a widely
described pattern of failure, not because any single one is authoritative. **Lower
confidence in §12 → `patterns-llm-agentic-and-legacy-migration`**, and deliberately so: the agentic pattern language is 2–3 years old,
naming is unstable, several sources are vendor-adjacent with obvious incentives, and
**multiple competing taxonomies is exactly what an immature pattern language looks like** —
which is why §16.7 leaves the "real patterns or vendor framing" question open rather than
resolving it.
