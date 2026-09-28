---
id: skill-part-2-prime-directive-before-writing-any-code-46114d242e
purpose: part 2 prime directive before writing any code
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-1-the-three-laws-precedence-order-never-invert-1010e48e8e"]
links: ["skill-part-3-eight-inviolable-security-principles-saltzer-schroeder-zero-trust-dae7dda65c"]
---

## PART 2: PRIME DIRECTIVE — BEFORE WRITING ANY CODE

Before writing a single line of implementation:

1. Re-read the spec, the acceptance criteria, and the Security Considerations section.
2. Identify the security implications (what could go wrong if done incorrectly?).
3. Identify which architectural layer owns this logic (see Part 6).
4. Write the failing test first (see Part 7).
5. Write the minimum secure implementation to make it pass.
6. Refactor.

**Never skip these steps. Never write implementation before a test exists. Never write a test that
does not cover a security boundary. Never leave a TODO, stub, or unimplemented method in
production code paths.**

If the spec is ambiguous about security behavior: stop, surface the ambiguity, wait for
clarification. The default answer to "should this be secured?" is always **yes**.

---
