---
id: skill-3-names-scopes-and-modules-4c018a1049
purpose: 3 names scopes and modules
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-design-parsing-and-types/SKILL.md
requires: ["skill-2-lexing-and-parsing-c4d4991752"]
links: ["skill-4-type-systems-36543252d2"]
---

## §3. Names, Scopes, and Modules

### 3.1 Name resolution

Bind every identifier to a declaration. Sounds simple; is not.
- **Scoping**: lexical (almost always correct) vs. dynamic (almost always a mistake).
- **Shadowing**: allowed, warned, or forbidden. Rust allows and uses it heavily; many
  languages warn.
- **Forward references**: can a function call something declared later? At top level,
  usually yes (requiring a separate declaration-collection pass); inside a block, usually
  no. **This decision determines whether name resolution is one pass or two.**
- **Namespaces**: are types, values, macros, and labels in the same namespace? (C has
  separate struct/ordinary namespaces; Rust separates types and values; Lisp-2 vs. Lisp-1
  is the oldest version of this argument.)
- **Overloading** multiplies resolution complexity by type checking — now name resolution
  and type checking are mutually dependent, and you may need to interleave them.

### 3.2 Modules

**[DURABLE] Module systems are where languages accrete the most regret**, because module
semantics touch compilation units, linking, versioning, packaging, and the file system all
at once. The decisions:

| Decision | Options |
|---|---|
| Unit of modularity | File, directory, explicit declaration, package |
| Import granularity | Whole module, selected names, glob |
| Visibility | Public/private, `pub(crate)`-style graded, explicit export lists |
| Cyclic imports | Allowed (complicates compilation order), forbidden (simplifies everything) |
| Name-to-file mapping | Implicit (Java, Python) or explicit (Rust `mod`, C++ modules) |
| Separate compilation | Per-file, per-module, per-package, whole-program |

**[DURABLE] Forbid cyclic module dependencies if you possibly can.** They force
whole-program analysis, complicate incremental compilation, and are almost always a design
smell in user code. Go forbids them; the ecosystem is measurably healthier for it.

> **⚠️ GOTCHA — C++ modules are the cautionary tale.** Standardized in C++20; **GCC 16.1
> (April 2026) still describes its C++20 modules support as experimental, requiring
> `-fmodules`.** Six years from standardization to "still experimental" in a major
> implementation is what happens when a module system must interoperate with a
> textual-inclusion legacy. **Design modules before you have a legacy, not after.**

---
