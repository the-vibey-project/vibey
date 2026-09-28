---
id: skill-13-the-ecosystem-comparison-de9fe14b30
purpose: 13 the ecosystem comparison
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-ux-ecosystems-and-governance/SKILL.md
requires: ["skill-12-ux-42db1816fc"]
links: ["skill-14-governance-and-sustainability-43da3d92f3"]
---

## §13. The Ecosystem Comparison

| | **npm** | **pip / uv** | **Cargo** | **Go modules** | **Maven** | **apt/dnf** | **Nix** |
|---|---|---|---|---|---|---|---|
| Manifest | `package.json` | `pyproject.toml` | `Cargo.toml` | `go.mod` | `pom.xml` | control/spec | `.nix` |
| Lockfile | `package-lock.json` | `uv.lock` / `pylock.toml` | `Cargo.lock` | `go.sum` (hashes; `go.mod` pins) | none native | none | `flake.lock` |
| Resolution | backtracking, npm semantics | pip: backtracking; **uv: PubGrub + forking** | backtracking (**PubGrub designated as replacement**) | **MVS** | nearest-wins mediation | **SAT (libsolv)** | none — exact inputs |
| Ranges | yes | yes | yes | **no** | yes | yes | n/a |
| Multiple versions | **yes** | no | **yes (semver-incompatible)** | **yes (via `/vN` import paths)** | no | no | **yes (by hash)** |
| Layout | hoisted/isolated/PnP | flat venv | compiler `--extern` | module cache | classpath | system-wide | content-addressed store |
| Install-time code | **yes (scripts)** | wheels: no; sdists: yes | `build.rs` | **no** | plugins | maintainer scripts | sandboxed builds |
| Namespacing | flat + `@scope` | flat | flat | **domain-derived** | **reverse-DNS** | flat | flat |
| Provenance | **Sigstore/SLSA, GA** | **PEP 740 attestations** | trusted publishing GA; signing proposed | `sum.golang.org` (integrity, not provenance) | PGP; Sigstore emerging | distro signing | hashes |
| Signature model | keyless (Sigstore) | keyless (Sigstore) | — | transparency log | PGP web-of-trust | distro keyring | — |

**Reading this table is the fastest way to see that there are no universal answers, only
consistent trade-off *sets*.** Go trades expressiveness for determinism at every single
row. npm trades strictness for compatibility. Nix trades familiarity for correctness.

---
