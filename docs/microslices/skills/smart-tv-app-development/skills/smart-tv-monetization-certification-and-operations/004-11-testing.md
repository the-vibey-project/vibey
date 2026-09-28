---
id: skill-11-testing-0fb434fb2d
purpose: 11 testing
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-10-certification-and-submission-ef44880496"]
links: ["skill-12-analytics-and-qoe-e7e6e98f0a"]
---

## §11. Testing

**[DURABLE] There is no substitute for real devices, and your device lab is a permanent
cost centre.**

Why emulators aren't enough: they don't reproduce the real CPU/GPU/memory profile, they
don't reproduce the frozen browser engine's actual behaviour, they don't do real DRM,
they don't do real HDMI/HDCP, and they don't have the real remote.

**A minimum viable device lab**: the **cheapest current** streaming stick on each
platform (this is your performance floor and where most users are), one **mid-range TV**
per major OS, one device from your **oldest supported model year** per OS (this is where
the frozen-Chromium bugs live), and at least one **4K/HDR** set for the media path.

**What to test that desktop QA will miss**: cold start on a memory-pressured device;
navigation under rapid key-repeat; network degradation mid-playback; app resume after
hours suspended; deep link from cold start; DRM on an old model; captions with the system
style set to something unusual; and the whole flow with the TV's own ACR/ads settings in
both states.

**Remote test labs** — Samsung and LG both offer remote access to real hardware, and
they're genuinely useful for breadth, but latency makes them poor for interaction testing.

**Automation**: Roku's **ECP** (External Control Protocol) allows remote key injection
over HTTP, which makes real CI on real hardware possible; Android TV automates through
adb; web platforms vary. **Automate the regression suite, hand-test the feel.**

---
