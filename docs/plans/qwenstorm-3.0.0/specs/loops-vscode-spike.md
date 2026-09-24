## Title
research(vscode): record V-VS1–V-VS5 and V-CC1 for the sovereign Code - OSS adapter

ADR-0046 lane L20a (slug `loops-vscode-spike`).

**Implementer: the operator, or a large model with a shell on the operator's machines. Not the
local gpt-oss:20b.** This lane changes no code in the repository. Its deliverable is evidence,
recorded in the ADR-0046 draft, that every later VS Code lane is gated on.

## Why
Sub-doctrine 8.b (as amended by #392, `src/vibey_tools/gh/docs/doctrines.md` at integration
`d3b4a388`) puts "**VS Code** when its provider is local" in `sovereignloop` and "VS Code on a
paid provider" in `paidloop`, and repeals OpenCode once the VS Code adapter carries its work.
The operator ruled on 2026-09-22 that the sovereign adapter is **Code - OSS / VSCodium**
(Arch `extra/code`, binary `code`; macOS `vscodium` cask, binary `codium`), and that
Microsoft's build is `vscode-paid` (STORM-CONTEXT.md, "Operator rulings").

ADR-0046 §8 (`specs/ADR-two-loops.md:279-283`) says: "At this cutoff no evidence exists of a
headless, account-free way to drive an agent session in Code - OSS." Its *Verification owed*
list (`:465-470`) names V-VS1 to V-VS5 and V-CC1, and its *Owes* item 2 (`:8`) says the
verification "must be recorded before lane L20 starts". Issue-audit gap B1
(`issue-audit/gaps.md`, "B1") classes this as research that needs a packet capture and a
licence reading, so it is not a 20B lane.

CDD (sub-doctrine 9.c) needs the divergence to be bounded: if the evidence says no, `vscode`
stays off, the opencodeloop runner is not removed, and the operator decides (ADR-0046 §8).
Status is evidence-bounded (10.f): every claim below names its command, its output file and
its date. Nothing is asserted from memory or from a vendor's marketing page.

## Required behaviour
Timebox: **one working day**. Stop at the timebox and record what is known, with the
verdict `INFEASIBLE — timebox reached before <item>` if any item is still open.

Work on **macOS** (the operator's laptop) and, where an Arch Linux host is available, on
**Arch Linux** too (8.h). Record for each OS: `uname -a`, the editor version
(`codium --version` or `code --version`), and the extension version.

1. **Evidence folder.** Create `STORM/evidence/vscode/`.
   Every command below is run through `script`/`tee` so its full transcript lands there as
   `<item>-<os>.log` (for example `v-vs1-macos.log`). Redact any credential with
   `[REDACTED:<kind>]` and say so in the log's first line (7.c: record every redaction).
2. **V-VS5 first — tell the OSS build from Microsoft's.** Locate `product.json`:
   - macOS VSCodium: `/Applications/VSCodium.app/Contents/Resources/app/product.json`;
   - Arch Code - OSS: `/usr/lib/code/product.json` (verify the path with `pacman -Ql code | grep product.json`).
   Save each file as `product-<os>-oss.json`. If Microsoft's build is available on the
   machine, save its `product.json` too as `product-<os>-microsoft.json`. Record the fields
   that differ and that a doctor can test reliably (candidates to check, not facts:
   `nameShort`, `nameLong`, `applicationName`, `dataFolderName`, `quality`,
   `extensionsGallery.serviceUrl`, `licenseName`, `licenseUrl`). Write the rule you propose,
   for example "OSS iff `extensionsGallery.serviceUrl` is Open VSX's and
   `applicationName` is `codium` or `code-oss`", and the evidence for it.
3. **V-VS2 — pick the agent extension.** Evaluate, in this order, and stop at the first that
   passes every check (candidates to verify, never to assume): Continue, Cline, Roo Code. For
   each candidate record:
   - its Open VSX page URL and version (`codium --install-extension <id>` must install it
     from Open VSX with no Microsoft marketplace);
   - its licence: the SPDX id read from the extension's own `LICENSE` file inside the
     installed extension directory (`~/.vscode-oss/extensions/<id>-<ver>/` on macOS; verify
     the Arch path), saved as `licence-<id>.txt`. It must be OSI-approved;
   - whether any sign-in, account, or telemetry opt-out is required to run a session with a
     local model. It must need none.
4. **V-VS1 — a headless session to completion.** Find a command line that starts the editor
   on a given folder, runs one agent session from a prompt file to completion, and exits,
   with no GUI interaction. Candidate routes, to verify in this order: (a) a CLI the
   extension itself ships; (b) `codium --extensionDevelopmentPath <tiny driver extension>
   --extensionTestsPath <runner>`, which the editor's own test harness uses to run an
   extension without a user, under a virtual display on Arch (`xvfb-run`); (c) any other
   documented automation entry point of the extension. Record the **exact** command, its
   exit code, the wall time, the folder it edited, and the diff it produced
   (`git -C <folder> diff > v-vs1-diff-<os>.patch`). The session must be driven by a local
   model (step 5), not a hosted one.
5. **V-VS3 — only the local provider is contacted.** Write the per-run settings JSON that
   registers one OpenAI-compatible provider at `http://127.0.0.1:11434/v1` serving
   `gpt-oss:20b` (the 8.d designation), with nothing else configured. Save it as
   `settings-local.json`. Run the V-VS1 command again under a capture:
   - macOS: `sudo tcpdump -i any -w v-vs3-macos.pcap 'not (host 127.0.0.1 or host ::1)'`
     for the duration of the run, or a proxy (`mitmproxy`) with `HTTPS_PROXY` set, whichever
     the editor honours; record which;
   - Arch: the same with `tcpdump`.
   Summarise every non-loopback host contacted in `v-vs3-hosts-<os>.txt` (host, port, count,
   and what it is). The result passes only if the list is empty, or every entry is disabled
   by a recorded setting that the per-run settings file then includes.
6. **V-VS4 — the event stream.** Record what the session exposes while it runs (turns, tool
   calls, text, errors, completion) and how it is read (a log file, stdout JSON, an extension
   API a driver extension can subscribe to). Save a sample as `v-vs4-events-<os>.txt` and
   write a mapping table to the family vocabulary that vibey tails
   (`src/vibey/infrastructure/engines/loop_events.py:207-218` at integration `d3b4a388`:
   `run.started`, `turn.starting`, `turn.completed`, `text_delta`, `tool_result`,
   `capacity.rejected`, `finished`, `failed`). Every family event either maps from a named
   source event or is written down as "synthesised by the runner from <source>".
7. **V-CC1 — Claude Code.** Record Claude Code's licence (the `LICENSE` or licence field of the
   installed `@anthropic-ai/claude-code` package, saved as `licence-claude-code.txt`) and, with
   claudeloop's local profile (`claudeloop --profile local doctor`), the non-loopback hosts it
   contacts (same capture method as step 5), in `v-cc1-hosts-<os>.txt`. This confirms or
   refutes the ADR §9 flag that claudeloop-local is paid-side because the tool is not FOSS.
8. **Record in the ADR draft.** Append this section to the end of
   `STORM/specs/ADR-two-loops.md` (append only; never
   edit earlier text):
   ```
   ## Verification recorded (V-VS1..V-VS5, V-CC1)

   Recorded <YYYY-MM-DD> by <who>, on <macOS version/arch> and <Arch Linux kernel/arch or "not available">.
   Evidence: STORM/evidence/vscode/.

   - V-VS1 (headless session): <PASS|FAIL>. Command: `<exact command>`. Exit <n>, <seconds> s. Evidence: <files>.
   - V-VS2 (extension): <PASS|FAIL>. <id> <version>, <SPDX>, Open VSX <url>, account needed: <no|yes>.
   - V-VS3 (local provider only): <PASS|FAIL>. Settings: settings-local.json. Non-loopback hosts: <none|list>.
   - V-VS4 (event stream): <PASS|FAIL>. Source: <how read>. Mapping: <table or file>.
   - V-VS5 (OSS vs Microsoft): <PASS|FAIL>. Rule: <rule>. Fields: <fields>.
   - V-CC1 (Claude Code): licence <SPDX or "proprietary">; non-loopback hosts with a local profile: <list>.

   Editor binary per OS: macOS `<binary>`, Arch `<binary>`.
   Driver contract for lane L20h: <the command template, the settings file shape, the event source>.

   V-VS VERDICT: FEASIBLE
   ```
   The last line is exactly `V-VS VERDICT: FEASIBLE` only when V-VS1 to V-VS5 all pass on at
   least macOS; otherwise it is `V-VS VERDICT: INFEASIBLE — <the first failing item and why>`.
   Every gated lane greps for the exact string `V-VS VERDICT: FEASIBLE`.
9. **If INFEASIBLE.** Change nothing else. The bounded path (ADR-0046 §8): `vscode` stays off,
   the opencodeloop runner stays as a declared-only transitional adapter (#321), and the
   operator decides. Say so in the recorded section.
10. **After the later lanes land** (not part of this lane, recorded here so it is not lost):
    the operator runs `vibey doctor --conformance --engine vscode` live on Arch Linux and on
    macOS, and appends one line per OS to the same section:
    `V-VS CONFORMANCE: PASS <YYYY-MM-DD> <os>` (or `FAIL …`). The OpenCode-retirement lanes
    (`loops-retire-opencode-*`, `loops-remove-opencode-tenant`) are gated on
    `V-VS CONFORMANCE: PASS` for both OSes.

## Where to change
- New: `STORM/evidence/vscode/` and the files named above.
- Append-only: `STORM/specs/ADR-two-loops.md`.
- Nothing in the repository (`STORM/integration`).

## Acceptance criteria
- [ ] `grep -c "^- V-VS[1-5] " specs/ADR-two-loops.md` is 5 and `grep -c "^- V-CC1 " specs/ADR-two-loops.md` is 1.
- [ ] `grep -E "^V-VS VERDICT: (FEASIBLE|INFEASIBLE — .+)$" specs/ADR-two-loops.md` prints exactly one line.
- [ ] Every PASS names at least one evidence file, and each named file exists in `evidence/vscode/`.
- [ ] `settings-local.json` exists and names only a loopback provider.
- [ ] Every log whose content was redacted says so on its first line.
- [ ] `git -C STORM/integration status --porcelain` shows nothing this lane wrote.

## Tests to write first (TDD)
None: this lane is research. Its checks are the greps above. The executable tests for each
V-item are owed by the lanes it gates: `loops-vscodeloop-oss-driver` (V-VS1, V-VS3, V-VS4 as an
`integration` test with `VSCODELOOP_TEST_EDITOR`) and `loops-vscodeloop-doctor` (V-VS5, and the
loopback-only provider rule).

## Checks the lane must run (all must pass)
    cd STORM
    test "$(grep -c '^- V-VS[1-5] ' specs/ADR-two-loops.md)" = 5
    test "$(grep -c '^- V-CC1 ' specs/ADR-two-loops.md)" = 1
    test "$(grep -cE '^V-VS VERDICT: (FEASIBLE|INFEASIBLE — .+)$' specs/ADR-two-loops.md)" = 1
    ls evidence/vscode/
    git -C integration status --porcelain

## Out of scope
- Any code, test or packaging change in the repository (lanes `loops-vscode-engine-ids`
  through `loops-vscode-vibey-wiring`).
- The human-facing VS Code extension of #290 (updates/290.md), which is a different deliverable.
- Installing the editor as a product feature (lane `installer-vscode`); install it by hand here.
- CHANGELOG.md, docs/, the repository's ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees. The only document this lane writes is the storm's ADR draft section above, which the
  docs wave carries into `docs/architecture/decisions/`.
- Do not push, open a PR, or change git remotes.

**Depends on:** nothing.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
