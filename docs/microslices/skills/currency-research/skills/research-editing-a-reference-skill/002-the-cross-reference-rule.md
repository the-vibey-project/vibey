---
id: skill-the-cross-reference-rule-a7168b3a36
purpose: the cross reference rule
source: src/vibey_tools/skills/plugins/currency-research/skills/research-editing-a-reference-skill/SKILL.md
requires: ["skill-anatomy-of-a-generated-skill-md-d79fb44212"]
links: ["skill-byte-discipline-325139ec26"]
---

## The cross-reference rule

Within a plugin, a reference to a section **that lives in a sibling skill** is annotated:

```
… as covered in §20 → `foo-isa-simulation-and-specialization`, the …
```

A reference to a section **in the same skill** stays bare (`§14`). A range lists only the
non-local targets: ``§7–§12 → `x`, `y` ``.

**If your edit adds a new `§N` reference, you must annotate it yourself** using the same rule:
find which skill owns §N (look at the sibling list in the header), and append `` → `that-skill` ``
if it is not the skill you are editing.

### ⚠️ Citations of *other documents* must stay bare

The marketplace's references cite each other. Those citations use the *other* document's
section numbers and **must never be annotated**, or they turn into links into the wrong
plugin — which is worse than no link, because it looks authoritative.

Four phrasings occur. All of them mean "another document's §N":

```
see a power engineering reference §12          ← 'a … reference' then the ref
a peripherals reference (§5's wireless HID)    ← ref opens the parenthetical
a robotics-software reference (§14 there)      ← ref followed by 'there'
§6 of a communications reference               ← ref before the words
```

And two lookalikes that **are** internal and stay annotated:

```
The IA reference (§3)                                    ← a books-table entry; note "The", not "a"
a security reference (§20's hierarchy … recurs there)    ← our §20, recurring over there
```

The distinguishing signals are the **indefinite article** (`a`/`an` introduces another
document; `The` usually introduces a titled work) and **`there` vs `here`**. When a citation
is genuinely ambiguous, leave it bare and say so in the pull request.

---
