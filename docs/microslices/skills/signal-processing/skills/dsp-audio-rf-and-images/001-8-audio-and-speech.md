---
id: skill-8-audio-and-speech-94e0feb365
purpose: 8 audio and speech
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-audio-rf-and-images/SKILL.md
requires: []
links: ["skill-9-rf-and-communications-44d4f48b46"]
---

## §8. Audio and Speech

### 8.1 The domain facts

**[DURABLE]** Human hearing spans roughly **20 Hz – 20 kHz** (⚠️ **and the top end
declines substantially with age**), with **~120 dB of dynamic range**, **logarithmic**
in both frequency and amplitude. **Critical bands / Bark / ERB scales** model the ear's
frequency resolution, and **masking** — a loud tone hiding a nearby quiet one, in frequency
and in time — is the entire basis of perceptual audio coding.

⚠️ **Latency budgets are what constrain audio engineering**: musicians notice round-trip
latency above roughly **10 ms**; conversational latency becomes awkward above ~**150–200 ms**
one-way. **These numbers determine your block size, and block size determines everything
else.**

### 8.2 Coding

**Perceptual codecs** (MP3, AAC, Vorbis, Opus) throw away what masking says you can't
hear: **MDCT** transform, psychoacoustic model, quantize, entropy-code.
**Speech codecs** (⚠️ **model the vocal tract rather than the waveform**): LPC, CELP,
AMR, and Opus's SILK layer.

**[VERSIONED] Opus is the one to know** — RFC 6716, hybrid SILK + CELT, **mandatory in
WebRTC**, and covers everything from speech at low bitrate to full-band music.

> **⚠️ GOTCHA — and the most interesting story in DSP right now: classical codecs are
> absorbing neural components rather than being replaced by them.**
>
> **Opus 1.5 (March 2024) put machine learning inside the codec for the first time**, all
> at the decoder — meaning **a service can adopt it on the playback side alone** and
> improve calls for users on bad networks without changing the sender.
> - **Deep PLC** — a neural network reconstructs lost packets, in place of the classical
>   repeat-and-fade. Recommended for occasional loss.
> - **DRED (Deep REDundancy)** — for **burst** loss. It uses a **rate-distortion-optimized
>   VAE** to compress acoustic features so aggressively that **up to one second of
>   redundancy fits in ~12–32 kb/s of overhead**, carried in each packet's padding.
>   ⚠️ **It transmits 20 acoustic features — 18 Bark-frequency cepstral coefficients plus
>   pitch and voicing — and resynthesizes speech from them.** Note the consequence: **the
>   features contain no phase information, so the recovered waveform deviates
>   significantly from the original while sounding similar.**
> - **LACE/NoLACE** — a DNN post-filter that denoises the decoder's output.
>
> **Opus 1.6 (Dec 2025)** added **bandwidth extension (BWE)**, which combined with DRED
> reaches **fullband quality**, and with NoLACE enables **good fullband speech as low as
> 9 kb/s.**
>
> ⚠️ **Two caveats worth carrying.** **DRED's format was still being finalised in IETF as
> of 2026 — treat it as advanced rather than settled.** And **any DNN in a codec
> significantly increases real-time compute**, which is the actual adoption barrier —
> along with model size, which Opus's own developers name as a main obstacle.

**Neural codecs proper** — SoundStream, EnCodec, and the discrete-token codecs underpinning
generative audio — are a genuinely different lineage: much lower bitrates, much higher
compute, and **tokens that double as inputs to generative models.**

### 8.3 The real-time voice pipeline

**[DURABLE] The order matters and is roughly fixed**: **AEC → noise suppression →
dereverberation → AGC → codec.**

**Acoustic echo cancellation** — ⚠️ **adaptive filter (§6 → `dsp-convolution-multirate-and-spectral-analysis`) to model the echo path, plus a
nonlinear residual echo suppressor, plus a double-talk detector.** Interestingly, **most
state-of-the-art AEC is still classical DSP or hybrid DSP-ML**, with deep learning
typically replacing only the nonlinear residual suppressor.

**Noise suppression — and this is where the convergence story is clearest.** The classical
line runs **spectral subtraction (Boll)** → ⚠️ **which produced the notorious "musical
noise" artifact** → **Wiener filtering** (needs a priori statistics) → **MMSE log-spectral
amplitude (Ephraim–Malah, 1985)**, still a respectable baseline.

**RNNoise (Valin, 2018) is the landmark hybrid**: a small recurrent network estimates
**ideal critical-band gains** while **a traditional pitch filter attenuates noise between
harmonics** — ⚠️ **significantly better than a classical MMSE estimator while staying
real-time at 48 kHz on a low-power CPU.** **DeepFilterNet** and successors extended this by
**predicting linear filters rather than estimating clean speech directly**, which is
computationally far cheaper and edge-deployable.

**⚠️ The honest current comparison**: traditional approaches are **fast but conservative**;
deep learning can be **more aggressive while preserving speech quality, at higher
computational cost.** In hearing-aid studies, deep and classical methods perform
**similarly in diffuse noise**, with the deep binaural approach winning **in the presence
of spatial interferers.** **The pattern throughout: hybrids, not replacements.**

**Beamforming** for multi-mic arrays — delay-and-sum, MVDR, GSC — ⚠️ **spatial filtering
that is genuinely complementary to spectral methods**, and increasingly paired with neural
mask estimation.

### 8.4 Music and analysis
**Pitch detection** (autocorrelation, YIN, CREPE), **onset detection**, **beat tracking**,
**source separation** (⚠️ **Demucs, Spleeter and the neural separators substantially beat
classical NMF-based methods** — one of the cleanest ML wins in audio), **MFCCs** (⚠️ **the
classical speech feature; largely superseded by learned representations and mel
spectrograms in modern ML pipelines, but still everywhere in legacy code**), **time-scale
and pitch modification** (phase vocoder, PSOLA, WSOLA).

---
