---
id: skill-8-streaming-delivery-2380b0317f
purpose: 8 streaming delivery
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-transcoding-streaming-and-drm/SKILL.md
requires: ["skill-7-transcoding-and-packaging-e3585de057"]
links: ["skill-9-drm-63e574d180"]
---

## §8. Streaming Delivery

### 8.1 The protocols and their latency

| Protocol | Latency | Notes |
|---|---|---|
| **HLS** | 20–45 s classic | Apple's; universal support; ⚠️ **CDN-native, which is the whole point** |
| **LL-HLS** | ~2–6 s | Partial segments and blocking playlist reload |
| **DASH** | similar | ISO standard; more flexible; ⚠️ **no native Safari/iOS support** |
| **LL-DASH** | ~2–6 s | Chunked CMAF |
| **WebRTC** | ~sub-second | ⚠️ **Interactive latency, and expensive/complex beyond small audiences** — SFUs, TURN, load balancing |
| **SRT / RIST** | — | ⚠️ **Contribution/ingest over lossy links, not distribution** |
| **RTMP** | ~2–5 s | ⚠️ **Legacy, still the ingest default, doesn't scale for distribution** |
| **MoQ** | ~0.15–1 s | §8.2 |

**[DURABLE] The structural tension that has defined live streaming for two decades**:
**HLS and DASH scale beautifully through HTTP CDNs and add latency; WebRTC gives sub-second
interactivity and scales expensively.** ⚠️ **Any platform wanting both has historically had
to run two stacks.**

### 8.2 ⚠️ Media over QUIC — the 2026 development

**[VERSIONED — the most significant delivery change in years, and still not finished.]**

**MoQ is an IETF effort to get WebRTC-class latency with CDN-class scale**, built as a
**pub/sub system over QUIC**, usable via **raw QUIC** or **WebTransport** in browsers.

**The data model** is worth learning because it's genuinely different from segment-based
streaming: **Object** (smallest unit, typically a frame) → **Subgroup** (objects sharing a
QUIC stream, priority and dependency) → **Group** (independently decodable, e.g. a GoP;
a switching point, droppable under congestion) → **Track** (a named media stream).
⚠️ **A reserved catalog track describes available tracks — the MoQ equivalent of a DASH MPD
or HLS playlist.**

**Two streaming formats sit on top**: **CMSF** — CMAF/fMP4 segments played via MSE,
DRM-capable via EME, **~0.5–1 s latency, best for broad compatibility**; and **MSF** —
raw LOC frames decoded via WebCodecs, **latency below 150 ms, best for real-time
communication and contribution.**

**Why 2026 is the inflection**: the IETF working group moved through monthly draft
revisions toward Working Group Last Call; **Cloudflare deployed MoQ relays across its edge
in 330+ cities**; **eleven vendors demonstrated interoperable implementations at NAB 2026**
(Ant Media, AWS, Bitmovin, Broadpeak, CacheFly, Cloudflare, Nomad Media, Norsk, Oracle,
Red5, Synamedia); **Meta and Google are co-editors** of the transport spec; and browser
support via WebTransport over HTTP/3 reached a **March 2026 baseline of Chrome, Firefox,
and Safari 26.4+**. One open-source implementation reports **200–300 ms latency in
production.**

> **⚠️ GOTCHA — the honest counter-position, which the enthusiasm tends to omit.**
> **MoQ as of mid-2026 still needs a sharply defined "killer" use case that doesn't
> already have a working solution, and the standard remains months away from RFC.**
> Practically: **track it, prototype with it, and plan for it as another transport
> alongside SRT and WebRTC — do not rebuild your production stack on it yet.** New
> protocols enter production through gateways and SDK support, not wholesale replacement.

### 8.3 Player and CDN concerns
**ABR algorithms** — buffer-based, throughput-based, and hybrid (BOLA, MPC).
⚠️ **The startup-quality-versus-startup-time trade is a product decision, not a technical
one.** **Players**: hls.js, dash.js, Shaka Player, Video.js, ExoPlayer/Media3, AVPlayer.
**CDN concerns**: cache-key design, origin shield, **multi-CDN with switching**, and
⚠️ **prefetch and warming for predictable events — a live sports start is a thundering
herd**. **QoE metrics that matter**: startup time, rebuffer ratio, average bitrate,
bitrate switches, play failure rate, and **exit-before-video-start.**

---
