---
id: skill-ios-swift-swiftui-555b4d2b3d
purpose: ios swift swiftui
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-native-platforms/SKILL.md
requires: []
links: ["skill-android-kotlin-jetpack-compose-34507e7782"]
---

## iOS — Swift / SwiftUI

- **Swift 6** enables complete concurrency checking by default: strict `Sendable`, actor
  isolation, `@MainActor`. **Swift 6.2 (Nov 2025)** added "approachable concurrency" to ease
  migration — practitioners still describe full UIKit migration as a major lift.
- **Architecture options:**
  - **The Composable Architecture (TCA 1.0+)** — Redux-style unidirectional flow with `Reducer`,
    `State`, `Action`, `@Dependency`, and `.run` async effects integrating Swift Concurrency.
  - **MVVM**, or Apple's lighter **"MV"** pattern.
- **Swift Package Manager** is the dependency/modularization standard.
- **Security:** Keychain accessibility classes; Secure Enclave key generation
  (`SecKeyCreateRandomKey`); **App Attest** for app/device attestation; App Transport Security.
- **CI/CD:** Xcode Cloud (or the cross-platform options in `mobile-azure-deployment`).
