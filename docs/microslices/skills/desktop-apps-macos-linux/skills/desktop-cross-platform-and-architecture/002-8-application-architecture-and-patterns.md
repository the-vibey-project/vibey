---
id: skill-8-application-architecture-and-patterns-1b88ff0dc8
purpose: 8 application architecture and patterns
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-cross-platform-and-architecture/SKILL.md
requires: ["skill-7-cross-platform-frameworks-137f615b20"]
links: ["skill-9-the-desktop-idioms-what-makes-an-app-feel-native-39eaf1e604"]
---

## §8. Application Architecture and Patterns

### 8.1 The layering that survives contact with two platforms

```
┌───────────────────────────────────────────────────────┐
│ Platform UI      SwiftUI/AppKit  │  GTK4/Qt6           │ ← thin, idiomatic, per-platform
├──────────────────────────────────┴──────────────────── ┤
│ Presentation     view models / stores / commands       │ ← testable, platform-free
├───────────────────────────────────────────────────────┤
│ Domain           entities, rules, use cases            │ ← pure. no I/O, no UI, no clock
├───────────────────────────────────────────────────────┤
│ Ports (traits/protocols)  FileStore, Clock, Net, Prefs │ ← the seam
├───────────────────────────────────────────────────────┤
│ Adapters         real FS, real network, real keychain  │ ← platform-specific, thin
└───────────────────────────────────────────────────────┘
```
**[UNIVERSAL] The domain layer must not import a UI framework, a clock, or a filesystem.**
Everything it needs comes in through a port you can substitute in tests. This is the single
highest-leverage architectural decision in a desktop app, for the same reason it is in
firmware: it converts a 30-second click-through into a 30-millisecond test.

### 8.2 State management

| Pattern | Where it's idiomatic | Notes |
|---|---|---|
| **MVVM** | SwiftUI (`@Observable` view models), Qt/QML, Avalonia, WPF-lineage | The desktop default. Keep view models free of framework types. |
| **MVC** | AppKit, GTK (loosely) | Classic; degrades into massive controllers without discipline |
| **Unidirectional / Redux-ish** | Elm-inspired (iced), TCA on Apple platforms, Electron+Redux | Excellent for undo/replay/time-travel; verbose |
| **MVP / MVVM-C** | Large enterprise apps | Explicit navigation ownership |

**[UNIVERSAL] Single source of truth.** Desktop apps have multiple windows, inspectors,
sidebars, and a menu bar all reflecting the same state. The moment two of them own
overlapping state, you get the classic desktop bug: change something in the inspector, and
the sidebar shows the old value. One store; views derive.

### 8.3 The document model, undo, and autosave

Desktop apps that edit user data have obligations that web apps don't:

- **Undo/redo is not optional** and it must be *unlimited* by default, *coalescing*
  (typing 30 characters is one undo step, not 30), and *scoped per document window*.
  - macOS: `UndoManager` — register undo closures at the model layer, not the view layer.
  - Cross-platform: a command/memento stack in your domain layer. Storing *inverse
    operations* scales better than storing full snapshots.
- **Autosave + versioning.** macOS gives you `NSDocument` autosave-in-place and Versions
  browsing largely for free; SwiftUI's `DocumentGroup` inherits it. On Linux you implement
  it: write to a temp file in the same directory, `fsync`, then `rename()` (atomic on the
  same filesystem). **Never truncate-and-write the user's file in place** — a crash
  mid-write destroys their data.
- **Dirty state and window close.** Modified documents must prompt. macOS convention: the
  close button shows a dot; the sheet offers Save/Don't Save/Cancel.
- **Crash recovery.** Periodically persist an unsaved-changes journal; offer restoration
  on next launch. Users forgive crashes; they don't forgive lost work.

```swift
// Undo done at the model layer, with coalescing — the shape that works
final class TextModel {
    private(set) var text: String = ""
    weak var undoManager: UndoManager?
    private var coalescingToken: Int = 0

    func replace(with new: String, actionName: String, coalesce: Bool = false) {
        let old = text
        if coalesce && undoManager?.isUndoing == false {
            // group rapid edits into one undoable action
            undoManager?.groupsByEvent = false
        }
        undoManager?.registerUndo(withTarget: self) { target in
            target.replace(with: old, actionName: actionName)   // inverse re-registers redo
        }
        undoManager?.setActionName(actionName)   // "Undo Typing" in the Edit menu
        text = new
    }
}
```

### 8.4 Threading and responsiveness

**[UNIVERSAL] The main thread budget is ~8 ms per frame at 120 Hz, ~16 ms at 60 Hz.**
Everything else goes off it.

| Work | Where |
|---|---|
| Any file I/O (yes, even "small" reads) | Background |
| Network | Background |
| Parsing, decoding, compression | Background |
| Database queries | Background (or a dedicated actor/queue) |
| Layout, drawing, widget mutation | **Main only** |
| Sorting/filtering a 10k-row list | Background, deliver a prepared snapshot |

Platform mechanics: macOS → Swift Concurrency (`@MainActor` + `actor` + `Task`) or GCD.
GTK → do work on a thread, marshal back with `glib::idle_add_local` /
`g_main_context_invoke`. Qt → `QThread`/`QtConcurrent` + queued signal-slot connections
(cross-thread signals are queued automatically, which is the point).

> **⚠️ GOTCHA — the progress indicator that isn't.** A spinner rendered on the same
> thread that's blocked doesn't spin. If your "loading" UI freezes, the work is on the
> main thread. This is diagnostic, not cosmetic.

**Cancellation is a first-class requirement on desktop.** Users close windows, switch
documents, and retype search queries. Every long operation needs a cancellation token
checked at intervals, and a UI affordance to trigger it.

### 8.5 IPC and multi-process design

Reasons to split processes: crash isolation, privilege separation, plugin sandboxing,
using a different language/runtime for part of the app.

| Platform | Mechanism |
|---|---|
| macOS | **XPC** (lifecycle-managed, typed, launchd-integrated) |
| Linux | **D-Bus** (discoverable, desktop-standard) or plain Unix sockets |
| Cross-platform | Unix domain sockets + a length-prefixed framed protocol; or gRPC; or stdin/stdout with JSON-RPC (what LSP does, and it works fine) |

**[UNIVERSAL] Design the protocol to be versioned and forward-compatible from message
one.** In a desktop app the two processes can end up at different versions during an
update; ignoring unknown fields and negotiating a version at handshake avoids a whole
class of upgrade bugs.

### 8.6 Single instance, and the launch protocol

Desktop users expect: clicking the launcher when the app is running **raises the existing
window**; opening a file when the app is running opens it in the running instance.

- macOS: automatic. `NSApplication` handles reopen and `application(_:open:)`.
- Linux: `GtkApplication`/`GApplication` with `G_APPLICATION_HANDLES_OPEN` gives you
  D-Bus-based single-instance and `Open`/`Activate` for free. Qt requires
  `QtSingleApplication`-style code or your own lock file + D-Bus name.
- **⚠️ GOTCHA:** a lock file in `/tmp` is not a correct single-instance mechanism — it
  survives crashes, breaks across users, and fails under Flatpak. Own a D-Bus name.

---
