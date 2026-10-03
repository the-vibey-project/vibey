# 0080 — Continuation prompts, kept current and run on GitHub every week

**Status:** accepted · **Date:** 2026-10-03 · **Issue:** [#1384](https://github.com/the-vibey-project/vibey/issues/1384) · **Cites:** sub-doctrines 8.a, 10.e, 10.f, 10.h, 12.d, 12.e and 12.h · **Related:** ADR-0039, ADR-0046, ADR-0047, ADR-0057, ADR-0075 · **Evidence:** `develop` at `913ee8a88`, read 2026-10-03; the minimum-specs record's CPU throughput for gpt-oss:20b on a GitHub-hosted aarch64 Ubuntu runner · **Canon:** drafts sub-doctrine 10.l, ratified by the operator's merge under Article II.3

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record and for
`docs/continuation/`; `docs/llms.txt` regenerated from that nav. All are in the change that
carries this record.

## Context

The project's continuity rested on people and sessions: an operator who remembers, and agent
sessions whose context ends. Twice in two weeks that failed quietly. A session handover
prompt written on 2026-09-24 lived in a chat log and was never committed. And on 2026-10-02 a
registered study stopped for about 22 hours when its model server dropped a connection,
because nothing watched it. Sub-doctrine 10.h already says the work outlives the machine;
nothing said the project outlives the people and sessions that carry it.

The operator asked (#1384) for "a handful of actually useful prompts to keep this project in
existence for all of eternity", "fully comprehensive and fully up to date always", run weekly,
and then that GitHub's workflows run them "automatically forever, like for real". Two facts
bound how. First, GitHub disables a public repository's scheduled workflows after 60 days
without activity, so "forever" has to be engineered, not assumed. Second, the operator chose
GitHub-hosted runners with open weights on CPU, over the self-hosted GPU runner and over a
paid fallback. The record measured gpt-oss:20b there at 2.8 tokens per second generating and
44.5 reading, so an agent cannot explore a large repository within one job's six hours.

## Decision

1. **Seven prompts, each self-contained,** in `docs/continuation/`: Resume, Keep develop green,
   Release, Triage, Research and measurement, Succession, and Rebuild. Each tells any capable
   agent, with no memory, what to read, what to run, what never to do, and how to know it is
   done. They are declared in `scripts/continuation_prompts.toml`, which is also where every
   setting below lives (12.h).
2. **Kept current by a check, not by care.** `scripts/continuation_prompts.py check` runs in CI
   on every pull request (`tests/meta/test_continuation_prompts.py`). It fails when:
   - a prompt names a file, glob, ADR or `vibey-gh` command that does not exist;
   - any workflow lane or agent skill is covered by no prompt and has no written exemption;
   - a page's generated state block is stale;
   - the lane that runs the prompts is missing, unscheduled, not dispatchable, or moved off
     GitHub-hosted runners.

   So a new lane or a renamed file cannot land without its prompt being updated.
3. **Run on GitHub every week** by `.github/workflows/continuation-prompts.yml`, on
   GitHub-hosted runners only:
   - **keepalive** re-enables every scheduled workflow through the API, which defeats the
     60-day disable, and warns about any lane whose newest scheduled run is more than 15 days
     old (12.e: a missed run is said out loud);
   - **refresh** re-renders the pages and runs the check, and opens a pull request when
     anything moved;
   - **run** executes each prompt with gptossloop and an open-weights model on the runner's
     CPU. Its input is bounded: deterministic commands, declared per prompt, gather the
     evidence first, cut loudly at a declared size (ADR-0075), and the run is limited by turns
     and by time;
   - **report** acts on the result.
4. **Authority is bounded by construction (12.d).** Each prompt declares a mode:
   - `drill` changes nothing and reports, as one tracking issue per prompt, every instruction
     that no longer holds. Release, Succession and Rebuild are drill-only by declaration,
     because acting them out is irreversible or needs a person.
   - `act` may produce one patch, which becomes a **draft** pull request.

   The agent's job holds no write permission and no secret, because it reads untrusted text
   and has root on its VM. A fresh runner, where no agent ran, applies the patch to a clean
   checkout. It refuses the whole patch if it touches a workflow, the canon or the declared
   state, and opens the draft pull request. Nothing in the lane can merge, approve, release,
   delete, or touch a ruleset or a secret.

## Consequences

- **The prompts drift only as long as a pull request takes.** Any change that breaks one
  fails CI. Coverage is mechanical, so "fully comprehensive" means every lane and every skill
  has a prompt that names it.
- **The CPU budget is narrow.** At about three tokens per second an act run can make a small,
  focused change and no more, and a drill can verify a page of instructions. The weekly run
  is a heartbeat and a smoke test of the prompts, not a replacement for a capable agent
  following them. A future operator may move the run to faster hardware by changing
  `[run] runs_on` and `[run] model`, and the check still forbids self-hosted runners for this
  lane.
- **Re-enabling relies on GitHub's own behaviour.** That a re-enable counts as activity is
  GitHub's behaviour, not ours, and it is not proved here. The keepalive's overdue warning is
  the evidence that it worked, and the lane's own weekly pushes also count as activity.
- **Drill reports are model output.** They are filed verbatim and marked unverified; a person
  checks each line.
- **The prompts outlive the forge.** The pages ship in the documentation site and the book,
  and the Rebuild prompt covers the day the forge, the runner or the operator is gone.
