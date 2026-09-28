---
id: skill-18-the-canon-ce48fe0a1b
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-65cc48ff8c"]
links: ["skill-19-quick-reference-7f9cab3790"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Smith, Steven W.** | ***The Scientist and Engineer's Guide to DSP*** | ⚠️ **Free online, and the best possible starting point.** Intuition before formalism |
| **Oppenheim & Schafer** | ***Discrete-Time Signal Processing*** | The standard graduate text. Rigorous |
| **Lyons** | ***Understanding Digital Signal Processing*** | ⚠️ **The best bridge between intuition and rigour.** Superb on practical gotchas |
| **Proakis & Manolakis** | *Digital Signal Processing* | Comprehensive, communications-leaning |
| **Vaidyanathan** | *Multirate Systems and Filter Banks* | §5 → `dsp-convolution-multirate-and-spectral-analysis`, definitively |
| **Zölzer** | *DAFX: Digital Audio Effects* | ⚠️ **The audio-effects reference, and genuinely fun** |
| **Pirkle** | *Designing Audio Effect Plugins in C++* | Implementation-focused |
| **Kay** | *Fundamentals of Statistical Signal Processing* (2 vols) | §6 → `dsp-convolution-multirate-and-spectral-analysis`, §7.4 → `dsp-convolution-multirate-and-spectral-analysis` — estimation and detection |
| **Haykin** | *Adaptive Filter Theory* | §6 → `dsp-convolution-multirate-and-spectral-analysis` |
| **Zwicker & Fastl** | *Psychoacoustics* | §8.1 → `dsp-audio-rf-and-images`'s foundations |
| **Gonzalez & Woods** | *Digital Image Processing* | §10 → `dsp-audio-rf-and-images` |
| **Proakis & Salehi** | *Digital Communications* | §9 → `dsp-audio-rf-and-images` |
| **Bracewell** | *The Fourier Transform and Its Applications* | ⚠️ **The classic on §2 → `dsp-sampling-frequency-domain-and-filters`, and beautifully written** |

### 18.2 Primary sources and tooling
**`scipy.signal` documentation** (⚠️ **unusually good at explaining *which* method and
why**), **MATLAB's DSP documentation**, **the Opus codec site and its demo pages**
(⚠️ **Valin's write-ups on Opus 1.5 and 1.6 are outstanding technical communication and the
best free explanation of neural-in-codec design**), **IETF drafts** for DRED,
**GNU Radio tutorials**, **DSPRelated.com**, **musicdsp.org**, **KVR** and the JUCE forum
for audio implementation, **the ICASSP / Interspeech / DAFx / AES** proceedings.

### 18.3 People
**Jean-Marc Valin** (⚠️ **Opus, Speex, RNNoise — arguably the most consequential practical
audio DSP engineer working, and he publishes clearly**), **Richard Lyons** (the best
explainer in the field), **Julius O. Smith III** (⚠️ **Stanford CCRMA — his four free
online books on filters, spectral audio, and physical modelling are a remarkable
resource**), **Alan Oppenheim**, **Steven W. Smith**, **Ronald Bracewell**,
**Udo Zölzer**, **P. P. Vaidyanathan**, **Simon Haykin**, **Monty Montgomery**
(⚠️ **Xiph — his video demonstrations of sampling and dither are the clearest explanations
of §1 → `dsp-sampling-frequency-domain-and-filters` anywhere**), **Emmanuel Vincent** and **Antoine Liutkus** (source separation).

---
