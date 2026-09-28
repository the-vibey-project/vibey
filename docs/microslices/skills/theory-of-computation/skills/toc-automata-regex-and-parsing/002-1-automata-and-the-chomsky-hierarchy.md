---
id: skill-1-automata-and-the-chomsky-hierarchy-64c9561cd6
purpose: 1 automata and the chomsky hierarchy
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-automata-regex-and-parsing/SKILL.md
requires: ["skill-0-routing-7c5fb3cec1"]
links: ["skill-2-regular-expressions-in-practice-f334609083"]
---

## §1. Automata and the Chomsky Hierarchy

### 1.1 The hierarchy as an engineering tool

**[DURABLE] The most practically useful idea in this entire document**: languages form a
strict hierarchy, each level needs strictly more machine, and **recognizing which level
your problem sits at tells you immediately what tool to use and what will never work.**

```
                        MACHINE              MEMORY            YOU MEET IT AS
Regular          ←  finite automaton     none (fixed states)   regex, lexers, protocol
                                                               state machines, UI states
Context-free     ←  pushdown automaton   a stack               programming language syntax,
                                                               JSON/XML nesting, expressions
Context-sensitive←  linear-bounded TM    bounded tape          type checking, most "real"
                                                               language rules
Recursively      ←  Turing machine       unbounded tape        general computation
enumerable
                                          ↑ everything above this line is decidable-ish
                                            below it, see §4
```

**[DURABLE] The pumping lemma is the tool for proving something is *not* at a level**, and
the engineering translation is simple: **a finite automaton cannot count unboundedly.**
That single fact is why `a^n b^n` isn't regular, why balanced parentheses aren't regular,
and why the answer to "can I match nested HTML with a regex?" is **no, and it is not a
matter of cleverness** (§2.2).

### 1.2 DFAs, NFAs, and state machines

**DFA**: one state at a time, one transition per input symbol. **NFA**: may be in many
states at once, may have ε-transitions. **[DURABLE] They recognize exactly the same
languages** — every NFA has an equivalent DFA (subset construction), **at a worst-case
exponential blowup in state count.** That blowup is not theoretical trivia; it's why some
regex engines compile lazily and why a pathological pattern can explode.

**Where you actually use this:**
- **Explicit state machines** — order lifecycle, connection state, UI flows, protocol
  handling. **[DURABLE] Model these as an explicit DFA with enumerated states and
  transitions**, not as a pile of boolean flags. The flags approach fails the moment you
  have a state combination nobody enumerated, and it fails silently.
- **Lexers/tokenizers** — a DFA over character classes.
- **Protocol validation** — is this message sequence legal?
- **Model checking** — verifying that a system's state graph satisfies a property.

**Composition matters**: regular languages are closed under union, intersection,
complement, concatenation, and star. **[DURABLE] Closure under intersection and complement
is what makes automata composable as a specification language** — you can build "matches A
but not B" mechanically.

---
