---
id: skill-13-the-kernel-development-process-bdd52622a5
purpose: 13 the kernel development process
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-debugging-process-and-hardening/SKILL.md
requires: ["skill-12-debugging-and-observability-65da5206a8"]
links: ["skill-14-security-and-hardening-434cf64a8e"]
---

## §13. The Kernel Development Process

### 13.1 How change actually happens

```
you → patch → subsystem mailing list + MAINTAINERS entries (get_maintainer.pl)
   → review (expect several rounds; v2, v3, v4 are normal and not an insult)
      → maintainer's -next tree → linux-next (integration testing)
         → MERGE WINDOW (2 weeks after a release) → Linus's tree
            → rc1 … rc7 (~7 weeks of stabilization)
               → release (~9–10 week cadence)
                  → -stable backports (Fixes: tag / Cc: stable@vger.kernel.org)
```

**Practical mechanics:**
- `scripts/get_maintainer.pl -f path/to/file.c` tells you exactly who to send to. Use it.
- `scripts/checkpatch.pl --strict` before every send.
- **Plain-text email, no HTML, no attachments.** `git send-email`, or `b4` which is now
  the ergonomic path for both sending and applying series.
- Subject: `[PATCH v3 2/5] subsystem: short imperative summary`.
- A **`Fixes: <12-char-sha> ("subject")`** tag is how a fix gets auto-backported to stable.
- Changelog **below** the `---` line for the version history; commit message above.
- `Reviewed-by`, `Acked-by`, `Tested-by`, `Reported-by`, `Closes:` are meaningful and
  tracked.
- Response to review is expected within a reasonable time; silence means the patch dies.

**[DURABLE] The commit message matters as much as the code.** Explain *why*, not *what* —
the diff shows what. A maintainer reading it in three years during a bisect needs the
reasoning.

### 13.2 Versioning and stable trees [VERSIONED — this changed in 2026]

**Version numbers carry no semantic meaning.** Linus increments the major number when the
minor gets uncomfortably large, not at milestones. **Linux 7.0 released 12 April 2026**
after 6.19, and **7.1 and 7.2 followed** on the ordinary ~9–10 week cadence; it is "a
normal continuation, not a major architectural break."

| Tree | Meaning |
|---|---|
| **mainline** | Linus's tree. `rc` releases during stabilization |
| **stable** | Point releases of the current release, weeks of support |
| **longterm (LTS)** | Multi-year support. **Each new LTS starts with a ~2-year projected EOL that gets extended if industry helps maintain it** |

**Current LTS set (Aug 2026):** 5.10, 5.15, 6.1, 6.6, 6.12, 6.18. In **February 2026**
Greg Kroah-Hartman **extended support for 6.6, 6.12, and 6.18** after discussions with
device manufacturers and embedded vendors — 6.18 now runs to at least **December 2028**.
**5.10 and 5.15 both EOL 31 December 2026** — if you're on either, the clock is running.

> **⚠️ GOTCHA — non-LTS releases get only a few months.** 7.0 reached EOL on
> **27 June 2026**, roughly ten weeks after release. Shipping a product on a non-LTS
> kernel means shipping a kernel that stops getting security fixes almost immediately.
> **Anchor products to an LTS.**

### 13.3 CVEs — and the flood

**[VERSIONED, and a genuine operational problem.]** In February 2024 **kernel.org became
its own CNA**. Two consequences designed in from the start: CVEs are assigned only *after*
a fix exists, and the team **errs on the side of assigning CVEs to all fixes** — because,
as the documentation puts it, almost any bug might be exploitable and exploitability is
usually not evident when the bug is fixed.

The result: **the Linux kernel is now the single largest issuer of CVEs**, at roughly
fifty a week, **with no severity scores attached**, because the kernel community treats a
CVE as an identifier for a fix rather than an alarm. In July 2026, **432 kernel CVEs were
published in under 48 hours**, prompting a public argument on oss-sec about whether
per-CVE prioritization is even feasible at that volume.

**[CONTESTED] Whether this is good.** *For:* it's honest — other vendors avoid assigning
CVEs unless exploitability is unambiguous, which systematically undercounts risk; and the
kernel's advice ("run a maintained stable kernel and take the point releases") is the
correct advice regardless. *Against:* a stream of unscored CVEs destroys the signal that
CVE was created to provide, and pushes triage cost onto every downstream consumer.

**The practical consequence, and it is now a legal one:** severity triage is the device
maker's job. Under the **EU Cyber Resilience Act** — vulnerability and incident reporting
obligations start **11 September 2026**, full obligations **11 December 2027** — the
kernel is a component in your SBOM and its vulnerabilities are your duty to handle.
**The cheapest compliant strategy is exactly what the kernel community has always
recommended: stay on a maintained LTS and take the point releases.** Do not attempt to
cherry-pick individual "important" fixes at a rate of fifty a week.

---
