---
id: skill-part-11-language-specific-debugging-patterns-c92bdf3bc2
purpose: part 11 language specific debugging patterns
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-10-ai-debugging-limitations-564d034c46"]
links: ["skill-part-12-advanced-debugging-tools-55f1401baf"]
---

## Part 11 — Language-Specific Debugging Patterns

### Python

- **`pdb`/`ipdb`**: commands `n` (next), `s` (step), `c` (continue), `p` (print), `bt` (backtrace), `l` (list), `q` (quit)
- **`breakpoint()`** builtin (Python 3.7+) — invokes pdb by default
- **py-spy** — sampling profiler that attaches to running processes without restart
- **objgraph** — reference graphs for memory leak investigation
- **mypy/pylint/pyflakes** — static analysis
- `logging.exception()` for full context including stack trace
- asyncio debug mode (`loop.set_debug(True)`)
- `raise X from Y` chaining; `contextlib.suppress`
- EAFP (Easier to Ask Forgiveness than Permission) vs LBYL (Look Before You Leap) — Python idiom prefers EAFP

### TypeScript/JavaScript

- **Chrome DevTools** — breakpoints, scope, network, performance, memory profiler
- **VS Code launch.json** — configurable debug sessions
- Source maps to map minified → source
- Extended console methods: `.error`, `.warn`, `.table`, `.group`, `.time`, `.trace`, `.assert`
- `--async-stack-traces` for better async debugging
- **React/Vue/Redux DevTools** browser extensions
- React error boundaries for component-level error isolation
- **Replay.io** — deterministic browser session recording; CI Agent auto-records every Playwright/Cypress test run and posts root-cause analysis as PR comment
- `unhandledRejection`/`uncaughtException` handlers for process-level error capture
- **neverthrow** — result types for TypeScript without exceptions

### Go

- **Delve** (`dlv debug/test/attach/core`) — the Go debugger
- **`go tool pprof`** — CPU/heap/goroutine/mutex/block flame graphs
- **`go test -race`** / **ThreadSanitizer** — race condition detection
- Runtime deadlock detector (built-in)
- **goleak** — goroutine leak detection in tests
- **`log/slog`** — standard library structured logging (Go 1.21+)
- **`go vet`/staticcheck** — static analysis
- `errors.Is`/`errors.As` (Go 1.13+), `%w` wrapping, sentinel and custom error types
- The `(value, error)` idiom — the Go team withdrew `if err != nil` reduction proposals in 2024–2025; the pattern will stay

### Java/JVM

- Diagnostic JVM flags: `-XX:+HeapDumpOnOutOfMemoryError`, `-XX:+PrintGCDetails`
- jstack (thread dumps), jmap (heap), jstat (statistics), jconsole/JMX
- VisualVM and Java Mission Control for live profiling
- SLF4J + Logback + MDC (Mapped Diagnostic Context)
- Java 14+ helpful NPE messages name the null variable
- Anti-pattern: wrapping checked exceptions in RuntimeException without context

### .NET/C#

- Visual Studio debugger (IntelliTrace historical debugging, pinned variables)
- `dotnet-dump`/`dotnet-trace`/`dotnet-counters`
- PerfView, BenchmarkDotNet
- WinDbg + SOS extension
- Serilog + `Microsoft.Extensions.Logging`
- OpenTelemetry for .NET

---
