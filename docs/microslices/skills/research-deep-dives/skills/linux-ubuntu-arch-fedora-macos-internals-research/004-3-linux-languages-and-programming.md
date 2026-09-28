---
id: skill-3-linux-languages-and-programming-68a24d3393
purpose: 3 linux languages and programming
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-2-linux-internals-e407509031"]
links: ["skill-4-kernel-programming-b1694a8ab6"]
---

## 3. Linux languages and programming

You can program Linux in C, C++, Rust, Go, Zig, Swift, Fortran, Ada, Java, Kotlin, C#, Python, Ruby, Perl, JavaScript/TypeScript, shell, Lua, R, and many more. The stable boundary is the kernel ABI and user-space APIs, not a particular language.

Typical roles:

- C: libc, kernel-facing libraries, mature systems tooling, and established interfaces.
- C++: large systems, GUI toolkits, performance-sensitive code.
- Rust: memory-safe systems components and selected kernel/user-space projects.
- Go: services, networking, distributed systems, and CLI tools.
- Python/shell/Ruby/Perl: automation, administration, testing, and orchestration.
- Assembly: boot, ABI glue, context switching, SIMD, atomics, and hardware-specific work.

The build chain is preprocessing/macro expansion, compilation, assembly, linking, packaging, installation, and dynamic loading. Toolchains include GCC, Clang/LLVM, binutils, Make, Ninja, CMake, Meson, Cargo, Go tooling, and language package managers.

A serious build records compiler, SDK, flags, target architecture, dependency versions, source revision, generated files, locale, and timestamps. Use warnings, sanitizers, static analysis, dependency audits, signed artifacts, and reproducible-build checks.
