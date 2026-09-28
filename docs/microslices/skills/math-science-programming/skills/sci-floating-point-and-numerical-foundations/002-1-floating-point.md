---
id: skill-1-floating-point-59b31b9f68
purpose: 1 floating point
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-floating-point-and-numerical-foundations/SKILL.md
requires: ["skill-0-routing-61d5b9f4a1"]
links: ["skill-2-conditioning-and-stability-1e68a18599"]
---

## §1. Floating Point

**[DURABLE] IEEE 754 dates from 1985, is implemented everywhere, and has not changed.
Everything in this section is permanent.**

### 1.1 What you're actually computing with

**`float64`**: 1 sign bit, 11 exponent, 52 mantissa. **~15–17 significant decimal digits**,
range ~10^±308. **`float32`**: ~6–9 digits, ~10^±38. **`float16`/`bfloat16`** trade
precision for memory and speed — ⚠️ **`bfloat16` keeps float32's exponent range and throws
away mantissa**, which is why ML uses it and numerical analysis mostly doesn't.

**Machine epsilon (float64): ~2.22e-16.** ⚠️ **The single most useful number in this
document** — it's the gap between 1.0 and the next representable number, and it bounds
your relative error per operation.

> **⚠️ GOTCHA — the consequences, all of which produce silent wrong answers:**
> - **`0.1 + 0.2 != 0.3`.** Decimal fractions mostly aren't representable in binary.
>   ⚠️ **Never compare floats with `==`** — compare against a tolerance, and think about
>   whether it should be absolute or relative.
> - **⚠️ Addition is not associative.** `(a+b)+c != a+(b+c)`. **This is why parallel
>   reductions give different answers on different thread counts** (§11 → `sci-statistics-performance-and-reproducibility`, §14 → `sci-statistics-performance-and-reproducibility`), and it is
>   the single most common source of "why doesn't my result reproduce."
> - **Catastrophic cancellation.** Subtracting nearly-equal numbers annihilates
>   significant digits. ⚠️ **The classic: the quadratic formula loses all precision for one
>   root when `b² >> 4ac`** — use the numerically stable variant.
> - **Absorption.** Adding a tiny number to a huge one changes nothing. ⚠️ **Summing a
>   large array naively accumulates error proportional to n** — use **Kahan/Neumaier
>   compensated summation** or pairwise summation (⚠️ **NumPy's `sum` already does
>   pairwise; a hand-rolled loop does not**).
> - **Special values.** `NaN != NaN` (⚠️ **which is how `NaN` sneaks past your validity
>   checks**), `inf - inf = NaN`, and **signed zero** matters at branch cuts.
> - **Subnormals** near zero lose precision gradually, ⚠️ **and can be dramatically slow on
>   some hardware** — flush-to-zero is a real performance flag.
> - **`x87` 80-bit intermediates, FMA contraction, and `-ffast-math`** all change results.
>   ⚠️ **`-ffast-math` assumes no NaN/inf and permits reassociation — it can silently break
>   correct code.**

### 1.2 The practices
**Scale and non-dimensionalize** your problem so quantities are O(1) — ⚠️ **this single
habit prevents a large fraction of overflow, underflow, and conditioning problems.**
**Prefer `log` space** for products of probabilities (`logsumexp`). **Reformulate to avoid
cancellation** (`log1p`, `expm1`, `hypot` exist precisely for this). **Use the library
function** — ⚠️ **`np.hypot(x,y)` is not `sqrt(x*x+y*y)`; it avoids intermediate overflow.**
And **when you genuinely need exactness — money, combinatorics — use integers, decimals, or
rationals**, not floats.

---
