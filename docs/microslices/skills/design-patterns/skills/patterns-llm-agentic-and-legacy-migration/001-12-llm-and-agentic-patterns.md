---
id: skill-12-llm-and-agentic-patterns-ff50762ffc
purpose: 12 llm and agentic patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-llm-agentic-and-legacy-migration/SKILL.md
requires: []
links: ["skill-13-migration-and-legacy-patterns-3cdd3c8ddc"]
---

## §12. LLM and Agentic Patterns

**[VERSIONED — the one genuinely new pattern language, and it is still forming.]**

**⚠️ Treat this section differently from the rest.** These patterns are 2–3 years old,
the naming is not yet stable, and **multiple overlapping taxonomies are in circulation** —
practitioners currently work from at least three sources: Andrew Ng's four foundational
patterns, Anthropic's workflow patterns, and a growing set of emergent reliability and
memory patterns. Some are genuine recurring solutions; some are vendor framing. **The
distinction is not yet settled, and anyone claiming otherwise is ahead of the evidence.**

**The distinction that organizes everything**: **workflows** — LLMs and tools orchestrated
through **predefined code paths**, where the flow is fixed and the model only generates
within each step — versus **agents**, where the model decides what comes next. **⚠️ Prefer
workflows.** They are more predictable, more auditable, cheaper, easier to test, and lower
latency; reach for agency only when the task genuinely can't be sequenced in advance.

| Pattern | What it is |
|---|---|
| **Prompt chaining** | Fixed sequence, each step consuming the last, with **programmatic gates between steps** that halt on bad output. Trades latency for accuracy; errors don't snowball |
| **Routing** | Classify the input, dispatch to a specialized handler |
| **RAG** | Retrieve, augment, generate — grounding output in a controlled corpus. ⚠️ **A fixed RAG chain is a workflow, not an agent**: the order is hardcoded and the model doesn't get a vote |
| **Tool use / function calling** | The model calls external capabilities |
| **ReAct** | Interleaved reasoning and action in a loop, adjusting on each observation. **Good for exploratory tasks**; predates the current framing by ~2 years |
| **Plan-and-Execute** | A planner produces a full multi-step plan, an executor runs it. **Better for long structured tasks where mid-stream drift is costly** |
| **Reflection / Evaluator-Optimizer** | A generator produces, a separate evaluator critiques, iterate. ⚠️ **Separated roles is what distinguishes this from single-model self-critique** |
| **Programmatic planning** | Hardcoded sequences or state machines for business processes requiring strict adherence — **high determinism, easier debugging, "golden paths"** |
| **Multi-agent / topologies** | Specialized agents with restricted toolsets; chain, star, and mesh communication topologies |
| **Human-in-the-loop** | ⚠️ **A cross-cutting modifier insertable into any pattern** as an approval gate, with **stopping conditions such as a maximum iteration count** |
| **Memory** | Short-term, long-term, episodic, procedural — retrieved separately and combined into context |
| **Guardrails** | Input and output validation at the boundary |
| **Progressive disclosure** | Load capability and context on demand to combat **context rot** |

> **⚠️ GOTCHA — the design forces that are specific to this domain and catch experienced
> engineers:**
> - **Non-determinism is the substrate.** Every pattern here is scaffolding to make a
>   probabilistic component behave like a reliable one. **The mental shift is from
>   "LLM-as-oracle" to "LLM-as-component."**
> - **Context is a scarce, contended resource**, and quality degrades as it fills.
> - **Cost and latency scale with orchestration.** Each agentic decision is another call.
>   **Runaway loops are a real financial failure mode** — hence iteration caps.
> - **⚠️ Multi-agent was a 2023–24 buzzword and is substantially over-applied.** A single
>   well-scaffolded agent beats a committee for most tasks.
> - **Observability is different**: step-level tracing, token cost tracking, hallucination
>   detection, and guardrail-violation metrics — **standard API logs won't show you where a
>   multi-step workflow went wrong.**
> - **Treat prompts as code** — versioned, decoupled from orchestration, testable.
> - **Don't pick a framework before you know which pattern you need.**

**[DURABLE, and this is the transferable insight]**: **if your system needs multiple steps,
external data, conditional branching, or retry logic, you are already building an agent
whether or not you called it one** — and the patterns in §8–§11 → `patterns-distributed-concurrency-and-messaging` apply to it, because it is
a distributed system with an unusually unreliable component in it.

---
