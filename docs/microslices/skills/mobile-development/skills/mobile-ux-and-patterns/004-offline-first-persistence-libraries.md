---
id: skill-offline-first-persistence-libraries-7ad3214e06
purpose: offline first persistence libraries
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-ux-and-patterns/SKILL.md
requires: ["skill-mobile-design-patterns-81b7e03e06"]
links: []
---

## Offline-first persistence libraries

- **MMKV** (Tencent, C++; `react-native-mmkv` V4 is a Nitro Module requiring RN 0.76+):
  synchronous key-value, "~30x faster than AsyncStorage" per the official README, built-in encryption
  (default AES-128, switchable to AES-256 via `encryptionKey`) — **store the key in
  Keychain/Keystore**. Best for small/medium data, not large datasets.
- **WatermelonDB** (Nozbe, MIT): SQLite-backed, lazy-loaded, observable; queries run on a separate
  native thread; two-phase sync via `pullChanges`/`pushChanges` with a `lastPulledAt` timestamp;
  per-column client-wins conflict resolution; scales to tens of thousands+ records; needs a dev build
  (no Expo Go). (Large-scale "sync success" figures are unverified vendor claims.)
- **Realm / Atlas Device SDK: DEPRECATED.** MongoDB announced deprecation Sept 9, 2024; **Atlas
  Device Sync reached EOL Sept 30, 2025.** Local Realm DB remains open source (v20+ without sync) but
  is maintenance-only. **Do not start new projects on Realm Sync** — if it was in scope, replan now.
- **SQLCipher** (Zetetic): transparent 256-bit AES SQLite encryption (`PRAGMA key`). The official
  Zetetic RN package is Enterprise-only; free paths are **op-sqlite** (`"sqlcipher": true`) and
  **expo-sqlite** (`{"useSQLCipher": true}` config plugin + prebuild, not in Expo Go).

See `mobile-security` for hardware-backed key storage that protects the MMKV/SQLCipher keys.
