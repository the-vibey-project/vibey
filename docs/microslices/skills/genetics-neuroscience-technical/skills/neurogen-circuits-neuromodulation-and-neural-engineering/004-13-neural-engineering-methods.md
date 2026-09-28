---
id: skill-13-neural-engineering-methods-d0864610d3
purpose: 13 neural engineering methods
source: src/vibey_tools/skills/plugins/genetics-neuroscience-technical/skills/neurogen-circuits-neuromodulation-and-neural-engineering/SKILL.md
requires: ["skill-12-development-and-glia-562461fb01"]
links: ["skill-14-stimulation-and-intervention-d3dcdd0419"]
---

## §13. Neural Engineering Methods

**⚠️ Optogenetics** — the technique that made causality testable.
```
ChR2       ~470 nm blue  → cation influx → EXCITE (ms precision)
Halorhodopsin (NpHR) ~590 nm → Cl⁻ influx → INHIBIT
Archaerhodopsin      ~570 nm → H⁺ efflux  → INHIBIT
Red-shifted (ReaChR, Chrimson) → deeper penetration, and ⚠️ enables dual-colour
Step-function opsins → bistable, long-lasting
```
**⚠️ Cell-type specificity comes from the promoter or Cre-driver line, not the opsin.**
**Practical caveats**: light scattering limits depth (⚠️ **hence implanted fibres**),
tissue heating, ⚠️ **and non-physiological synchrony — driving a population at 20 Hz
uniformly is not what the circuit normally does, so interpret gain-of-function results
carefully.**

**Chemogenetics (DREADDs)** — hM3Dq (excite), hM4Di (inhibit), activated by a designer
ligand. ⚠️ **Minutes-to-hours timescale rather than milliseconds; no implant needed.**
⚠️ **The CNO caveat is real: clozapine-N-oxide back-metabolizes to clozapine, which has
its own pharmacology — modern practice uses lower doses, alternative ligands, and
DREADD-free controls.**

**Imaging**: **GCaMP** calcium indicators (⚠️ **calcium is a proxy for spiking with
~100–500 ms decay — you cannot resolve individual spikes at high rates**),
**voltage indicators** (⚠️ **ASAP, Voltron — direct and fast, but far fewer photons and
lower SNR**), **two-photon** (⚠️ **~500–800 µm depth in cortex**), **three-photon**
(deeper), **miniscopes** for freely-moving animals, **fibre photometry** (bulk signal, no
cellular resolution), **light-sheet** for whole-brain imaging in transparent larval
zebrafish.

**Electrophysiology**: **patch clamp** (⚠️ **gold standard for single-cell biophysics;
whole-cell, cell-attached, and the in-vivo variants**), **sharp electrodes**,
**tetrodes**, **Neuropixels** (⚠️ **hundreds to thousands of recording sites on a single
shank — the change that made large-scale population recording routine**), **ECoG**, and
**MEA** in vitro.

**Anatomy and tracing**: **viral tracers** (⚠️ **rabies for monosynaptic retrograde input
mapping; AAV variants for anterograde**), **CLARITY/iDISCO** tissue clearing,
**expansion microscopy** (⚠️ **physically swell the specimen to beat the diffraction
limit**), **Brainbow** multicolour labelling, **serial-section EM** for connectomics
(§17.2 → `neurogen-reference`).

**Molecular profiling**: single-cell and single-nucleus RNA-seq (⚠️ **nuclei work on frozen
and on post-mortem tissue, where whole cells don't**), **spatial transcriptomics**
(MERFISH, Visium, Slide-seq — ⚠️ **transcriptome with anatomical position, which is what
cell-type atlases needed**), and **Patch-seq**, which combines electrophysiology,
morphology and transcriptome from the same cell.

---
