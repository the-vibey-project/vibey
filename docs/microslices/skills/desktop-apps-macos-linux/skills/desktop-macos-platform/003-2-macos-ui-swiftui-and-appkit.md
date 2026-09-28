---
id: skill-2-macos-ui-swiftui-and-appkit-419098117f
purpose: 2 macos ui swiftui and appkit
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-macos-platform/SKILL.md
requires: ["skill-1-macos-platform-architecture-720e7ce771"]
links: ["skill-3-swift-concurrency-and-persistence-8771448e9d"]
---

## §2. macOS UI — SwiftUI and AppKit

### 2.1 The 2026 state of play

**[CONTESTED, and the most consequential macOS decision.]** The honest summary that
experienced Mac developers converge on: **almost nobody starts a new Mac app in pure
AppKit anymore, and almost no serious Mac app is pure SwiftUI.** The real skill is knowing
where the seam goes. Apple's own guidance (WWDC26 "Use SwiftUI with AppKit and UIKit") is
explicitly incremental: start new scenes in SwiftUI, keep existing AppKit, and there is
*no expectation* that an app becomes entirely SwiftUI.

**Case for SwiftUI on macOS:**
- Declarative state→UI eliminates a whole category of "view and model disagree" bugs.
- Dramatically less code for typical forms, lists, sidebars, settings.
- One codebase across macOS/iOS/iPadOS/visionOS when that matters.
- Apple's investment is entirely here; new APIs (including Liquid Glass adoption)
  land in SwiftUI first or exclusively.
- `@Observable` (the Observation framework) removed most of the `ObservableObject`
  boilerplate and its over-invalidation problems.

**Case for AppKit (still, in 2026):**
- **Dense, large data.** `NSTableView`/`NSOutlineView` with cell reuse still beat SwiftUI
  `List`/`Table` for tens of thousands of rows with complex cells. This is the single most
  commonly cited gap.
- **Deep menu, toolbar, and window customization** — non-native fullscreen, custom title
  bars, accessory view controllers, `NSWindow` subclassing behaviours.
- **Text.** `NSTextView`/TextKit 2 is a full text system; SwiftUI's `TextEditor` is not
  in the same category. Any editor, IDE, or writing app will use it.
- **Precise control over first responder, key equivalents, and focus.**
- **Backward deployment** to older macOS versions.
- Predictability: AppKit does what you told it. SwiftUI sometimes does what it inferred.

**The pragmatic architecture most shipping apps use:**
```
SwiftUI  → app structure (App/Scene), settings, sidebars, inspectors, simple lists,
           anything form-shaped
AppKit   → the one hard view (the editor, the canvas, the giant table), embedded via
           NSViewRepresentable / NSViewControllerRepresentable
Shared   → @Observable model layer that both read
```

### 2.2 SwiftUI on macOS — the Mac-specific parts

The parts of SwiftUI that only matter on the Mac, which iOS-shaped tutorials skip:

```swift
@main
struct MyApp: App {
    @State private var model = AppModel()          // @Observable, @MainActor

    var body: some Scene {
        // A document-based app gets New/Open/Save/Revert/Versions for free
        DocumentGroup(newDocument: MyDocument()) { file in
            EditorView(document: file.$document)
        }
        .commands {
            // Menu bar customization — Mac-only, and where most Mac apps live
            CommandGroup(replacing: .newItem) {
                Button("New Project…") { model.newProject() }
                    .keyboardShortcut("n", modifiers: [.command, .shift])
            }
            CommandMenu("Analyze") {
                Button("Run") { model.run() }.keyboardShortcut("r")
                Divider()
                Button("Clear Results") { model.clear() }
                    .disabled(model.results.isEmpty)     // menu items MUST disable
            }
        }

        // Settings scene → gets the standard ⌘, shortcut and window chrome
        Settings { SettingsView().frame(width: 520) }

        // A secondary utility window, openable via openWindow(id:)
        Window("Activity", id: "activity") { ActivityView() }
            .defaultSize(width: 400, height: 300)
            .keyboardShortcut("0", modifiers: .command)

        // Menu bar extra — the Mac's status-item idiom
        MenuBarExtra("Status", systemImage: "waveform") {
            StatusMenu()
        }
        .menuBarExtraStyle(.window)   // .menu for a plain menu, .window for a popover
    }
}

// Standard Mac three-column layout
struct RootView: View {
    var body: some View {
        NavigationSplitView {
            Sidebar()
        } content: {
            ItemList()
        } detail: {
            DetailView()
        }
        .toolbar { /* ... */ }
        .navigationSplitViewStyle(.balanced)
    }
}
```

**Mac-specific view modifiers worth knowing**: `.focusedSceneValue` (drive menu enablement
from the focused window's state — this is how you make menu items correctly gray out),
`.onKeyPress`, `.contextMenu`, `.draggable`/`.dropDestination`, `.fileExporter`/
`.fileImporter` (they route through the sandbox correctly), `.help()` (tooltips),
`.windowResizability`, `.defaultPosition`, `.presentedWindowToolbarStyle`.

### 2.3 The interop seam — where the money is

```swift
// Wrapping AppKit inside SwiftUI: the 90% case
struct TextEditorView: NSViewRepresentable {
    @Binding var text: String

    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSTextView.scrollableTextView()
        let tv = scroll.documentView as! NSTextView
        tv.delegate = context.coordinator
        tv.isRichText = false
        tv.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        return scroll
    }

    func updateNSView(_ scroll: NSScrollView, context: Context) {
        guard let tv = scroll.documentView as? NSTextView else { return }
        // ⚠️ Guard against feedback loops: only write if actually different,
        // or every keystroke round-trips and the cursor jumps to the end.
        if tv.string != text { tv.string = text }
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, NSTextViewDelegate {
        let parent: TextEditorView
        init(_ p: TextEditorView) { parent = p }
        func textDidChange(_ n: Notification) {
            guard let tv = n.object as? NSTextView else { return }
            parent.text = tv.string
        }
    }
}

// Wrapping SwiftUI inside AppKit: the incremental-adoption direction
let host = NSHostingController(rootView: InspectorView(model: model))
splitViewController.addSplitViewItem(NSSplitViewItem(viewController: host))
```

> **⚠️ GOTCHA — the `updateNSView` feedback loop.** This is *the* interop bug. SwiftUI
> calls `updateNSView` whenever any observed state changes; if you unconditionally write
> to the AppKit view, and the AppKit view's delegate writes back to the binding, you get
> an infinite loop or (more insidiously) a cursor that resets to position 0 on every
> keystroke. Always compare before assigning, and consider a "programmatic change" flag.

> **⚠️ GOTCHA — sizing.** `NSViewRepresentable` doesn't automatically communicate an
> intrinsic size to SwiftUI's layout. Set `intrinsicContentSize` on the NSView, or use
> `.frame()` / `sizeThatFits` explicitly, or you'll get a zero-height view and conclude
> the wrapper is broken.

### 2.4 Liquid Glass (macOS 26 Tahoe)

macOS 26 introduced **Liquid Glass**, the biggest visual change since 2013 — a translucent,
light-refracting material applied to toolbars, sidebars, menu bar, Dock, window controls,
sheets, and popovers. What developers need to know:

- **You get most of it for free.** Recompile against the macOS 26 SDK and framework-provided
  chrome (toolbars, sidebars, sheets, popovers, standard controls) adopts the new material
  with no code changes, whether you're on SwiftUI, UIKit, or AppKit.
- **Custom components do not.** Anything you drew yourself keeps its old look and will
  now clash. This is where the actual migration work is.
- The opt-in APIs are `.glassEffect()`, `GlassEffectContainer`, and `glassEffectID` for
  morphing between glass elements.
- **Icons** need rework through Apple's **Icon Composer** (layered vector content with
  blur/translucency, real-time specular highlights) — the old flat 1024px PNG workflow is
  obsolete.
- **[UNIVERSAL, and important]** Translucency is an accessibility hazard. Respect
  **Reduce Transparency** and **Increase Contrast**; test with both on. Text over a
  glass material at low contrast is a real WCAG failure, not a style preference.

**[CONTESTED]** Whether to adopt aggressively: proponents argue apps that don't adapt will
look broken beside system apps; skeptics note the material is expensive to render, hurts
legibility when misapplied, and that Apple's own first-year implementations drew
substantial criticism. The defensible middle: adopt the *system* chrome (free), use
semantic colors and system materials rather than hardcoded palettes, and be conservative
about applying `.glassEffect()` to your own content surfaces.

### 2.5 Mac Catalyst — when (not) to use it

Catalyst runs a UIKit iPad app on the Mac. **Its purpose is porting an existing iPad app**,
and that's the only case where it's the right call. For a new multiplatform product, a
SwiftUI multiplatform target produces a better Mac app for the same effort. Note also that
Apple silicon Macs can simply *run* unmodified iPad apps, which removes much of Catalyst's
original motivation. Catalyst apps consistently read as "not quite a Mac app" to Mac users
— wrong menu structure, wrong keyboard behaviour, wrong window resizing.

---
