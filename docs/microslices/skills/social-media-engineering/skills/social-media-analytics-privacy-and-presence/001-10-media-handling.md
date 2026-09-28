---
id: skill-10-media-handling-909f221321
purpose: 10 media handling
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-media-analytics-privacy-and-presence/SKILL.md
requires: []
links: ["skill-11-analytics-and-experimentation-a02ce4fbf8"]
---

## §10. Media Handling

**[DURABLE] Uploads are an attack surface as much as a feature.**
**Validate server-side, always** — ⚠️ **never trust the client's content type or extension;
sniff the actual bytes.** **Transcode rather than serve originals** (⚠️ **which also
strips a large class of embedded exploits**), **strip EXIF** (⚠️ **GPS coordinates in
uploaded photos are a real and recurring privacy incident**), generate multiple sizes,
serve via CDN with signed URLs where privacy matters, and **run hash-matching against known
violating content before publication** (§7 → `social-moderation-abuse-and-regulation`).

**⚠️ The specific hazards**: **decompression bombs** (a small file that expands to
gigabytes — cap dimensions and pixel count before decoding), **SVG containing script**
(⚠️ **never serve user SVG from your own origin**), **polyglot files** valid as two types,
**and video that's expensive to transcode** — rate-limit by cost, not by file count.

For everything downstream of that — codecs, packaging, delivery — see a media-engineering
reference.

---
