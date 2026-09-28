---
id: skill-9-lifecycle-scripts-and-building-8b40fb61eb
purpose: 9 lifecycle scripts and building
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-supply-chain-and-workspaces/SKILL.md
requires: ["skill-8-supply-chain-security-99afb69e75"]
links: ["skill-10-workspaces-monorepos-and-overrides-a610e5e369"]
---

## §9. Lifecycle Scripts and Building

### 9.1 The problem, stated plainly

**[DURABLE] Arbitrary code execution at install time is the original sin of package
management.** `npm install` running `preinstall`/`postinstall`, `pip install` executing
`setup.py`, `gem install` running `extconf.rb` — in every case, *fetching a dependency
executes attacker-controlled code with the developer's full privileges.*

Every major worm in §8.1 used this. Shai-Hulud's move from `postinstall` to `preinstall`
was specifically to execute *before* installation completed, widening the blast radius.

### 9.2 Why it exists, and how ecosystems escaped it

It exists because native code needs compiling and platforms differ. The escapes, in order
of how well they worked:

1. **Prebuilt binary artifacts.** Python's **wheels** are the great success story here: a
   wheel is a zip that is *installed by copying*, with no code execution. The
   `manylinux`/`musllinux`/`macosx` platform tag scheme made prebuilt binaries portable.
   **This single change removed install-time execution from the overwhelming majority of
   Python installs** — and it's why sdists (which do run `setup.py`) are now the risky path.
2. **Declarative build metadata.** `pyproject.toml`'s `[build-system]` replaced executable
   `setup.py` configuration with data. Cargo's `Cargo.toml` was declarative from birth
   (with `build.rs` as a deliberate, visible exception).
3. **Separate build from install.** Go does not execute dependency code at fetch time at
   all — it compiles it as part of *your* build, which is a different and much better trust
   boundary.
4. **Default-off with an allowlist.** pnpm's `onlyBuiltDependencies` is the pragmatic
   modern answer: scripts don't run unless you name the package. npm has `--ignore-scripts`.
   Bun and Yarn have equivalents.

**[DURABLE] If you are designing a package manager today: do not run install-time scripts
by default.** Provide an explicit, per-package allowlist that lives in the manifest and is
reviewable in a diff. The compatibility cost is real (native modules — node-gyp builds,
`sharp`'s prebuilt binaries, Prisma's engine downloads — all use postinstall) and it is
worth paying.

### 9.3 If you must run them

- **Sandbox**: no network, restricted filesystem, no access to credentials or environment
  secrets. Nix and Guix's build sandboxes are the reference implementations.
- **Log everything** the script does, visibly.
- **Never run scripts for transitive dependencies the user didn't name**, at minimum
  without a prompt.
- **Deterministic environment**: fixed `PATH`, no ambient config, no `$HOME` dotfiles.

### 9.4 Binary distribution design

If you ship prebuilt artifacts, you need a **platform tag scheme** answering: OS, libc
(glibc version! musl!), CPU architecture, and language/ABI version. Python's
`manylinux_2_28_x86_64` encodes a glibc floor; that design is worth copying because it
expresses *forward* compatibility rather than distro identity.

Also decide: what happens when there's no matching binary? Fall back to source (and thus to
executing a build), or fail? Both answers are defensible; **silently falling back to source
build is how "it worked on my machine and took 40 minutes in CI" happens.**

---
