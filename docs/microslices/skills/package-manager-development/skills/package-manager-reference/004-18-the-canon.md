---
id: skill-18-the-canon-933053fc02
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-2433908836"]
links: ["skill-19-quick-reference-bd73541889"]
---

## §18. The Canon

### 18.1 Foundational writing

| Author | Work | Why |
|---|---|---|
| **Natalie Weizenbaum** | *PubGrub: Next-Generation Version Solving* (2018) | The algorithm now in Dart, uv, Poetry, Bundler, and slated for Cargo. Read the blog post *and* `dart-lang/pub/doc/solver.md` |
| **Russ Cox** | *Go & Versioning* series — esp. *Minimal Version Selection*, *The Principles of Versioning in Go*, ***Version SAT*** | The best-argued minority position in the field, plus the clearest statement of why the problem is NP-complete |
| **Di Cosmo, Mancinelli, Vouillon et al.** | The **EDOS** work; *Dependency solving: a separate concern in component evolution management* | The original NP-completeness proof and the "dependency solving is a separate concern" framing |
| **Hynek Schlawack** | *Semantic Versioning Will Not Save You* | The strongest, most-cited critique of SemVer-as-guarantee |
| **Hyrum Wright** | Hyrum's Law | One sentence that explains why every compatibility scheme leaks |
| **Winters, Manshreck, Wright** | *Software Engineering at Google* (the versioning chapter) | The extended argument against SemVer, and the "live at HEAD" alternative |
| **Andrew Nesbitt** | `nesbitt.io` — *Dependency Resolution Methods*, package-management reading lists; **ecosyste.ms** | The best single index of how each ecosystem actually resolves, and cross-ecosystem data |
| **Eelco Dolstra** | The Nix thesis, *The Purely Functional Software Deployment Model* | The most rigorous rethinking of what a package manager is |
| **Pinckney et al.** | *PacSolve* / *MaxNPM* | Research on customizable resolution objectives beyond "any valid solution" |

### 18.2 Primary sources

- **Specs**: `semver.org`; **PEP 440** (versions), **PEP 508** (dependency specifiers),
  **PEP 517/518/621** (build/metadata), **PEP 658/714** (metadata-only fetches),
  **PEP 700** (upload timestamps), **PEP 740** (attestations), **PEP 751** (pylock),
  **PEP 807** (trusted publishing), and the canonical `pylock.toml` spec on the **PyPA
  specs page** (the PEP is explicitly a historical document).
- **Ecosystem docs**: `go.dev/ref/mod` (the best-written package-manager reference in
  existence, full stop); the **Cargo Book**; **npm docs** on provenance and trusted
  publishing; the **pnpm** docs on the store and linker; `docs.rs/pubgrub`.
- **Security**: **SLSA** (`slsa.dev`), **Sigstore** (`sigstore.dev` and its blog),
  **in-toto**, **OSV** (`osv.dev` — the interoperable advisory format), **OpenSSF
  Scorecard**, and the OpenSSF **Securing Software Repositories WG**
  (`repos.openssf.org`) — whose *Build Provenance for All Package Registries* guide is the
  implementation manual if you're adding provenance to a registry.
- **Incident reporting** (for how attacks actually work): Microsoft Threat Intelligence,
  Unit 42, JFrog Security Research, Socket, ReversingLabs, Datadog Security Labs,
  Sonatype, Aikido. These are vendor blogs with commercial incentives — cross-read them,
  but they are where the technical detail lives.
- **PyPI blog** (`blog.pypi.org`) and **discuss.python.org/c/packaging** — packaging policy
  is decided in public there; **GitHub Changelog** and the **npm blog** for the JS side.

---
