---
id: skill-part-2-the-ai-type-taxonomy-dd42f04795
purpose: part 2 the ai type taxonomy
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/ai-chatbot-fundamentals/SKILL.md
requires: ["skill-part-1-what-ai-actually-is-93651246a1"]
links: ["skill-part-3-the-ml-deep-learning-transformer-hierarchy-768f8ab713"]
---

## Part 2: The AI Type Taxonomy

### The Two Big Categories

AI systems divide into two fundamental categories based on capability scope.

#### Narrow AI (the only kind that exists commercially)

Systems trained to do one specific thing very well. They are highly competent and completely inflexible outside their domain. They cannot adapt to new tasks without being retrained.

Every AI tool in commercial use today — ChatGPT, Siri, a customer service chatbot, a fraud detection system, a product recommendation engine — is an example of Narrow AI.

**Two key subtypes within Narrow AI:**

- **Reactive Machines:** Respond to inputs in real time but do not learn from or remember previous interactions. IBM's Deep Blue is the canonical example — could defeat world champions at chess but had no capacity to apply that capability to any other task.
- **Limited Memory Systems:** Use past data to inform current decisions. A self-driving car that learns from accumulated traffic patterns is a Limited Memory system. Most commercial AI today falls into this category.

#### General AI / AGI (theoretical only)

A hypothetical system that could reason, learn, and understand the world across multiple domains, the way a human can — solving unfamiliar problems without retraining and moving between tasks fluidly. This does not exist. Researchers disagree substantially on whether it is 20–30 years away, whether it is achievable at all, and whether achieving it would be desirable.

#### Artificial Superintelligence / ASI (speculative only)

A hypothetical category describing systems that would surpass all human cognitive ability in creativity, strategy, reasoning, and every other domain simultaneously. No real examples exist. It belongs in the taxonomy for completeness, not for practical planning.

### Summary Table

| Type | What It Does | Examples | Status |
|---|---|---|---|
| Narrow AI | Solves specific tasks | Chatbots, Netflix recs, Siri | Already here |
| Conversational AI | Understands/responds in language | Chatbots, voice assistants | Very common |
| Reactive Machines | No memory, reacts only | Deep Blue | Used today |
| Limited Memory | Learns from past data | Self-driving cars | Used today |
| General AI (AGI) | Solves any task like a human | None commercially | Theoretical |
| Superintelligence (ASI) | Surpasses all human ability | None | Speculative |

### Conversational AI: A Special Case of Narrow AI

Conversational AI is a subset of Narrow AI built specifically to understand and generate natural language. Chatbots, virtual assistants, and customer service bots are all forms of Conversational AI. When a well-built Conversational AI answers a question, it is not understanding language the way a human does — it is applying learned statistical patterns to produce a response likely to be relevant and coherent. This distinction matters when diagnosing failures, setting expectations, and deciding what to build.

---
