---
id: skill-5-dependency-injection-and-inversion-71ff27d785
purpose: 5 dependency injection and inversion
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-foundations-gof-and-alternatives/SKILL.md
requires: ["skill-4-functional-and-data-oriented-alternatives-2d0b55ce92"]
links: []
---

## §5. Dependency Injection and Inversion

**[DURABLE] The most consequential idea in this whole area, and the most commonly
misunderstood.**

**Three distinct things people conflate:**
- **Dependency Inversion Principle** — depend on abstractions, not concretions. *A design
  principle.*
- **Dependency Injection** — pass dependencies in rather than constructing them inside.
  *A technique.* **⚠️ Constructor injection is DI. It requires no framework at all.**
- **DI container / IoC framework** — Spring, Guice, .NET's built-in container. *A tool*,
  and an optional one.

> **⚠️ GOTCHA — the failure modes, and they're common:**
> - **Interfaces with exactly one implementation, created "for testability."** If nothing
>   else will ever implement it, the interface is ceremony. **Modern test tooling can fake
>   concrete types.**
> - **Container magic** — runtime-resolved graphs that are impossible to trace by reading
>   code, and that fail at startup in production rather than at compile time.
> - **Over-abstracting stable dependencies.** You are not going to swap out the standard
>   library's date type.
> - **⚠️ Service Locator is not DI.** It hides dependencies inside the implementation
>   rather than declaring them in the signature, and it is widely regarded as an
>   anti-pattern for that reason.

**[DURABLE] The pragmatic default: constructor injection, plain, no framework, until the
object graph is large enough to genuinely hurt.** Introduce an interface when you have a
second implementation or a real seam — not speculatively.
