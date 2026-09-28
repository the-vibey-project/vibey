---
id: skill-21-method-a3178b372a
purpose: 21 method
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-reference/SKILL.md
requires: ["skill-20-quick-reference-88a22130fc"]
links: []
---

## §21. Method

**No searches were run; none would have helped.** ⚠️ **This is settled mathematics.**
**von Neumann's minimax theorem (1928)**, **von Neumann & Morgenstern (1944)**, **Nash
(1950)**, **Arrow (1951)**, **Gale-Shapley (1962)**, **Selten (1965)**, **Harsanyi
(1967)**, **Gibbard-Satterthwaite (1973)**, **Maynard Smith & Price (1973)**, **Rubinstein
(1982)**, **Myerson-Satterthwaite (1983)**. ⚠️ **The theorems have not changed.**

**Sources** are the references in §19 — chiefly **Osborne & Rubinstein** and **Fudenberg &
Tirole** for §1–§12 → `gametheory-framework-nash-and-classic-games`, `gametheory-zero-sum-sequential-repeated-and-information`, `gametheory-bargaining-cooperative-mechanism-design-and-matching`, **Roth** for §13 → `gametheory-bargaining-cooperative-mechanism-design-and-matching`, **Nowak** and **Maynard Smith** for §14 → `gametheory-evolutionary-empirical-limits-and-computation`,
**Camerer** for §15 → `gametheory-evolutionary-empirical-limits-and-computation`, and **Nisan et al.** for §16 → `gametheory-evolutionary-empirical-limits-and-computation`.

**Confidence: high on the mathematics**, and ⚠️ **I have stated theorems with their
hypotheses throughout, because in this field the hypotheses are where the content is** —
**revenue equivalence, the folk theorem, and second-price truthfulness are all routinely
invoked outside the conditions under which they hold, and §12 → `gametheory-bargaining-cooperative-mechanism-design-and-matching` and §17 flag each case.**

⚠️ **Three places I've taken a position rather than reporting neutrally.**

**§5.1 → `gametheory-framework-nash-and-classic-games`'s warning about the Prisoner's Dilemma is deliberate and I'd defend it strongly.**
⚠️ **The PD is the most over-applied model in social science, and the misdiagnosis has
practical consequences**: **a Stag Hunt is a trust problem where the good outcome is
already an equilibrium and communication may suffice; a true PD requires enforcement or
repetition.** **Prescribing the wrong remedy follows directly from naming the wrong game**,
and the inequality test in §5.1 → `gametheory-framework-nash-and-classic-games` takes thirty seconds.

**§8 → `gametheory-zero-sum-sequential-repeated-and-information`'s framing of the folk theorem as bad news** is the standard view among theorists and
the opposite of how it's usually popularized. ⚠️ **"Anything can be sustained in
equilibrium" is a statement that the concept has lost its predictive content in that
setting**, and presenting it as "game theory explains cooperation" overstates it.

**§16 → `gametheory-evolutionary-empirical-limits-and-computation`'s complexity concern I treat as substantive rather than technical.** ⚠️ **If
computing an equilibrium is PPAD-complete, the claim that players locate it needs
defending**, and **correlated equilibrium's tractability plus its reachability by simple
no-regret learning is a genuine argument for preferring it.** **The practical successes in
§16 → `gametheory-evolutionary-empirical-limits-and-computation` are no-regret learning methods, not equilibrium solvers** — ⚠️ **which I'd read as the
field's computational results being vindicated in practice rather than worked around.**

**§15 → `gametheory-evolutionary-empirical-limits-and-computation` I've tried to state fairly in both directions**: the experimental failures are real
and large, ⚠️ **and they mostly indict the auxiliary assumptions rather than the
framework** — which is why the behavioural variants fit inside it.
