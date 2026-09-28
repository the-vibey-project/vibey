---
id: skill-12-macos-system-extensions-security-and-testing-ffe1d44418
purpose: 12 macos system extensions security and testing
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-11-macos-architecture-5d8323ef3a"]
links: ["skill-13-comparative-architecture-463771aae3"]
---

## 12. macOS system extensions, security, and testing

System extensions include DriverKit, NetworkExtension, EndpointSecurity, and other specialized interfaces. They are delivered inside an app bundle, activated through SystemExtensions, and checked for signatures, identifiers, entitlements, and placement. DriverKit templates use C++ and an I/O Kit interface-generator header. Apple requires drivers inside `Contents/Library/SystemExtensions`. [DriverKit creation](https://developer.apple.com/documentation/driverkit/creating-a-driver-using-the-driverkit-sdk) and [installation](https://developer.apple.com/documentation/systemextensions/installing-system-extensions-and-drivers)

macOS security layers include code signing, Developer ID, notarization, Gatekeeper, App Sandbox, TCC privacy permissions, hardened runtime, entitlements, quarantine, SIP, and system-extension approval.

Apple’s notarization workflow requires signing, hardened runtime and appropriate entitlements for modern distributed software; `notarytool` is the current submission tool. [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

Conceptual workflow:

```sh
xcodebuild archive ...
xcodebuild -exportArchive ...
codesign --verify --deep --strict --verbose=4 path
ditto -c -k --keepParent path artifact.zip
xcrun notarytool submit artifact.zip --wait
xcrun stapler staple path
spctl --assess --type execute --verbose=4 path
```

Test on clean macOS installations and both architectures where relevant. Test sleep/wake, hot plug, multiple users, privacy prompts, sandbox failure, update/uninstall, network loss, and code-signing/notarization behavior.

SIP protects system areas and unauthorized execution. Apple says it may need temporary disabling for certain low-level development, but it should be restored immediately. [Apple SIP guidance](https://developer.apple.com/documentation/security/disabling-and-enabling-system-integrity-protection)
