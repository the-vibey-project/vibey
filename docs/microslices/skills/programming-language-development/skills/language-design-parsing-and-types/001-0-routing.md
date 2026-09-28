---
id: skill-0-routing-3027fc0e91
purpose: 0 routing
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-design-parsing-and-types/SKILL.md
requires: []
links: ["skill-1-language-design-aaccd13d29"]
---

## §0. Routing

### 0.1 The pipeline

```
SOURCE TEXT
  │  LEXER ─────────── tokens (+ trivia, spans)                            §2
  │  PARSER ────────── CST/AST (+ error recovery)                          §2
  ▼
FRONT END
  │  NAME RESOLUTION ─ bind identifiers to declarations; modules, scopes   §3
  │  TYPE CHECKING ─── inference, coercion, trait/class resolution         §4
  │  SEMANTIC ANALYSIS ─ borrow/effect/exhaustiveness/definite-assignment  §4.7
  ▼
MIDDLE END
  │  LOWER to IR ───── SSA / CPS / ANF; desugar; monomorphize              §5
  │  OPTIMIZE ──────── inline, constant-fold, DCE, GVN, LICM, vectorize    §6
  ▼
BACK END
  │  INSTRUCTION SELECTION ─ IR → target instructions                      §7
  │  REGISTER ALLOCATION ─── virtual → physical registers                  §7.3
  │  SCHEDULING / EMISSION ─ object code, debug info                       §7
  ▼
RUNTIME + LINK ───── GC, scheduler, FFI, unwinding, dynamic loading        §8
```

**[DURABLE] The two most consequential structural decisions are made before you write a
line of the pipeline:**
1. **What is your IR, and how many do you have?** (§5 → `language-irs-optimization-and-backends`) Every serious compiler ends up with
   at least three levels. Deciding this late means rewriting everything.
2. **Is the front end reusable by an IDE?** (§11 → `language-diagnostics-tooling-and-evolution`) A compiler designed as a batch
   source-to-binary pipeline cannot be turned into a responsive language server without
   substantial rearchitecture. Design for incrementality from day one or accept that you
   will do it twice.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Should this be a language at all? Design philosophy, trade-offs | §1 |
| Lexing, parsing, grammars, error recovery, syntax design | §2 |
| Scopes, modules, imports, name resolution | §3 |
| Type systems, inference, generics, traits, effects, ownership | §4 |
| IR design — SSA, CPS, ANF, MLIR, lowering | §5 → `language-irs-optimization-and-backends` |
| Optimization passes and where they belong | §6 → `language-irs-optimization-and-backends` |
| Code generation, instruction selection, register allocation, backends | §7 → `language-irs-optimization-and-backends` |
| Runtime: memory management, GC, concurrency, FFI, exceptions | §8 → `language-runtimes-interpreters-and-jits` |
| Interpreters, bytecode VMs, JIT | §9 → `language-runtimes-interpreters-and-jits` |
| Error messages and diagnostics | §10 → `language-diagnostics-tooling-and-evolution` |
| Incremental compilation, IDE, LSP | §11 → `language-diagnostics-tooling-and-evolution` |
| Testing, fuzzing, formal verification | §12 → `language-diagnostics-tooling-and-evolution` |
| Standard library, ecosystem, tooling | §13 → `language-diagnostics-tooling-and-evolution` |
| Evolution, versioning, governance, deprecation | §14 → `language-diagnostics-tooling-and-evolution` |
| "Don't do this" | §15 → `language-development-reference` |
| "Which approach is better?" | §16 → `language-development-reference` (contested) |
| "Is this still current?" | §17 → `language-development-reference` |
| Books, papers, people | §18 → `language-development-reference` |

---
