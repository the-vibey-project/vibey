---
id: skill-8-supply-chain-security-99afb69e75
purpose: 8 supply chain security
source: src/vibey_tools/skills/plugins/package-manager-development/skills/package-manager-supply-chain-and-workspaces/SKILL.md
requires: []
links: ["skill-9-lifecycle-scripts-and-building-8b40fb61eb"]
---

## §8. Supply-Chain Security

### 8.1 The 2025–2026 npm worm era — what actually happened, because it changed the design space

**[ECOSYSTEM, but the lessons are universal.]** This is the most important recent case
study in package-manager security, and its details matter.

**Timeline:**
- **September 2025 — Shai-Hulud.** A **self-replicating worm** (named for the workflow file
  `shai-hulud-workflow.yml` it dropped, a *Dune* reference) entered via maintainer
  phishing. It injected malicious **postinstall** scripts, stole credentials, then — the
  novel part — **used the stolen npm token to authenticate as the compromised developer,
  enumerate their other packages, inject itself, and publish new versions.** Exponential
  spread with no attacker involvement. It also created public GitHub repos named
  "Shai-Hulud" containing the victim's exfiltrated secrets. GitHub removed 500+ compromised
  packages and blocked uploads matching the malware's IoCs.
- **November 2025 — Shai-Hulud 2.0.** Moved from **postinstall to preinstall**, widening
  impact to run before installation even completed.
- **2026 — continued waves**: "The Third Coming" (April), "Mini Shai-Hulud" (April–May,
  attributed to TeamPCP), and **August 2026's "ChainDrop"** — a Mini Shai-Hulud variant
  that compromised **`keyv`, `flat-cache`, `cache-manager` and 400+ packages across
  multiple unrelated publishers, ~2 billion monthly installs, within hours.** Microsoft's
  analysis describes a heavily obfuscated **Bun-based** payload executing via npm
  `preinstall`, harvesting npm, GitHub, AWS, Kubernetes, and HashiCorp Vault credentials.
- **The tradecraft shift that matters most:** earlier waves published using stolen tokens.
  **The 2026 waves increasingly ride the victim project's own release workflow** — pushing
  to `main` and cutting a release through legitimate CI. JFrog documented one sample that,
  inside a *specific* GitHub Actions run, requested an Actions OIDC token with audience
  `npm:registry.npmjs.org` — i.e. **abusing trusted publishing itself.**
- Parallel campaigns hit PyPI: **LiteLLM 1.82.7/1.82.8 (24 March 2026, ~95M monthly
  downloads) and telnyx 4.87.1/4.87.2**, part of a chain that began with a compromise of
  the **Trivy GitHub Action**. The LiteLLM payload used a **`.pth` file**, which
  auto-executes on *every interpreter start* — no import required.

**Scale context**: ReversingLabs measured a **73% year-over-year increase in malicious
open-source packages**, with npm accounting for roughly 90% of open-source malware;
Sonatype tracked 512,847 malicious packages in a single year.

**[DURABLE] The five design lessons:**
1. **Lifecycle scripts are the primary payload delivery mechanism.** See §9.
2. **A publishing credential is a lateral-movement primitive**, not just a secret. Any
   design where one credential can publish many packages is a worm substrate.
3. **Signing and provenance are necessary but not sufficient.** A worm that publishes
   through the victim's real CI earns a *legitimate* attestation. The VentureBeat framing
   is exact: the worm "didn't fake its security check — it earned a legitimate one."
4. **Detection speed is now a design parameter.** Socket reported average detection at
   ~5 minutes 18 seconds after publication during the August wave — and hundreds of
   packages still propagated.
5. **Containment beats prevention.** The controls that actually limited damage were
   short-lived credentials, script execution defaults, cooldowns, and blast-radius limits —
   not detection.

**npm's response** (worth knowing as the reference remediation): mandatory 2FA for
publishing, **revocation of legacy never-expiring tokens**, granular access tokens with
short expiry, and trusted publishing so build systems push without stored credentials.

### 8.2 The attack taxonomy

| Attack | Mechanism | Defense |
|---|---|---|
| **Typosquatting** | `reqeusts`, `python-dateutil` vs `dateutil` | Name-similarity checks at publish, install-time warnings |
| **Dependency confusion** | Public package shadows a private one of the same name | **Scoped/namespaced private packages; never let a public index satisfy an internal name.** Configure per-registry scope pinning |
| **Maintainer account takeover** | Phishing, credential stuffing | Mandatory 2FA/WebAuthn, trusted publishing |
| **Token theft** | Exfiltrated from CI, dotfiles, a compromised machine | Short-lived OIDC credentials; no long-lived tokens |
| **Self-replicating worm** | Stolen token → publish to all your packages | §8.1; per-package publish scoping |
| **Malicious maintainer / hostile handoff** | Legitimate owner turns, or hands the package to an attacker | Ownership-change alerts, cooldowns, code review of updates |
| **Protestware / sabotage** | Author deliberately breaks or wipes | Lockfiles + cooldowns + vendoring for critical paths |
| **Release poisoning** | Add a malicious file to an old, trusted release | §5.3 → `package-manager-registries-and-installation` — PyPI's 14-day rule |
| **Repojacking / name reuse** | Take over an abandoned name or deleted repo | **Never allow name reuse**; verify repo ownership continuously |
| **Compromised build tool** | The CI action itself is backdoored (Trivy, KICS in 2026) | Pin actions **by commit SHA, never by mutable tag** |
| **`.pth` / import-time execution** | Python-specific auto-execution | Restrict what installs may place on `sys.path` |
| **Compromised mirror / MITM** | Substituted bytes | TLS + lockfile hashes + transparency logs |

> **⚠️ GOTCHA — mutable references are a recurring root cause.** The March 2026 LiteLLM and
> Telnyx compromises traced to a **mutable reference in their use of the Trivy GitHub
> Action**. `uses: some/action@v1` is a moving target controlled by someone else. Pin to a
> full commit SHA. This single practice would have prevented multiple 2026 incidents.

### 8.3 Registry-side controls worth building

- **Mandatory 2FA / WebAuthn for publishing**, especially for high-impact packages.
- **Trusted publishing** and deprecation of long-lived tokens (§7.1 → `package-manager-registries-and-installation`).
- **Provenance generation by default**, not opt-in (§7.2 → `package-manager-registries-and-installation`).
- **Quarantine**, not delete — freeze a suspected package pending investigation while
  preserving existing installs.
- **Name-similarity scoring at publish time** and an appeals process.
- **Publish-event alerting to maintainers**, so an unexpected release is noticed in minutes.
- **A public, machine-readable advisory feed** (OSV format is the interoperable standard).
- **Malware scanning at ingest** — imperfect, but the August 2026 detection times show it
  meaningfully compresses exposure windows.
- **Upload timestamps in the API** so clients can implement cooldowns.

### 8.4 Client-side controls — and the one with the best evidence

**Cooldowns / minimum release age are the highest-value new control.** The idea: refuse to
install a version published less than N days ago, so the ecosystem's detection machinery
gets a chance first.

- **pip 26.1 (April 2026) added `--uploaded-prior-to`**; **uv has `--exclude-newer`**;
  **pnpm has `minimum-release-age`**; Dependabot has a cooldown setting. All rely on
  registry-reported upload timestamps (PEP 700 in Python).
- **The reported evidence**: research cited alongside the pip 26.1 release found that a
  **7-day cooldown would have prevented 8 out of 10 analyzed supply-chain attacks from
  reaching end users**. That is an unusually strong result for a control this cheap.
- **The honest limitations**, which the pip team and others state plainly: it does not stop
  a sophisticated attack that evades detection for longer, does nothing about
  vulnerabilities in packages you already depend on, and **delays security patches** — so
  you need an expedite path for genuine fixes.

The rest of the client-side baseline:
- **`--frozen-lockfile` / `ci` mode everywhere in CI.** Never resolve in CI.
- **Disable lifecycle scripts by default** (§9), allowlisting the few that need them.
- **Pin CI actions by SHA.**
- **Generate an SBOM per build** (SPDX or CycloneDX; `npm sbom`, `syft`) — this is what
  turns "are we affected?" from a week into minutes, and is increasingly a legal
  requirement (§14.3 → `package-manager-ux-ecosystems-and-governance`).
- **Verify provenance where available** — prefer packages with attestations, and pin
  *publisher identities* where your tooling supports it.
- **Vendor or mirror** the dependencies of anything you cannot afford to have change.

---
