---
id: skill-1-quantum-mechanics-formalism-224b6e7506
purpose: 1 quantum mechanics formalism
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-quantum-mechanics-and-field-theory/SKILL.md
requires: ["skill-0-routing-6f61860dc1"]
links: ["skill-2-solved-systems-and-structure-1c9821f41d"]
---

## §1. Quantum Mechanics: Formalism

### 1.1 The postulates

**[DURABLE] Stated cleanly, because most confusion is a failure to keep them separate:**

1. **States.** A physical state is a ray in a complex Hilbert space `ℋ` — a unit vector
   `|ψ⟩` up to phase.
2. **Observables.** Measurable quantities are **self-adjoint operators** on `ℋ`.
   Self-adjointness guarantees real eigenvalues and a complete orthonormal eigenbasis.
3. **Measurement outcomes.** The only possible results are eigenvalues of the operator.
4. **Born rule.** `P(a_n) = |⟨a_n|ψ⟩|²`.
5. **Unitary evolution.** `iħ ∂|ψ⟩/∂t = Ĥ|ψ⟩` — the Schrödinger equation.
6. **Composite systems.** States combine by **tensor product**, `ℋ_AB = ℋ_A ⊗ ℋ_B`.

> **⚠️ GOTCHA — postulates 4 and 5 are in tension, and that tension is the measurement
> problem (§11 → `physics-measurement-problem-and-quantum-gravity`).** Evolution is **linear, deterministic, and reversible**; measurement is
> **nonlinear, stochastic, and irreversible**. **The theory does not say which one applies
> when, or what constitutes a "measurement."** Everything in §11 → `physics-measurement-problem-and-quantum-gravity` and §15 → `physics-reference` is an attempt to
> resolve that.

**⚠️ And postulate 6 is where the physics gets strange, not postulate 4.** The tensor
product's dimension grows *multiplicatively* — `2ⁿ` for n qubits — and **most states in
`ℋ_A ⊗ ℋ_B` do not factorize.** Those non-factorizing states are entangled. **Entanglement
is a consequence of linear algebra, not an extra assumption.**

### 1.2 The machinery

**Commutators**: `[Â,B̂] = ÂB̂ − B̂Â`. **Canonical**: `[x̂,p̂] = iħ`.
**The uncertainty relation is a theorem, not a measurement limitation:**
```
σ_A σ_B ≥ ½|⟨[Â,B̂]⟩|      →      σ_x σ_p ≥ ħ/2
```
⚠️ **Derived from Cauchy–Schwarz.** It says non-commuting observables **do not have
simultaneous sharp values**, not that your apparatus is clumsy. **Heisenberg's microscope
is pedagogically useful and philosophically misleading.**

**Pictures**: Schrödinger (states evolve), **Heisenberg** (operators evolve:
`dÂ/dt = (i/ħ)[Ĥ,Â] + ∂Â/∂t` — ⚠️ **note the structural echo of Poisson brackets in
classical mechanics**), and **interaction** (used for perturbation theory).

**Density matrices** for mixed states: `ρ̂ = Σ p_i|ψ_i⟩⟨ψ_i|`, with `⟨Â⟩ = Tr(ρ̂Â)`.
⚠️ **The distinction that matters: a pure state has `Tr(ρ²) = 1`; a mixed state has
`Tr(ρ²) < 1`.** For an entangled pair, **each subsystem's reduced density matrix is mixed
even though the joint state is pure** — the information is in the correlations, not the
parts. **This is the technical content of "entanglement."**

**Symmetries and Noether**: every continuous symmetry gives a conserved quantity.
Time translation → energy. Space translation → momentum. Rotation → angular momentum.
⚠️ **In QM the generator *is* the conserved observable**, which is why `p̂ = −iħ∇` (the
generator of translations) and `Ĥ` (the generator of time evolution) have the forms
they do.

### 1.3 The results that constrain interpretation

**[DURABLE] These are theorems. Any interpretation must accommodate them.**

**Bell's theorem (1964)**: no local hidden-variable theory reproduces QM's correlations.
The CHSH inequality bounds local-realist correlations at `|S| ≤ 2`; QM permits
`|S| ≤ 2√2` (**Tsirelson's bound**). ⚠️ **Experimentally violated, with the detection and
locality loopholes closed simultaneously in 2015** — and the 2022 Nobel went to Aspect,
Clauser and Zeilinger for this line of work.

**⚠️ What Bell actually rules out**: the *conjunction* of locality and definite
pre-existing values. **You may keep either one by giving up the other** — which is exactly
what the interpretations do (§15 → `physics-reference`).

**Kochen–Specker**: no non-contextual hidden-variable assignment exists (for dim ≥ 3).
**PBR theorem (2012)**: under stated assumptions, the wavefunction cannot be merely
epistemic. **No-cloning**: `|ψ⟩ → |ψ⟩|ψ⟩` is not unitary — ⚠️ **the foundation of quantum
cryptography, and the reason quantum error correction had to be cleverer than repetition.**
**No-communication**: entanglement transmits no information. ⚠️ **Measurement on A does not
change A's local statistics at all**; correlation only appears when the results are
compared classically. **This is why entanglement is not faster-than-light signalling.**

---
