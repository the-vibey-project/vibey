---
id: skill-2-radioactive-decay-3427f46fb7
purpose: 2 radioactive decay
source: src/vibey_tools/skills/plugins/nuclear-physics/skills/nuclear-structure-decay-reactions-and-dose/SKILL.md
requires: ["skill-1-nuclear-structure-1ac8c2ebd7"]
links: ["skill-3-reactions-and-cross-sections-15f759a305"]
---

## §2. Radioactive Decay

```
Alpha (α)      ⚠️ emits ⁴He; heavy nuclei; quantum TUNNELLING through the Coulomb
               barrier — which is why half-lives span 30 orders of magnitude
Beta-minus     n → p + e⁻ + ν̄ₑ    ⚠️ neutron-rich nuclei
Beta-plus / EC p → n + e⁺ + νₑ    proton-rich
Gamma (γ)      ⚠️ NOT a change of nuclide — de-excitation of an excited state
Spontaneous fission · neutron emission (⚠️ delayed neutrons — see §6.3)
```
**Decay law**: `N(t) = N₀e^{−λt}`, `t½ = ln2/λ`, activity `A = λN` in becquerels.
**⚠️ Secular equilibrium**: when a long-lived parent feeds a short-lived daughter, the
daughter's activity rises to match the parent's. **This is why radon (3.8 d) persists in
uranium-bearing rock indefinitely.**

> **⚠️ GOTCHA — long half-life means LOW activity, and this inverts most people's
> intuition.** ⚠️ **Activity is `λN`, and `λ = ln2/t½`.** **`²³⁸U` (4.5 billion years) is
> barely radioactive — you can hold it. `¹³¹I` (8 days) is intensely radioactive and
> dangerous.** **"It stays radioactive for 10,000 years" and "it is dangerously
> radioactive" are close to opposites**, and the confusion drives a lot of bad reasoning
> about waste (§8 → `nuclear-fuel-cycle-waste-and-safety`).

---
