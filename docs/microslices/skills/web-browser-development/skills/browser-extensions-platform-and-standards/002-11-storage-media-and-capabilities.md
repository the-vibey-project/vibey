---
id: skill-11-storage-media-and-capabilities-49308be52b
purpose: 11 storage media and capabilities
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-extensions-platform-and-standards/SKILL.md
requires: ["skill-10-extensions-f6bd740699"]
links: ["skill-12-accessibility-5487f3b0ac"]
---

## §11. Storage, Media, and Capabilities

**Storage**: cookies, localStorage/sessionStorage (synchronous — a main-thread hazard),
**IndexedDB** (the real database), Cache API, Origin Private File System, and the
**Storage Standard**'s quota and eviction model. **All of it must be partitioned** (§9.2 → `browser-security-and-privacy`),
and all of it needs a clear "clear browsing data" story.

**Service workers** — a programmable proxy for a scope, with a lifecycle (install →
activate → idle → terminate) that is a common source of both bugs and confusion. They are
also a persistence mechanism with security implications.

**Media**: the codec matrix (H.264/AVC, VP9, AV1, HEVC — with **patent licensing driving
which engine ships what**), Media Source Extensions, **Encrypted Media Extensions and
CDMs** (proprietary binary blobs in your process — sandbox them), WebCodecs, WebRTC,
autoplay policy, and hardware decode paths.

**Capability APIs** — WebUSB, WebBluetooth, WebSerial, WebHID, WebNFC, File System Access,
WebGPU, geolocation, notifications.
**[CONTESTED] The capability question is the deepest philosophical split between engines.**
Chrome ships them behind permission prompts, arguing the web should be able to do what
native can. Apple and Mozilla have declined many, citing attack surface and fingerprinting
entropy. *Both positions are coherent*: every capability is simultaneously a user
empowerment and a new way to be attacked or identified. There is no neutral answer, and
"the other engine is just being obstructive" is usually wrong.

---
