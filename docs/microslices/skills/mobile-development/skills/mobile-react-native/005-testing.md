---
id: skill-testing-edea250b0b
purpose: testing
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: ["skill-performance-d958701aa0"]
links: ["skill-expo-eas-69db33dbb0"]
---

## Testing

- **Unit/component (~70% of pyramid):** Jest + React Native Testing Library.
- **E2E:** **Maestro** (YAML, black-box via the accessibility layer, no native build changes,
  sub-1% flakiness) is now generally preferred over **Detox** (gray-box, synchronizes with the
  JS thread, sub-2% flakiness, deeper RN integration but heavy native setup). Jupiter's fintech
  case study found Detox succeeded "only 2 out of 10 times on physical devices" and switched to
  Maestro, slashing MPIN entry from 18s to under 1s via `runScript`.
