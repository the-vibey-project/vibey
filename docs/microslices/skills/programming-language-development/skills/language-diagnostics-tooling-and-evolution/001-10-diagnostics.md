---
id: skill-10-diagnostics-2bcb23ad28
purpose: 10 diagnostics
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-diagnostics-tooling-and-evolution/SKILL.md
requires: []
links: ["skill-11-incremental-compilation-and-ide-support-617ae6487f"]
---

## §10. Diagnostics

**[DURABLE] Error messages are the compiler's primary user interface.** For most users,
most of the time, the compiler is a machine that produces errors. Rust and Elm changed
industry expectations here permanently, and every new language is now judged against them.

### 10.1 What a good diagnostic contains

```
error[E0308]: mismatched types                    ← stable, searchable code
  --> src/main.rs:4:18                            ← precise primary location
   |
 3 |     let x: u32 = 5;
   |            --- expected due to this type      ← SECONDARY span: the cause
 4 |     let y: String = x;
   |            ------   ^ expected `String`, found `u32`
   |            |
   |            expected due to this type
   |
help: try converting the value                    ← ACTIONABLE, ideally machine-applicable
   |
 4 |     let y: String = x.to_string();
   |                      ++++++++++++
```
The elements, in order of value: **precise primary span**, **secondary spans that explain
*why*** (this is the biggest differentiator — showing the *other* end of the conflict),
**plain language, no jargon-first**, **a concrete suggestion**, **machine-applicable fixes**
(so `--fix` and the IDE quick-fix work), and a **stable error code** with extended
documentation.

### 10.2 The rules

1. **Never cascade** (§2.3 → `language-design-parsing-and-types`). One root cause, one error.
2. **Say what was expected, not just what was found.**
3. **Point at the cause, not the symptom.** Type inference makes this genuinely hard: the
   error surfaces where unification fails, which may be far from the mistake. Bidirectional
   checking (§4.2 → `language-design-parsing-and-types`) helps because you know the expected type.
4. **Suggest, but only when confident.** A wrong suggestion is worse than none.
5. **Errors, warnings, and lints are different things** with different severity policies.
   Let users configure lints; don't let them disable soundness errors.
6. **Test your diagnostics.** Snapshot-test error output (rustc's `ui` tests, Elm's
   approach). Untested diagnostics rot immediately.

### 10.3 Warnings

**[DURABLE] Warnings that everyone ignores are worse than no warnings**, because they train
users to ignore output. Keep the default set small and high-precision; put the rest behind
opt-in lint groups; and provide a mechanism to acknowledge-and-silence a specific instance
(`#[allow]`, `// nolint`) so `-Werror` is survivable.

### 10.4 Source locations

Keep spans **everywhere** — in the AST, through desugaring, through IR, into debug info.
Macro-expanded code needs a *chain* of locations (expansion site plus definition site) or
macro errors become unintelligible; Rust's `SyntaxContext`/expansion-info machinery exists
entirely for this. **This is much harder to add later than to design in.**

---
