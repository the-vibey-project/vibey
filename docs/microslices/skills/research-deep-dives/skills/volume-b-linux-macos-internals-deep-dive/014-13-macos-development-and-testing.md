---
id: skill-13-macos-development-and-testing-8d752fb87a
purpose: 13 macos development and testing
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-12-drivers-and-system-extensions-650eeda3a2"]
links: ["skill-14-cross-platform-programming-849b572021"]
---

## 13. macOS development and testing

Swift and Objective-C integrate with Foundation, Cocoa, SwiftUI, XPC, Metal, Network Extension, DriverKit and other frameworks. C and C++ remain important for systems and cross-platform code. Shell and scripting languages are useful, but system-provided versions and permissions vary by release.

Testing should include XCTest, UI tests, Instruments, sanitizers, unified logging, crash reports, signed and packaged execution, sandbox and TCC behavior, clean user accounts, Intel and Apple-Silicon targets where relevant, and deployment tests.

System extensions require correct entitlements, signatures, installation, approval and lifecycle behavior. Development modes that relax validation are not shipping configurations; validation must be restored before release.

Source: [Apple system-extension testing](https://developer.apple.com/documentation/driverkit/debugging-and-testing-system-extensions).
