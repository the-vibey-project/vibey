---
id: skill-how-ai-prose-fails-peer-reviewed-evidence-50f1140960
purpose: how ai prose fails peer reviewed evidence
source: src/vibey_tools/skills/plugins/writing-craft/skills/prose-mechanics/SKILL.md
requires: ["skill-punctuation-as-craft-d23e0baa6c"]
links: ["skill-overriding-ai-prose-defaults-e0871599e3"]
---

## How AI prose fails: peer-reviewed evidence

The convergence of evidence on LLM writing style (Kobak et al., *Science Advances* 2025; Reinhart et al., *PNAS* 2025; Padmakumar & He, ICLR 2024; Liang et al., ICML 2024) shows that **post-training (RLHF and instruction tuning), not base-model pretraining, creates the recognizable "AI voice."**

### The statistical signature of AI prose

**Excess vocabulary**: *delve, intricate, notably, crucial, pivotal, underscore, navigate, comprehensive, nuanced, tapestry, garner, multifaceted, showcasing*. Kobak et al. estimated 13.5% of 2024 PubMed abstracts were LLM-processed.

**Sentence-length uniformity**: AI prose clusters around a 15-22 word mean with low variance. Human prose exhibits more scattered distributions. AI avoids both the very short emotional sentence and the very long syntactic experiment.

**Syntactic patterns** (Reinhart et al., *PNAS* 2025): instruction-tuned models used **present participial clauses at 2-5× the rate of human text**. "Bryan, leaning on his agility, dances around the ring, evading Show's heavy blows" — two present participles in one sentence. Also: nominalizations at 1.5-2× human rate.

**Structural uniformity**: intro-body-conclusion architecture even when the question does not call for it. Signature closing moves: "Ultimately...", "In conclusion...", "It is worth noting that..."

**Emotional tone flattening**: RLHF training optimizes for helpfulness and harmlessness at the expense of strong signals. Strong human signals — positive or negative — are dragged toward the middle.

**The convergence problem**: LLM-assisted writing reduces stylistic diversity at the population level. Padmakumar and He: base GPT-3 did not homogenize co-written text; InstructGPT did.

### The competence trap

Reinhart et al.'s finding: AI prose is competent, dense, and statistically distinguishable from human prose. **Technically correct prose can be dead prose.**

What aliveness in prose requires is *risk*: the metaphor that might fail, the sentence whose rhythm pushes against its grammar, the emotional gesture that an averaged reader might find excessive. RLHF's reward signal optimizes against risk.
