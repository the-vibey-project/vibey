---
id: skill-2-regular-expressions-in-practice-f334609083
purpose: 2 regular expressions in practice
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-automata-regex-and-parsing/SKILL.md
requires: ["skill-1-automata-and-the-chomsky-hierarchy-64c9561cd6"]
links: ["skill-3-parsing-and-grammars-c027eb0969"]
---

## §2. Regular Expressions in Practice

### 2.1 What regex actually is

**[DURABLE] Theoretical regular expressions and "regex" as implemented are different
things.** Backreferences (`\1`), lookahead/lookbehind, and recursion are **not regular** —
they push the language beyond finite automata, which is exactly why they cost more.

**Two engine families, and the distinction matters enormously:**

| Engine | How | Consequence |
|---|---|---|
| **Backtracking** (PCRE, Perl, Python `re`, Java, JavaScript, .NET) | Explores alternatives, backs up on failure | Supports backreferences and lookaround. ⚠️ **Worst case exponential** — §2.3 |
| **Automata-based** (RE2, Rust `regex`, Go `regexp`, `grep -E` typically) | Simulates an NFA/DFA | **Linear-time guaranteed.** No backreferences |

**[DURABLE] If you are matching untrusted input, this is a security decision, not a style
preference.**

### 2.2 What regex cannot do

**⚠️ Nested structures.** HTML, JSON, balanced parentheses, arbitrary nesting — **regex
cannot match these, ever, because they are context-free and regex is regular** (§1.1).
The famous Stack Overflow answer about parsing HTML with regex is memorable but the
underlying point is a theorem, not an opinion. **Use a parser** (§3).

**⚠️ Counting, arithmetic, and correlated constraints** across arbitrary distance.

### 2.3 ReDoS — where the theory bites daily

> **⚠️ GOTCHA — catastrophic backtracking is a real, common, and preventable denial-of-
> service vulnerability**, and it is the single most direct way automata theory shows up in
> a production incident.
>
> A backtracking engine on a pattern with **nested quantifiers over overlapping
> alternatives** — the `(a+)+`, `(a|a)*`, `(a*)*` shapes — can take **exponential time** on
> a non-matching input, because the number of ways to partition the string explodes.
> A pattern that looks fine and passes tests can be hung by a 30-character string.
>
> **The defences, in order of preference:**
> 1. **Use a linear-time engine** (RE2, Rust `regex`, Go `regexp`) for anything touching
>    untrusted input. This eliminates the class.
> 2. **Avoid nested quantifiers over overlapping alternations.** Learn to recognize the
>    shape.
> 3. **Impose a timeout and an input length cap.**
> 4. **Scan your patterns** — static ReDoS analyzers exist and are worth wiring into CI.
> 5. **Don't build regexes from user input.** That's injection with extra steps.

**[DURABLE] Anchor your patterns.** `^...$` is both a correctness and a performance
property. And **prefer a parser to a heroic regex** — a regex you can't read is a
maintenance liability regardless of complexity class.

---
