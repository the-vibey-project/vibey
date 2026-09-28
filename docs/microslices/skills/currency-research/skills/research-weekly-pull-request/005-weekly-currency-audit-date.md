---
id: skill-weekly-currency-audit-date-88aa01c4a3
purpose: weekly currency audit date
source: src/vibey_tools/skills/plugins/currency-research/skills/research-weekly-pull-request/SKILL.md
requires: ["skill-the-pull-request-body-3b66f6bf25"]
links: ["skill-scope-limits-for-an-unattended-run-b663436ebf"]
---

## Weekly currency audit — <date>

Audited: <plugin>, <plugin>, <plugin>  (rotation slice N of M)

### Changes proposed

**<plugin> — `<skill>` §<N>**
- **Was:** <the existing claim, quoted or closely paraphrased>
- **Now:** <the replacement>
- **Source:** <publisher>, *<title>*, <date> — <what it actually says>
- **Confidence:** <direct statement / inference / single source>

### Checked, unchanged

- **<plugin> §<N>** — <claim> still current as of <source + date>.

### Unresolved

- **<plugin> §<N>** — <what is ambiguous, what you looked for, why you did not edit>
```

Rules for the body:

- **Quote the before-state.** A reviewer cannot judge an edit they have to reconstruct.
- **Name the source inline.** "Per the vendor's changelog" is not a source; the changelog with
  its date is.
- **List what you checked and did not change.** This is the most valuable section for the next
  run, and the one most often omitted.
- **Put genuine uncertainty in "Unresolved" rather than resolving it yourself.** A question
  raised is worth more than a wrong edit made.
- **State the tool honestly.** The run is automated; say so, and do not write the body as
  though a person did the reading.

---
