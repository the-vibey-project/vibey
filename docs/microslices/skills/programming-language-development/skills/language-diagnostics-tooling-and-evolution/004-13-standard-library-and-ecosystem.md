---
id: skill-13-standard-library-and-ecosystem-7936c14b56
purpose: 13 standard library and ecosystem
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-diagnostics-tooling-and-evolution/SKILL.md
requires: ["skill-12-testing-and-verification-e923e8e202"]
links: ["skill-14-language-evolution-5be9d4fc30"]
---

## §13. Standard Library and Ecosystem

**[DURABLE] A language is not a language; it's a language plus a standard library plus a
package manager plus a build tool plus a formatter plus a debugger plus documentation.**
The languages that succeeded in the last twenty years shipped the whole thing (Go, Rust);
the ones that struggled left it to the community and got fragmentation.

**Standard library scope [CONTESTED]:** "batteries included" (Python, Go) versus minimal
core plus ecosystem (Rust, Node). *For batteries*: no dependency for common tasks, one
obvious way, no supply-chain risk for basics. *Against*: **the standard library is where
code goes to die** — you can never break it, you can never move fast, and Python's
`asyncio`/`urllib`/`distutils` history is the standard evidence. Rust's deliberate
minimalism trades a large dependency graph for the ability to evolve.

**Ship on day one**: a formatter (**with no options** — `gofmt` ended a category of
argument permanently), a build tool and package manager (see the package-manager reference),
a test runner, a documentation generator, a linter, and a debugger story (DWARF, and
actually test it).

---
