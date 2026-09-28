---
id: skill-16-contested-questions-73effb9b78
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: ["skill-15-anti-patterns-3bb9109b0a"]
links: ["skill-17-currency-snapshot-verified-august-2026-65cc48ff8c"]
---

## §16. Contested Questions

**16.1 Classical DSP or deep learning?** ⚠️ **The live question, and the evidence is more
interesting than either camp's slogan.** *For learning*: it removes the fine hand-tuning of
estimator parameters that classical enhancement depends on, and it wins clearly on source
separation and on non-stationary noise. *For classical*: interpretability, guarantees,
tiny compute, and no training data required — **and much state-of-the-art echo cancellation
remains classical or hybrid, with DNNs replacing only the nonlinear residual stage.**
**[The synthesis the field has actually converged on — RNNoise, DeepFilterNet, Opus 1.5/1.6
— is hybrid: keep the DSP structure you understand, learn the parameters you can't tune.]**

**16.2 Are neural codecs going to replace classical ones?** *For*: dramatically lower
bitrates, and codec tokens double as generative-model inputs. *Against*: compute, model
size (⚠️ **which Opus's own developers name as a main barrier to DNNs in codecs**),
determinism, and the fact that classical codecs are absorbing neural components
incrementally rather than being displaced. **⚠️ Note also that DRED's resynthesis discards
phase — fine for speech intelligibility, and a categorical change in what "reconstruction"
means.**

**16.3 Do objective quality metrics work?** PESQ, POLQA, STOI, SI-SDR are cheap and
repeatable; **they also disagree with listeners, especially on generative or heavily
processed audio where a metric can reward artifacts.** ⚠️ **Subjective MOS testing persists
because nothing has replaced it.**

**16.4 Is high-resolution audio (96/192 kHz) audible?** *For*: filter design headroom,
fewer intermodulation artifacts, and real benefit **during production**. *Against*: the
psychoacoustic evidence for playback benefit above 44.1/48 kHz is weak, and blind tests
mostly fail to show it. **[CONTESTED, and unusually heated relative to the stakes.]**

**16.5 FIR or IIR?** §3.1 → `dsp-sampling-frequency-domain-and-filters`. **Genuinely application-dependent** — and the phase requirement
usually settles it before compute does.

**16.6 Should DSP still be taught with the Z-transform and analogue prototypes?** *For*:
it's the language of the literature, and you cannot read filter design papers without it.
*Against*: most practitioners call a library function and never design a filter from poles
and zeros. **⚠️ The defensible middle: understand what the tool is doing well enough to
choose and debug it — §3.1 → `dsp-sampling-frequency-domain-and-filters`'s decision table matters more than deriving the bilinear
transform.**

---
