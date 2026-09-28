---
id: skill-17-frontier-what-actually-moved-8562bdd5bb
purpose: 17 frontier what actually moved
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-reference/SKILL.md
requires: ["skill-16-numbers-d1ee44b023"]
links: ["skill-18-books-379ce7d46a"]
---

## §17. Frontier — What Actually Moved

**[Everything above is settled. These two areas changed materially and are worth dating.]**

### 17.1 Therapeutic genome editing

**⚠️ Casgevy (exagamglogene autotemcel) is the landmark**: the first approved
CRISPR-Cas9 therapy, for sickle cell disease and transfusion-dependent β-thalassemia,
approved 2023. **Ex vivo** — cells edited outside the body and reinfused. ⚠️ **Reported
~$2.2M price, which has become a structural test of whether gene editing works as a
healthcare intervention rather than only as science.**

**In vivo editing has now been demonstrated repeatedly:**
- **NTLA-2001** (transthyretin amyloidosis, LNP to liver) — **~87% TTR protein reduction at
  12 months**, competitive with approved siRNA therapies, with Phase 3 studies listed.
- **⚠️ The KJ case (reported NEJM, May 2025) is the one to know**: a **personalized in vivo
  CRISPR therapy for an infant with CPS1 deficiency, developed, FDA-approved and delivered
  in six months**, via LNP by IV infusion. Dosed three times, symptoms and medication
  dependence reduced, no serious side effects reported. **It sets precedent for a
  regulatory pathway for rapid approval of platform therapies** — arguably more significant
  than the editing itself.
- **Prime editing reached patients**: **PM359** for chronic granulomatous disease showed
  **restored NADPH oxidase activity in 58% of neutrophils by Day 15 and 66% by Day 30** in
  the first dosed patient — above the anticipated clinical threshold.
- **Base editing** in trials for AATD and hypercholesterolemia; **over 50 CRISPR trials
  actively recruiting globally as of mid-2026.**

> **⚠️ GOTCHA — a source conflict I could not resolve, so treat with caution.** One 2026
> source lists **EDIT-101 (Leber congenital amaurosis) as FDA-approved alongside Casgevy.**
> ⚠️ **Multiple other sources from the same period describe Casgevy as the only approved
> CRISPR therapy.** I have not been able to reconcile these. **Verify against FDA directly
> before relying on it.** The safe statement: **Casgevy is unambiguously approved; treat
> any second approval as unconfirmed.**

**⚠️ The honest summary**: the technology works, and the remaining problems are
**delivery beyond liver, manufacturing, and cost** — not editing chemistry.

### 17.2 Connectomics

**⚠️ *Nature Methods* named EM-based connectomics its Method of the Year for 2025**, on the
strength of two results:

**FlyWire (2024)** — **the complete connectome of an adult *Drosophila* brain**:
**139,255 neurons and ~5 × 10⁷ chemical synapses**, with annotations for cell types,
classes, nerves, hemilineages and predicted neurotransmitters. ⚠️ **The first adult
connectome completed since *C. elegans***, and it required years of distributed human
proofreading on top of automated segmentation.

**MICrONS (2025)** — **one cubic millimetre of mouse visual cortex**: EM reconstruction of
**>200,000 cells and ~0.5 billion synapses**, ⚠️ **co-registered with calcium imaging of
~75,000 neurons in the same animal viewing natural and synthetic stimuli.** **That
co-registration is the point** — structure and function in the same tissue.

> **⚠️ GOTCHA — scale honestly.** One cubic millimetre is roughly **0.2% of mouse cortex.**
> A **full mouse connectome is estimated to require on the order of 500 petabytes**, with
> **imaging alone costing $200–300M**, and human proofreading for a human brain would be
> vastly harder still. ⚠️ **"We've mapped the brain" is wrong by several orders of
> magnitude**, and ⚠️ **the "fly brain upload" framing is a misreading**: simulations built
> on the connectome still require training on top of it to produce behaviour. **What the
> connectome gives you is the wiring — not the synaptic weights, the neuromodulatory state,
> or the dynamics.**

**⚠️ And the deeper limitation**: a connectome is a static, single-individual snapshot. It
does not contain plasticity (§8 → `neurogen-neuron-biophysics-plasticity-and-coding`), neuromodulation (§11 → `neurogen-circuits-neuromodulation-and-neural-engineering`), or short-term synaptic dynamics
(§7 → `neurogen-neuron-biophysics-plasticity-and-coding`) — **all of which are load-bearing for computation.**

---
