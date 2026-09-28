---
id: skill-adopt-the-new-architecture-now-the-legacy-bridge-is-end-of-life-6bbddb0c0d
purpose: adopt the new architecture now the legacy bridge is end of life
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: []
links: ["skill-project-structure-state-management-180c0db662"]
---

## Adopt the New Architecture now — the legacy Bridge is end-of-life

The New Architecture replaces the asynchronous, JSON-serializing Bridge with four pillars:

- **JSI** — synchronous C++ JS↔native interface (no serialization round-trip).
- **TurboModules** — lazily loaded native modules.
- **Fabric** — the new concurrent renderer.
- **Codegen** — generates type-safe native interfaces from JS specs.

Timeline:
- **RN 0.76 (Oct 23, 2024)** made the New Architecture the **default**; shipped React Native
  DevTools (zero-config, replaces Flipper), a **~15× faster** Metro resolver and ~4× faster
  warm builds, and New-Architecture-only style props `boxShadow` and `filter`. Meta coordinated
  compatibility "with over 850 library maintainers."
- **RN 0.80 (June 12, 2025)** brought React 19.1, **froze** the legacy architecture, and
  deprecated JavaScriptCore in favor of **Hermes** (Hermes is required).
- **RN 0.82** drops the legacy architecture entirely.
- **Expo SDK 53+** defaults to the New Architecture; **SDK 55 (RN 0.83) cannot disable it**.

Migration reality: audit **every third-party native module** for New Architecture
compatibility. Run `npx expo-doctor` to validate against the React Native Directory. Reported
gains (faster cold start, lower memory) are directional vendor/community figures, not controlled
Meta benchmarks.
