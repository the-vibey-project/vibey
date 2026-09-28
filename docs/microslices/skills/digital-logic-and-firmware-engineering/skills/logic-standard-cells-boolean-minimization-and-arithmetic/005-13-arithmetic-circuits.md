---
id: skill-13-arithmetic-circuits-5ba49f85b1
purpose: 13 arithmetic circuits
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-standard-cells-boolean-minimization-and-arithmetic/SKILL.md
requires: ["skill-12-combinational-building-blocks-018455c32e"]
links: []
---

## §13. ⚠️ Arithmetic Circuits

> **⚠️ Where the carry chain makes latency a structural problem rather than a gate-count
> problem.**
```
⚠️ HALF ADDER  sum = XOR, carry = AND
⚠️ FULL ADDER  three inputs, sum and carry out
⚠️ ⚠️ RIPPLE CARRY  ⚠️ simple, and delay grows LINEARLY with width
   because each stage waits for the previous carry. ⚠️ This is
   the fundamental problem of binary addition
⚠️ THE FASTER ADDERS, all attacking the carry
   ⚠️ CARRY LOOKAHEAD  ⚠️ compute GENERATE and PROPAGATE terms in
      parallel, so carries don't ripple. ⚠️ Logarithmic delay,
      more area
   ⚠️ CARRY SELECT  compute both possible results, choose when
      the carry arrives
   ⚠️ CARRY SKIP · ⚠️ PARALLEL PREFIX (Kogge-Stone, Brent-Kung —
      the family real high-speed adders come from, trading
      wiring against depth)
⚠️ ⚠️ TWO'S COMPLEMENT  ⚠️ negation is invert-and-add-one, and
   ⚠️ THE SAME ADDER HANDLES SIGNED AND UNSIGNED. ⚠️ This is why
   two's complement won over sign-magnitude — the hardware is
   identical
   ⚠️ OVERFLOW DETECTION differs between signed and unsigned,
   which is a classic source of bugs
⚠️ MULTIPLICATION  ⚠️ partial products → ⚠️ WALLACE or DADDA tree
   reduction using CARRY-SAVE adders (⚠️ which defer carry
   propagation entirely until the final add) → one fast adder
   ⚠️ BOOTH ENCODING reduces the number of partial products
⚠️ DIVISION  ⚠️ genuinely hard, iterative, and much slower —
   restoring, non-restoring, SRT (⚠️ and the Pentium FDIV bug
   was an SRT lookup table error, which is why this is a famous
   example of verification failure)
⚠️ FLOATING POINT  ⚠️ align, operate, normalize, round — with
   ⚠️ ROUNDING and denormal handling as the parts that are
   subtly wrong in naive implementations
```
