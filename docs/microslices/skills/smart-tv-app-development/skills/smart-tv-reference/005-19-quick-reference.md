---
id: skill-19-quick-reference-4a63153f92
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: ["skill-18-the-canon-0a92840fb3"]
links: ["skill-20-sources-and-method-b161936671"]
---

## §19. Quick Reference

### 19.1 Numbers
- Design canvas **1920×1080**; **safe area 90%** (5% margin each side).
- Body text **≥24 px**; nothing below ~18 px.
- Focusable targets **≥60–80 px**.
- Frame budget **16.6 ms**; time-to-first-video-frame **<2 s**; cold start **<3 s**.
- Rebuffer ratio **<0.5%**; playback failure **<1%**.
- Loudness **−23 LUFS** (streaming/SSAI), **−24 LKFS** (US broadcast).
- Ad creative **≤200 MB** (≤150 MB preferred); **VAST 4.x**.
- Samsung 2024 TVs run **Chromium 108**; 2018 TVs run **Chromium 56**.
- Roku **Instant Resume required by 1 Oct 2026** (qualifying US apps).

### 19.2 Pre-launch checklist
- [ ] Focus never lost; Back always predictable; initial focus set on every screen
- [ ] Everything inside the 90% safe area; readable at 10 feet
- [ ] Tested on the **cheapest** device and the **oldest model year** you support
- [ ] Long lists virtualized; images server-sized; memory monitored
- [ ] Cold start and time-to-first-frame measured on the slowest device
- [ ] Deep links work: cold start, warm start, unentitled user, missing content
- [ ] Playback position saved continuously; resume verified after a long suspend
- [ ] Both `cenc` and `cbcs` packaging verified on old and new devices
- [ ] Captions render and honour system style settings
- [ ] Sign-in via device-code pairing, not an on-screen keyboard
- [ ] Platform billing implemented per policy; entitlement enforced server-side
- [ ] Analytics segmented by device model and OS version
- [ ] Certification checklist walked end-to-end **before** submission
- [ ] Catalogue feed submitted for platform search/voice/recommendation rows

### 19.3 "It's broken on TV" triage
| Symptom | First look |
|---|---|
| Remote appears dead | Focus lost, or focus trapped in a container (§3.1 → `smart-tv-platforms-and-10-foot-ui`) |
| Blank/white screen on some models only | Frozen-Chromium feature gap — check the engine version (§1.3 → `smart-tv-platforms-and-10-foot-ui`) |
| Black screen on playback, older devices | `cenc`/`cbcs` mismatch, or codec unsupported on that tier (§5.1 → `smart-tv-playback-drm-and-performance`) |
| App killed during use | Memory budget exceeded — profile image cache and list virtualization |
| Slow to start playing | Sequential cold-start network cascade (§4.3 → `smart-tv-playback-drm-and-performance`) |
| Fails certification on launch time | Same, plus JS bundle parse cost |
| Works via deep link, broken from search | Catalogue feed mapping or unentitled-user path (§7.2 → `smart-tv-playback-drm-and-performance`–7.3) |
| Ads too loud | Loudness normalization (§4.2 → `smart-tv-playback-drm-and-performance`) |
| Fine on the OLED, broken on the stick | You tested on the wrong device (§11 → `smart-tv-monetization-certification-and-operations`) |

---
