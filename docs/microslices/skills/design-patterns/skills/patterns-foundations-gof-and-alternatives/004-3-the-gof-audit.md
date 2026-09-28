---
id: skill-3-the-gof-audit-52facdaa30
purpose: 3 the gof audit
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-foundations-gof-and-alternatives/SKILL.md
requires: ["skill-2-the-honest-critique-of-gof-9b4c8fde81"]
links: ["skill-4-functional-and-data-oriented-alternatives-2d0b55ce92"]
---

## §3. The GoF Audit

**[VERSIONED — the verdicts depend on your language, and that's the point.]**

### 3.1 Largely obsolete or absorbed into languages

| Pattern | What happened |
|---|---|
| **Iterator** | **Built into every modern language.** `for…of`, generators, `IEnumerable`, `Iterator`. ⚠️ Emulating the GoF recipe in Python is explicitly pointless — the language *is* the pattern |
| **Singleton** | ⚠️ **Widely regarded as an anti-pattern now** (§14 → `patterns-reference`). In Python and JS, **modules are natural singletons**. Where you genuinely need one instance, DI container lifetime management is the modern answer |
| **Command** | **A function is a command.** The pattern existed to give a callable first-class status in languages that lacked it. ⚠️ Still earns its keep when you need undo/redo, queuing, or serializable operations — the *object* buys you something the closure doesn't |
| **Strategy** | **A function parameter.** ⚠️ Though see §2.2 — when strategies carry state, configuration, or need naming and discovery, the object form still has value |
| **Template Method** | Inheritance-heavy and **⚠️ composition generally wins in modern codebases.** Higher-order functions do this without the inheritance tree |
| **Prototype** | Absorbed by `clone`/copy semantics, and by JS's prototype model outright |
| **Interpreter** | Rarely hand-rolled; parser generators and existing DSL tooling win (see a parsing reference) |

### 3.2 Still genuinely useful

| Pattern | Why it survives |
|---|---|
| **Adapter** | ⚠️ **Permanently useful.** Impedance mismatch between your code and someone else's interface never goes away. The core of hexagonal architecture (§6.2 → `patterns-architectural`) |
| **Facade** | Simplifying a complex subsystem is a durable need |
| **Decorator** | Composable behaviour layering — middleware, wrappers, Python decorators, HTTP handler chains. **This one arguably got *more* important** |
| **Observer** | Underpins every event system, reactive framework, and pub/sub. ⚠️ **Now usually reached via a library** (RxJS, signals, event emitters), not hand-rolled |
| **Composite** | Trees where leaves and nodes share an interface — UI, filesystems, expression trees |
| **Builder** | ⚠️ **Genuinely valuable** in languages without named/default/optional arguments. **Largely unnecessary in Python or Kotlin.** A clean language-dependence example |
| **State** | Explicit state machines are underused and this pattern names them well |
| **Proxy** | Lazy loading, remoting, access control, caching. Every ORM lazy-loading implementation |
| **Flyweight** | Niche but real — string interning, glyph caches, ECS |
| **Visitor** | ⚠️ Awkward, but **the right answer for operations over a stable type hierarchy** (compilers, ASTs). **Pattern matching and sum types replace it more cleanly** where available (§4) |

### 3.3 Situational
**Factory Method / Abstract Factory** — ⚠️ **heavily over-applied**, but real when object
creation genuinely varies by configuration or platform. **Bridge** — real when two
dimensions vary independently, rare in practice. **Chain of Responsibility** — middleware
pipelines are exactly this and are everywhere. **Mediator** — can degenerate into a god
object (§14 → `patterns-reference`). **Memento** — undo and snapshots.

---
