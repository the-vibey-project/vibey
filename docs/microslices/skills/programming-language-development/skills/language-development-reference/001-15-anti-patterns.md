---
id: skill-15-anti-patterns-c5d6743c0f
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-09580a9a30"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| AST-only front end, no CST | Formatters, refactoring, and IDEs become impossible | Lossless CST, derive the AST (§2.4 → `language-design-parsing-and-types`) |
| Parser that gives up on the first error | The IDE sees broken code 100% of the time | Error nodes + recovery (§2.3 → `language-design-parsing-and-types`) |
| Generated parser for a production language | Poor error messages, poor recovery | Hand-written recursive descent + Pratt |
| One IR for everything | Every pass handles every abstraction level | 3+ levels, progressive lowering (§5.1 → `language-irs-optimization-and-backends`) |
| No IR verifier | Miscompiles found by users, not CI | Verifier after every pass in debug builds |
| No textual IR round-trip | Undebuggable, untestable passes | Print/parse your IR |
| Dropping spans during lowering | Debug info and diagnostics silently degrade | Carry spans to the end (§10.4 → `language-diagnostics-tooling-and-evolution`) |
| Skipping the occurs check | Compiler hangs on `fun x -> x x` | Do the occurs check (§4.3 → `language-design-parsing-and-types`) |
| Naive HM generalization | Accidentally quadratic in environment size | Levels/ranks (§4.3 → `language-design-parsing-and-types`) |
| Global type inference, no signature annotations | Errors surface far from the cause | Require signatures; infer bodies |
| Deferring generic errors to instantiation | Pre-concepts C++ template errors | Check the generic body against its bounds |
| Undefined behaviour for convenience | The most hostile compiler behaviour there is | Define it — even "unspecified" beats "undefined" (§6.2 → `language-irs-optimization-and-backends`) |
| Cascading errors | One typo, 400 messages | Suppress derived errors (§2.3 → `language-design-parsing-and-types`) |
| Warnings everyone ignores | Trains users to ignore all output | Small high-precision default set (§10.3 → `language-diagnostics-tooling-and-evolution`) |
| Compile-time execution with I/O or no step limit | Non-reproducible builds, non-terminating compiles | Sandbox and bound it (§4.8 → `language-design-parsing-and-types`) |
| Cyclic module dependencies allowed | Forces whole-program analysis, kills incrementality | Forbid them (§3.2 → `language-design-parsing-and-types`) |
| Phase-ordered batch compiler, LSP added later | The largest refactor a compiler team can do | Query-based from day one (§11.2 → `language-diagnostics-tooling-and-evolution`) |
| Two implementations, one for the compiler and one for the IDE | Guaranteed divergent behaviour | One engine, two entry points |
| Optimizing before you have benchmarks | You will optimize the wrong pass | Measure first (§6.2 → `language-irs-optimization-and-backends`) |
| Adding a keyword without an edition mechanism | Breaks every program using it as an identifier | Reserve early or ship editions (§14.2 → `language-diagnostics-tooling-and-evolution`) |
| Inventing your own ABI while wanting C FFI | Interop bugs on every platform corner | Implement the platform ABI exactly (§7.4 → `language-irs-optimization-and-backends`) |
| Letting panics/exceptions unwind into C | UB | Catch at the boundary (§8.4 → `language-runtimes-interpreters-and-jits`) |
| Choosing GC late | Constrains calling convention, optimizer, FFI | Decide before the back end (§8.1 → `language-runtimes-interpreters-and-jits`) |
| No formatter, or a formatter with options | Permanent style arguments | Ship one, with no options (§13 → `language-diagnostics-tooling-and-evolution`) |
| No fuzzing on an optimizer | Miscompiles reach users | Csmith/YARPGen-style fuzzing in CI (§12.1 → `language-diagnostics-tooling-and-evolution`) |
| Untested diagnostics | They rot immediately | Snapshot-test error output (§10.2 → `language-diagnostics-tooling-and-evolution`) |

---
