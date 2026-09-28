---
id: skill-10-boolean-algebra-c97637a5eb
purpose: 10 boolean algebra
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-standard-cells-boolean-minimization-and-arithmetic/SKILL.md
requires: ["skill-9-standard-cells-f81981cf41"]
links: ["skill-11-minimization-8b7ee9f5cc"]
---

## §10. ⚠️ Boolean Algebra

```
⚠️ THE OPERATORS  AND, OR, NOT · ⚠️ XOR (⚠️ the workhorse of
   arithmetic and parity) · NAND, NOR
⚠️ ⚠️ FUNCTIONAL COMPLETENESS  ⚠️ NAND ALONE can express every
   Boolean function. So can NOR alone. ⚠️ This is why §5's
   natural gates are sufficient
⚠️ THE LAWS  identity, null, idempotent, complement,
   commutative, associative, distributive
   ⚠️ DE MORGAN'S  ⚠️ NOT(A AND B) = NOT A OR NOT B, and dual.
   ⚠️ The most-used identity in practice — it lets you push
   inversions around to match available gates
   ⚠️ CONSENSUS and absorption
⚠️ CANONICAL FORMS  ⚠️ sum of products (minterms) and product of
   sums (maxterms) — ⚠️ any function has exactly one of each,
   which is what makes automated minimization possible
⚠️ REPRESENTATIONS  truth table · algebraic · schematic ·
   ⚠️ BDD (binary decision diagram — ⚠️ canonical for a given
   variable order, which makes EQUIVALENCE CHECKING tractable
   and underpins formal verification)
⚠️ ⚠️ DON'T CARES ARE VALUABLE  ⚠️ input combinations that cannot
   occur, or outputs that don't matter, give the optimizer
   freedom. ⚠️ Failing to specify them costs real area
```

---
