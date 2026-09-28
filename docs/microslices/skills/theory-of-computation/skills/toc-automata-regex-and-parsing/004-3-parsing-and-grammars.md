---
id: skill-3-parsing-and-grammars-c027eb0969
purpose: 3 parsing and grammars
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-automata-regex-and-parsing/SKILL.md
requires: ["skill-2-regular-expressions-in-practice-f334609083"]
links: []
---

## §3. Parsing and Grammars

### 3.1 The grammar classes you'll meet

```
Regular           ⊂  LL(k)  ⊂  LR(k)  ⊂  Context-free  ⊂  Context-sensitive
                     ↑          ↑          ↑
                  recursive  most parser  ambiguity possible;
                  descent    generators   general parsers (Earley, GLR, CYK)
                  by hand    (yacc, etc.) handle it at higher cost
```
**LL(k)** parses top-down with k symbols of lookahead — **this is what hand-written
recursive descent is**, and it's why hand-written parsers are common and pleasant.
**⚠️ LL cannot handle left recursion** (`expr := expr '+' term` loops forever); you rewrite
it iteratively.
**LR(k)** parses bottom-up, handles a strictly larger class, and is what parser generators
emit. **LALR** is the compressed variant most tools actually use — and **"shift/reduce
conflict" means your grammar isn't in the class the tool handles**, which is the theory
telling you something real.
**PEG / packrat** — ordered choice removes ambiguity by fiat, which is convenient and
occasionally hides a genuine grammar problem.

### 3.2 The practical points

**[DURABLE] Real programming languages are not context-free**, and this surprises people.
Declaration-before-use, type correctness, and scope rules are context-sensitive.
**The universal solution: parse the context-free skeleton, then do semantic analysis on the
tree.** That two-phase structure is not an implementation convenience; it's a direct
consequence of where the language sits in the hierarchy.

**⚠️ C's famous ambiguity** — `x * y;` is either a multiplication or a pointer declaration
depending on whether `x` is a type — requires feeding symbol-table information back into
the parser. **The "lexer hack."** It's ugly because the language design outran the grammar
class.

**[DURABLE] Ambiguity is a property of the grammar, not the language**, and determining
whether an arbitrary CFG is ambiguous is **undecidable** (§4 → `toc-computability-and-complexity`). This is why parser
generators report conflicts rather than proving your grammar unambiguous.

**Practical advice**: **don't hand-roll a parser for a format that has one.** Use a real
JSON/YAML/CSV parser — the edge cases (escaping, encodings, numeric precision, YAML's
famous surprises) have consumed more engineering time collectively than almost any other
category of self-inflicted bug.
