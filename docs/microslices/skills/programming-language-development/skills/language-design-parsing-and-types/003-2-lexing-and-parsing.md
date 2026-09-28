---
id: skill-2-lexing-and-parsing-c4d4991752
purpose: 2 lexing and parsing
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-design-parsing-and-types/SKILL.md
requires: ["skill-1-language-design-aaccd13d29"]
links: ["skill-3-names-scopes-and-modules-4c018a1049"]
---

## §2. Lexing and Parsing

### 2.1 Lexing

Convert characters to tokens. The parts people underestimate:
- **Unicode.** Identifiers (UAX #31), normalization (NFC — decide and enforce it, or `é`
  and `é` are different identifiers), and **bidirectional-override characters, which are a
  security issue**: the "Trojan Source" attack uses them to make source read differently
  to a human than to the compiler. Reject or warn on bidi control characters in source.
- **Spans/locations on every token.** Byte offsets plus a line-index side table is the
  standard efficient design — computing line/column lazily from a precomputed line table
  beats tracking it per character.
- **Trivia** (whitespace, comments) — either preserve them attached to tokens or you cannot
  build a formatter or a lossless refactoring tool later (§2.4).
- **Interpolated strings, raw strings, and nested comments** are where hand-written lexers
  earn their keep; regex-based lexer generators struggle with them.

### 2.2 Parsing — choosing an approach

| Approach | Notes |
|---|---|
| **Recursive descent + Pratt** | **The overwhelming choice of production compilers** (GCC, Clang, rustc, Go, TypeScript, V8). Hand-written, readable, arbitrary lookahead, and — decisively — *excellent error recovery and error messages* |
| LL(k) generators (ANTLR) | Good tooling, good for DSLs; less control over errors |
| LALR generators (yacc/bison) | Compact, fast; conflicts are famously painful to debug; poor error messages |
| GLR / Earley | Handle ambiguous grammars; slower; useful for language *research* and for parsing C++ |
| PEG / packrat | Unambiguous by construction (ordered choice), linear with memoization; **ordered choice silently hides ambiguity, which is a footgun** |
| Combinators | Elegant, great for prototypes; error messages and performance need work |

**[DURABLE] Essentially every widely-used production compiler uses hand-written recursive
descent, and the reason is error recovery.** A generated parser gives up or produces a
generic message; a hand-written one can say "you forgot a semicolon here" and continue.
Since the parser's output feeds an IDE that sees broken code 100% of the time, this is not
a minor consideration.

**Pratt parsing (top-down operator precedence)** is the right technique for expressions:
each token gets a binding power, and precedence and associativity fall out of comparing
them. It's about 50 lines and handles prefix, infix, postfix, and mixfix cleanly.

### 2.3 Error recovery

**[DURABLE] The parser's job is not to reject bad programs. It is to produce a usable tree
from bad programs**, because that is the input it receives most of the time.
- **Error nodes / poison nodes**: represent "something was here but it was wrong" in the
  tree so later phases can continue and produce *their* errors too.
- **Panic-mode recovery with synchronization tokens**: on error, skip to the next `;`, `}`,
  or start-of-declaration and resume.
- **Insertion/deletion repair**: hypothesize a missing token and continue.
- **Never cascade.** One missing brace producing 400 errors is the classic failure. Suppress
  errors within a short distance of a previous one, and suppress errors *derived from*
  poison nodes.

### 2.4 CST vs. AST

- **CST (concrete syntax tree)**: every token, every space, every comment. Required for
  formatters, refactoring tools, and IDEs. Rust-analyzer's **rowan** and the
  **Roslyn** "red-green tree" design are the reference implementations: a persistent,
  immutable "green" tree of shared nodes plus a lightweight "red" layer providing parent
  pointers and absolute positions.
- **AST**: semantic structure, trivia discarded.
- **[DURABLE] Build the CST and derive the AST from it.** Going the other direction is
  impossible. This is the single most common regret in compiler front-end design, because
  the IDE requirement always arrives later than the compiler requirement.

---
