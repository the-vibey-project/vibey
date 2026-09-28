---
id: skill-1-language-design-aaccd13d29
purpose: 1 language design
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-design-parsing-and-types/SKILL.md
requires: ["skill-0-routing-3027fc0e91"]
links: ["skill-2-lexing-and-parsing-c4d4991752"]
---

## §1. Language Design

### 1.1 The questions that determine everything else

Answer these before implementation; each one propagates through the whole pipeline.

| Question | Options | Downstream consequences |
|---|---|---|
| **Static or dynamic typing?** | Static, dynamic, gradual | Determines whether the type checker is a phase or a runtime |
| **Memory management?** | Manual, RAII/ownership, refcount, tracing GC, region/arena | The single largest runtime-design driver (§8.1 → `language-runtimes-interpreters-and-jits`) |
| **Compiled or interpreted?** | AOT, JIT, bytecode VM, tree-walk, transpile | Determines the whole back end |
| **Generics: monomorphize or erase?** | Monomorphize (C++, Rust), erase (Java, Go pre-1.18), dictionary-pass (Haskell, Swift) | Code size vs. compile time vs. runtime cost (§4.5) |
| **Concurrency model?** | Threads+locks, async/await, actors, CSP, STM, structured concurrency | Colours your entire function type system (§8.3 → `language-runtimes-interpreters-and-jits`) |
| **Mutability default?** | Mutable, immutable, controlled | Affects optimization opportunity enormously |
| **Nullability?** | Nullable-by-default, option types, non-null-by-default | Tony Hoare's "billion-dollar mistake." Option types are the settled answer for new languages |
| **Error handling?** | Exceptions, result types, error returns, panics | Interacts with every ABI and FFI decision (§8.4 → `language-runtimes-interpreters-and-jits`) |
| **Metaprogramming?** | None, macros (hygienic or not), reflection, compile-time execution, templates | Determines whether your compiler is also an interpreter (§4.8) |

### 1.2 The design principles that hold up

- **[DURABLE] Simplicity is a budget, not a virtue.** You get a fixed complexity budget;
  every feature spends it. The question is never "is this feature good?" but "is this
  feature worth what it costs in interaction with everything else?" Feature *interactions*
  are superlinear, which is why languages get harder to learn faster than they get bigger.
- **Orthogonality**: features should compose without special cases. Every special case is
  a thing to learn, a thing to implement, and a source of bugs at the seams.
- **The principle of least astonishment** applies to *the population you're targeting*, not
  to language theorists.
- **Make the right thing easy and the wrong thing hard.** Rust's success is mostly this
  principle applied to memory.
- **Errors should be impossible, then caught at compile time, then caught at runtime, then
  documented — in that order of preference.**
- **[CONTESTED] "Worse is Better" (Richard Gabriel, 1989)** — the New Jersey school
  (simplicity of *implementation* beats completeness; ship it) versus the MIT/Stanford
  school (correctness and completeness first). C and Unix won with the first; the second
  produced better artifacts that fewer people used. This tension is unresolved and shows
  up in every language committee.
- **Hyrum's Law**: with enough users, every observable behaviour of your implementation
  becomes a promise, whether or not you specified it. **Specify aggressively, and
  deliberately randomize what you refuse to promise** (Go randomizes map iteration order
  precisely to prevent people depending on it — a technique worth stealing).

### 1.3 Syntax

**[DURABLE] Syntax is the least important part of a language and the part people argue
about most.** That said, it is the interface, and interfaces matter:
- **Familiarity has enormous value.** Jakob's Law applies to languages: users arrive with
  expectations from every other language they know. Novel syntax is a tax paid on every
  reader forever, and it should buy something real.
- **Readability > writability.** Code is read far more than written. Perl and APL optimized
  the wrong one.
- **Prefer unambiguous grammars.** If your grammar needs unbounded lookahead or a "lexer
  hack," your tooling — formatters, highlighters, IDEs, other implementations — will
  suffer forever. C's `(a)*b` ambiguity (cast or multiply? depends on whether `a` is a
  type) is the canonical example.
- **Design for tooling from the start**: a formatter, a syntax highlighter, and an IDE all
  want a *lossless* CST with trivia preserved (§2.4).

> **⚠️ GOTCHA — significant whitespace and tabs.** If you choose indentation-sensitive
> syntax, you must specify the tab/space interaction exactly, at the lexer level, in
> version one. Python took until Python 3 to make mixing an error, and it caused real bugs
> for a decade.

> **⚠️ GOTCHA — reserve keywords generously.** Adding a keyword later breaks every program
> using it as an identifier. Languages handle this with contextual keywords (complexity),
> editions (Rust — §14.2 → `language-diagnostics-tooling-and-evolution`), or just breaking people. Reserve more than you need on day one.

---
