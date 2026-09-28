---
id: skill-1-macos-platform-architecture-720e7ce771
purpose: 1 macos platform architecture
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-macos-platform/SKILL.md
requires: ["skill-0-routing-classify-before-answering-34aa1abfb9"]
links: ["skill-2-macos-ui-swiftui-and-appkit-419098117f"]
---

## §1. macOS Platform Architecture

### 1.1 The stack

```
┌──────────────────────────────────────────────────┐
│ Your app: SwiftUI / AppKit / Catalyst / 3rd-party│
├──────────────────────────────────────────────────┤
│ App frameworks: AppKit, SwiftUI, UIKit(Catalyst) │
├──────────────────────────────────────────────────┤
│ Media/graphics: Core Animation, Metal, Core Image,│
│ AVFoundation, Core Text                          │
├──────────────────────────────────────────────────┤
│ Core Services: Foundation, Core Foundation, GCD, │
│ Core Data, Network.framework, XPC                │
├──────────────────────────────────────────────────┤
│ Darwin: XNU kernel (Mach + BSD), launchd, dyld,  │
│ APFS, Sandbox (Seatbelt), TCC, AMFI, SIP         │
└──────────────────────────────────────────────────┘
```

**Things that matter and are non-obvious:**
- **XNU is a hybrid kernel**: Mach (ports, IPC, VM, scheduling) + BSD (POSIX, sockets,
  VFS). Mach ports are the substrate for XPC and for essentially all privileged IPC.
- **launchd is PID 1** and the *only* supported way to run background processes. Not
  cron, not init scripts, not a daemon you fork yourself.
  - `LaunchAgents` run per-user in the GUI session (`~/Library/LaunchAgents`,
    `/Library/LaunchAgents`). `LaunchDaemons` run as root, system-wide, with no GUI
    session (`/Library/LaunchDaemons`).
  - Modern apps should prefer **`SMAppService`** (macOS 13+) to register login items and
    helpers from *inside* the app bundle, rather than dropping plists into
    `~/Library/LaunchAgents`. The user then manages them in System Settings → General →
    Login Items, which is what they expect.
- **dyld** is the dynamic linker; the **dyld shared cache** is why system frameworks load
  fast. `DYLD_*` environment variables are ignored for hardened-runtime and
  SIP-protected processes — which is exactly why your `DYLD_LIBRARY_PATH` trick works in
  development and fails in the notarized build.
- **SIP (System Integrity Protection)** makes `/System`, `/usr` (except `/usr/local`),
  and `/bin` immutable even to root. Never write outside `/usr/local`, `/opt`, or the
  app's own container.

### 1.2 Bundles — the unit of macOS software

```
MyApp.app/
└── Contents/
    ├── Info.plist              ← identity, version, doc types, URL schemes, usage strings
    ├── MacOS/
    │   └── MyApp               ← the actual executable (CFBundleExecutable)
    ├── Resources/
    │   ├── Assets.car          ← compiled asset catalog (icons, images, colors)
    │   ├── en.lproj/           ← localized strings, per language
    │   └── de.lproj/
    ├── Frameworks/             ← embedded .framework and .dylib — MUST be signed
    ├── PlugIns/                ← app extensions
    ├── XPCServices/            ← XPC helpers
    ├── Library/
    │   └── LoginItems/         ← helper apps registered via SMAppService
    ├── _CodeSignature/         ← signature over the whole bundle
    └── embedded.provisionprofile (App Store / some entitlements)
```

**Info.plist keys you will actually need:**
| Key | Purpose |
|---|---|
| `CFBundleIdentifier` | Reverse-DNS identity. **Immutable in practice** — changing it orphans user data, keychain items, and the App Store record. |
| `CFBundleShortVersionString` | Marketing version ("2.1.0") — what users see |
| `CFBundleVersion` | Build number — must **monotonically increase** per upload |
| `LSMinimumSystemVersion` | Minimum macOS |
| `CFBundleDocumentTypes` / `UTExportedTypeDeclarations` | File type ownership + custom UTIs |
| `CFBundleURLTypes` | Custom URL schemes (`myapp://`) |
| `NS*UsageDescription` | **Required** privacy strings — missing one = instant crash on first use of that API |
| `LSUIElement` | `true` = menu-bar-only app, no Dock icon |
| `LSApplicationCategoryType` | Required for the App Store |
| `ITSAppUsesNonExemptEncryption` | Saves you an export-compliance dialog on every upload |

> **⚠️ GOTCHA — missing usage strings crash, they don't warn.** Calling an API guarded by
> TCC (camera, microphone, contacts, calendar, photos, Downloads/Documents/Desktop,
> screen recording, Automation/AppleScript) without the corresponding
> `NSCameraUsageDescription`-style key in Info.plist terminates the process immediately.
> This looks like a random crash on a user's machine and is instant in the debugger.
> Write the strings as user-facing sentences — the App Store rejects vague ones.

**Where app data goes [PLATFORM]:**
| Content | Sandboxed path | Non-sandboxed |
|---|---|---|
| User-visible documents | `~/Documents` via user selection | same |
| App support / databases | `~/Library/Containers/<id>/Data/Library/Application Support/<id>` | `~/Library/Application Support/<id>` |
| Caches (deletable) | `.../Library/Caches/<id>` | `~/Library/Caches/<id>` |
| Preferences | `UserDefaults` → `.../Library/Preferences/<id>.plist` | same |
| Logs | `.../Library/Logs/<id>` | `~/Library/Logs/<id>` |

Use `FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, ...)`
and never hardcode paths — sandboxing silently redirects them, and hardcoded paths are the
#1 reason an app breaks when you enable the sandbox.

### 1.3 The run loop, GCD, and the main thread

**[PLATFORM, but the concept is UNIVERSAL] All UI work happens on the main thread.**
On macOS the main thread runs an `NSRunLoop`/`CFRunLoop` that dispatches events, timers,
and sources. Touching `NSView`/`NSWindow` — or SwiftUI state that a view reads — from any
other thread is undefined behaviour that manifests as corrupted rendering or a crash in
unrelated code minutes later.

- **GCD (`DispatchQueue`)**: `DispatchQueue.main` is the UI queue. Background work goes on
  `.global(qos:)` or a private serial queue. QoS classes (`.userInteractive`,
  `.userInitiated`, `.utility`, `.background`) affect scheduling priority *and*
  thermal/energy behaviour — mislabeling background work as `.userInitiated` is a real
  battery cost.
- **Swift Concurrency** (`async`/`await`, actors, `@MainActor`) is the modern layer over
  this, and as of Swift 6 the compiler *enforces* the main-thread rule (§3.2).
- **Thread explosion**: `DispatchQueue.concurrentPerform` and unbounded
  `DispatchQueue.global().async` can blow past the thread limit and deadlock. Bound your
  concurrency explicitly (semaphore, `TaskGroup` with a limit, or a serial queue).

### 1.4 XPC — the right way to do privilege separation

XPC is macOS's IPC mechanism, with lifecycle management by launchd. Use it for:
- **Crash isolation**: a plugin host, a parser handling untrusted input, a video decoder.
  If it crashes, the app survives.
- **Privilege separation**: put the network- or file-parsing code in an XPC service with
  a *tighter* sandbox than the main app. This is genuinely effective hardening.
- **Privileged helpers**: `SMJobBless`-style root helpers (modern: `SMAppService.daemon`)
  for the rare operation that truly needs root. Verify the *client's* code signature in
  the helper — an unauthenticated root helper is a local privilege-escalation
  vulnerability, and this has shipped in real products repeatedly.

```swift
// Modern XPC with NSXPCConnection, plus the security check that people omit
let connection = NSXPCConnection(serviceName: "com.example.MyApp.ParserService")
connection.remoteObjectInterface = NSXPCInterface(with: ParsingProtocol.self)
connection.resume()

let proxy = connection.remoteObjectProxyWithErrorHandler { error in
    // Service crashed or was killed — degrade gracefully, don't crash the app
    log.error("XPC failed: \(error)")
} as? ParsingProtocol
```

### 1.5 Apple silicon, Rosetta, and universal binaries

- Ship **universal 2** binaries (`arm64` + `x86_64`) via `lipo`/Xcode until you drop Intel.
  **macOS 26 Tahoe is the last macOS to support Intel Macs** — from macOS 27, Apple
  silicon only. That changes the calculus for new products: an arm64-only build is now
  defensible for apps requiring macOS 27+.
- **Rosetta 2** translates x86_64 ahead-of-time; it does *not* support AVX-512 and it
  cannot load arm64 dylibs into an x86_64 process (or vice versa) — a mixed-architecture
  plugin ecosystem is a real, painful problem.
- Apple silicon has **efficiency and performance cores**; QoS is how you steer work
  between them. Also relevant: unified memory means GPU/CPU transfers are cheap, and
  `MTLStorageMode.shared` is usually right.

---
