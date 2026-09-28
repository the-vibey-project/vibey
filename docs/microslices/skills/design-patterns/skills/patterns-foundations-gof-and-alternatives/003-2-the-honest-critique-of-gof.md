---
id: skill-2-the-honest-critique-of-gof-9b4c8fde81
purpose: 2 the honest critique of gof
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-foundations-gof-and-alternatives/SKILL.md
requires: ["skill-1-what-a-pattern-is-443befc37a"]
links: ["skill-3-the-gof-audit-52facdaa30"]
---

## §2. The Honest Critique of GoF

**[CONTESTED — and this is a genuine, decades-long disagreement, not a settled question.
Both sides below have real merit and I'll give each its strongest form.]**

### 2.1 The case against

*Design Patterns: Elements of Reusable Object-Oriented Software* (Gamma, Helm, Johnson,
Vlissides, 1994) was written in a C++ context, in an era when — as one widely-cited
critique puts it — **programmers were "festooning their code with virtual methods,
superclasses, subclasses, and clever mixins,"** and **"language limitations and static
types were locking them out of improvements they later wanted to make."**

The structural argument: **each chapter tackled a design conundrum posed by the era's
limited programming languages**, and most solutions **"introduced new classes to cleverly
decouple code that would otherwise be too tightly linked."** Where languages have since
gained first-class functions, modules, and richer type systems, **several patterns
dissolve into a language feature** (§3).

A common academic complaint: the book **"was developed to address several things that
cannot easily be done in C++, which have been better handled in newer languages"**, and
that heavy reliance on the catalogue **"may feel a bit like making the problem fit the
solution instead of building a new solution to fit the problem."**

**⚠️ And the cultural damage was real.** For two decades, **knowing the GoF by heart was
treated as a marker of seniority** — which produced a generation of codebases with
`AbstractSingletonProxyFactoryBean`-shaped indirection installed for its own sake.
Recent commentary describes a **"post-pattern" turn toward "enlightened simplicity,"**
driven by language maturation, functional programming, data-oriented design, and cognitive
load theory.

### 2.2 The case for

**⚠️ The "patterns are just C++ deficiencies" claim is historically shaky**, and the
strongest rebuttal makes three points: **patterns came as much from Smalltalk as from
C++** — and Smalltalk is dynamic with first-class functions, so the deficiency story
doesn't fit the origin; **first-class functions alone don't fully obviate patterns like
Strategy** (they change the implementation, not always the design conversation); and
**providing an alternative implementation doesn't make the original bad.**

The forces argument, which is the strongest one: **design problems repeat even when
technology changes** — creation, composition, variation, decoupling, and behaviour
coordination are permanent. **The names and tooling evolve; the problems don't.**

And the absorption argument cuts both ways: **frameworks from Spring to .NET to Angular
implicitly implement these patterns.** You may not write a Factory, but you configure one
daily — and **you still need to recognize the pattern to judge whether the framework's use
of it fits your case.**

### 2.3 The synthesis this document takes

**[DURABLE] Learn the patterns as vocabulary and as a way of seeing forces. Do not learn
them as a catalogue of things to install.** Concretely:
- **Know all 23 by name and force.** The recognition is cheap and permanently useful.
- **Implement almost none of them literally.** Your language or framework probably has it.
- **Start simple. Add a pattern only when it removes duplication, isolates change, or
  clarifies intent** — and **if it makes the code harder to explain, it's premature.**
- **Weight the modern pattern languages higher** (§8–§12 → `patterns-distributed-concurrency-and-messaging`, `patterns-llm-agentic-and-legacy-migration`). They address forces that are
  live in 2026 in a way that Abstract Factory is not.

---
