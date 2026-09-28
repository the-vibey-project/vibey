---
id: skill-14-language-evolution-5be9d4fc30
purpose: 14 language evolution
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-diagnostics-tooling-and-evolution/SKILL.md
requires: ["skill-13-standard-library-and-ecosystem-7936c14b56"]
links: []
---

## §14. Language Evolution

### 14.1 Backward compatibility

**[DURABLE] The core tension: every language must evolve, and every change breaks someone.**
The strategies actually used:
- **Never break** (Java, C, Go 1.x). Maximum trust, permanent accumulation of mistakes.
- **Deprecate then remove** (Python 2→3). The Python 3 transition took roughly a decade and
  is the field's canonical warning about breaking changes at scale.
- **Editions/language versions** (Rust editions, C++ standards). §14.2.
- **Feature flags** (`from __future__ import`, `#![feature]`). Lets you ship unstable
  features to consenting users and get feedback before committing.

### 14.2 Editions — the best mechanism we have

**Rust's edition model**: each crate declares its edition; editions may change syntax and
idioms; **crates of different editions interoperate freely** in one program because the
change happens in the front end and the IRs unify. Combined with `cargo fix` for automated
migration, this lets a language change `async` from an identifier to a keyword without a
Python-3 event.

**[DURABLE] If you're designing a language and you expect to live for decades, design the
edition mechanism early.** The constraint it imposes — editions cannot change the *type
system* or the *runtime*, only surface syntax and lints — is exactly the constraint that
makes it work, and it's much easier to honour from the start.

### 14.3 Governance

Options: BDFL (fast, coherent, has a bus factor and a succession crisis — Python's PEP 8016
governance transition after Guido's resignation is the reference), committee (ISO C/C++ —
slow, stable, produces documents rather than implementations), foundation + teams (Rust,
Python post-2018), corporate (Go, Swift, Kotlin — fast and coherent, with the community's
influence bounded by the sponsor's interests).

**[VERSIONED] The C++ committee's 2025–26 record is an instructive case**: C++26 was
finalized on 28 March 2026 after a six-day London meeting with 210 experts from 24 nations,
delivering reflection, contracts, `std::execution`, and a hardened standard library. It
also **rejected the "Safe C++" borrow-checking proposal** in favour of the Profiles
approach, and **the `[[profiles::enforce]]` attribute was then deferred to C++29**. Herb
Sutter stepped down as convener. Read that sequence as a demonstration of what committee
governance is good at (a large, coherent, multi-vendor standard shipping on schedule) and
what it is bad at (deciding a contested safety strategy quickly).

**Whatever the model, you need**: a public proposal process with a written record, a
stability policy stated *before* you need it, a deprecation policy, and a security-response
process.

### 14.4 Multiple implementations

**[CONTESTED]** A second implementation validates the specification, breaks vendor
lock-in, and expands platform reach — but doubles the conformance surface and creates
"which one is right?" ambiguity when the spec is incomplete.

**[VERSIONED] `gccrs` is the live experiment.** A GCC front end for Rust, motivated by
reaching every target GCC supports without depending on LLVM-based rustc. Its 2026 status
is a useful reality check on how long a second implementation takes: the project stated its
**2026 goal as being able to *mis*-compile the Linux kernel** — explicitly, an experimental
compiler that produces binaries that may not run correctly — with milestones ordered as
"embedded Rust compiler" → "Rust for Linux compiler" → "general-purpose compiler." As of
mid-2026 it handles simple standalone programs, having spent the first half of the year
finding and fixing problems in attribute handling, name resolution, and resource
management by testing against kernel crates. The project began in earnest around 2020.
**Budget five-plus years for a second implementation of a non-trivial language, and note
that gccrs deliberately targets Rust 1.49 semantics rather than chasing current Rust.**
