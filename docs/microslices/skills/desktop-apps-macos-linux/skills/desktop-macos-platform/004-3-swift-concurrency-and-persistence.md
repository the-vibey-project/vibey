---
id: skill-3-swift-concurrency-and-persistence-8771448e9d
purpose: 3 swift concurrency and persistence
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-macos-platform/SKILL.md
requires: ["skill-2-macos-ui-swiftui-and-appkit-419098117f"]
links: []
---

## §3. Swift, Concurrency, and Persistence

### 3.1 Language baseline

- **Swift 6.x is current** (Xcode 26.4 ships Swift 6.3; language *modes* 4/4.2/5/6 are
  selectable per target). Objective-C remains fully supported and is still load-bearing in
  large codebases; new code should be Swift.
- **`@Observable`** (Observation framework) replaced `ObservableObject`/`@Published` for
  most purposes: finer-grained invalidation (SwiftUI only re-renders views that read the
  properties that actually changed), less boilerplate, no `objectWillChange` plumbing.
- Value types by default; `struct` for models, `final class` when you need identity,
  `actor` for shared mutable state.

### 3.2 Swift 6 strict concurrency — the migration everyone is doing

Swift 6 makes **data-race safety a compile-time guarantee**: warnings in Swift 5 mode
become errors. Core concepts:

| Concept | Meaning |
|---|---|
| `Sendable` | Marker protocol: values of this type can safely cross concurrency domains. Structs of Sendable members get it synthesized; classes only if immutable (`final` + all `let`) or internally synchronized. |
| `actor` | Reference type with automatic mutual exclusion on its state. |
| `@MainActor` | Global actor for UI. Everything touching views/view models belongs here. |
| `nonisolated` | Opt a member out of its actor's isolation (must not touch isolated state). |
| `nonisolated(unsafe)` | "Trust me." Last resort; document why. |
| `@preconcurrency` | Import a not-yet-audited module without drowning in errors. |

```swift
// The canonical shapes.
@MainActor @Observable
final class DocumentViewModel {              // UI state — main actor
    var items: [Item] = []
    var isLoading = false

    private let store: ItemStore              // an actor

    func refresh() async {
        isLoading = true
        defer { isLoading = false }
        items = await store.fetchAll()        // compiler inserts the hop
    }
}

actor ItemStore {                             // shared mutable state — isolated
    private var cache: [UUID: Item] = [:]
    func fetchAll() -> [Item] { Array(cache.values) }
    func insert(_ item: Item) { cache[item.id] = item }
}

struct Item: Sendable, Identifiable {         // crosses boundaries — must be Sendable
    let id: UUID
    var title: String
}
```

**[IMPORTANT, and recent] Swift 6.2 changed the ergonomics substantially.** The
"approachable concurrency" work (`SWIFT_APPROACHABLE_CONCURRENCY = YES`, on by default for
new Xcode 26 projects) **inverts the default**: code is main-actor-isolated unless you say
otherwise, and `nonisolated` async functions run on the *caller's* actor rather than
hopping. `@concurrent` is the explicit escape hatch for pushing CPU-heavy work
(decoding, image processing) off the main actor.

**[CONTESTED]** Whether this is an improvement: proponents say the old model buried the
signal in a wall of Sendable errors and drove people to slap `@unchecked Sendable` on
everything, so a safe-by-default model that's easy to use correctly is a net win.
Critics — notably the "Swift Concurrency is a Mess in 2026" line of argument — say the
repeated model changes eroded trust, and that main-actor-by-default hides main-thread
bottlenecks from developers who never learn to move work off it. Both observations are
accurate; which dominates depends on team seniority.

**Migration strategy that works** (from teams who've done it on 50K+ LOC):
1. Stay in Swift 5 mode; turn on **complete** strict-concurrency *checking* to surface
   warnings without breaking the build.
2. Fix **module by module**, leaf-first. Flip each target to Swift 6 mode as it goes clean.
3. Order of operations: `@MainActor` on view models and UI-adjacent classes → `Sendable`
   on value types that cross boundaries → `actor` for shared mutable services → globals
   last (`static let` + Sendable, or `@MainActor`, or as a last resort
   `nonisolated(unsafe)` with a comment explaining the invariant).
4. Expect a cascade: annotating one class forces its callers async, which forces theirs.
   Budget real time; one documented migration touched 79 files and ~2,800 lines for a
   mid-size app.

> **⚠️ GOTCHA — the singleton.** `static var shared` is non-isolated global mutable state
> and is an error in Swift 6. Fix with `static let` + `Sendable`, or `@MainActor static let`,
> or convert the type to an `actor`. Do not reach for `nonisolated(unsafe)` first.

### 3.3 Persistence on macOS

| Option | Use when | Watch out for |
|---|---|---|
| **UserDefaults** | Small preferences, window state | Not for data. Not synchronized across processes reliably. |
| **SwiftData** | New apps, macOS 14+/iOS 17+, SwiftUI-shaped models | Younger; heavyweight/custom migrations and some CloudKit sync modes still weak; measurable overhead at 10K+ rows |
| **Core Data** | Existing apps, complex object graphs, 15+ entities, batch ops, older OS support | Verbose; concurrency model fights modern Swift; `.xcdatamodeld` is an Xcode-bound artifact |
| **GRDB / SQLiteData** | Data-heavy apps, you want SQL and control, fastest reads/bulk writes | More glue code for SwiftUI reactivity; no free CloudKit |
| **Plain files (JSON/plist/SQLite)** | Document-based apps, simple state | You own migration and atomicity |

**[CONTESTED] SwiftData vs Core Data in 2026.** SwiftData is built on Core Data's storage
engine and has been stable across three major OS releases; for new apps with SwiftUI it's
the productivity default. But real teams still choose Core Data for complex models — the
common counterargument is roughly "15 entities with intricate relationships, two decades
of Core Data hardening versus three years of SwiftData, and the abstraction layer's
stability doesn't automatically inherit the storage engine's." Both positions are held by
people shipping real apps. A third camp (growing) picks **GRDB** and skips the object
graph entirely.

**[UNIVERSAL] Whatever you pick: design the migration story before v1 ships.** Desktop
apps hold years of irreplaceable user data. A schema you can't migrate is a product you
can't update.
