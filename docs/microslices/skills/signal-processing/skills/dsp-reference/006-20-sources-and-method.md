---
id: skill-20-sources-and-method-4d71d07fe8
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-reference/SKILL.md
requires: ["skill-19-quick-reference-7f9cab3790"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written as practice guidance for engineers implementing DSP.
**The overwhelming majority — §1–§7 → `dsp-sampling-frequency-domain-and-filters`, `dsp-convolution-multirate-and-spectral-analysis`, §9–§15 → `dsp-audio-rf-and-images`, `dsp-implementation-tools-and-testing` — is classical signal processing**, resting on
the standard literature (Oppenheim & Schafer, Lyons, Smith, Vaidyanathan, Kay, Bracewell)
rather than on anything searched, and it does not move: **Nyquist is 1928, Shannon 1949,
Cooley–Tukey 1965, and Ephraim–Malah 1985.** §17 says so plainly rather than manufacturing
a currency layer. Two targeted searches were run in **August 2026** on the one part that
genuinely moved: the convergence of classical DSP with machine learning in audio.

**Search log** (August 2026): Opus 1.5/1.6, DRED, deep packet loss concealment, and neural
audio codecs · speech enhancement and noise suppression, classical versus deep, and
real-time constraints.

**Primary and near-primary sources consulted (selected):**
- **The Opus codec project's own demo pages for 1.5 and 1.6** and the **xiph/opus
  repository**, for the DRED, Deep PLC, LACE/NoLACE and BWE descriptions and the
  bitrate figures; **IETF `draft-ietf-mlcodec-opus-dred`** for the acoustic-feature
  specification and the standardization status; **arXiv 2212.04453** (Valin et al.,
  *DRED: Deep REDundancy Coding of Speech*) for the design rationale
- **arXiv 1709.08243** (Valin, *A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band
  Speech Enhancement* — RNNoise), read for the architecture and the stated comparison
  against MMSE; DeepFilterNet and successor papers for the predict-filters-not-signal
  approach; **IEEE/ACM TASLP** work on real-time multichannel deep enhancement in hearing
  aids for the diffuse-versus-spatial-interferer comparison
- Independent evaluation write-ups (CouthIT) of Opus 1.5's Deep PLC and LACE, and a 2026
  practitioner guide to noise suppression, for the classical-versus-deep framing

**Confidence statement.** **Very high confidence** in §1–§7 → `dsp-sampling-frequency-domain-and-filters`, `dsp-convolution-multirate-and-spectral-analysis` and §9–§15 → `dsp-audio-rf-and-images`, `dsp-implementation-tools-and-testing` — this is textbook
signal processing, taught consistently for decades, and my confidence rests on that
literature rather than on web sources. **High confidence in the Opus material** in §8.2 → `dsp-audio-rf-and-images` and
§17: the mechanism descriptions, bitrates and feature counts come from the Opus project's
own documentation and the IETF draft, and Valin's technical writing is unusually precise.
⚠️ **The DRED standardization status is the item most likely to have moved** — the draft I
saw was dated January 2026 with a July 2026 expiry, so **check the IETF datatracker before
relying on it.**

⚠️ **Moderate confidence on §8.3 → `dsp-audio-rf-and-images`'s classical-versus-deep comparison.** The individual
findings are from peer-reviewed sources, but **"most state-of-the-art AEC is still
classical or hybrid" comes from a paper whose authors were motivating their own end-to-end
alternative**, and such framing is naturally selective; the hearing-aid comparison is one
study on two acoustic scenes. **The broad pattern — that hybrids are outperforming both
pure approaches in production audio — is well supported across multiple independent lines
of evidence, but the specific characterizations should not be read as settled consensus.**
§16 is opinion labelled as such, and §16.4 in particular is a debate where I have tried to
report the state of the evidence rather than adjudicate.
