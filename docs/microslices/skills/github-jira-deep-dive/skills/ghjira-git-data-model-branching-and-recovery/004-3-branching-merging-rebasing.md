---
id: skill-3-branching-merging-rebasing-52167c7990
purpose: 3 branching merging rebasing
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-git-data-model-branching-and-recovery/SKILL.md
requires: ["skill-2-git-s-data-model-5cf78d0cba"]
links: ["skill-4-recovery-e110cedfcd"]
---

## §3. Branching, Merging, Rebasing

```
MERGE    ⚠️ creates a commit with two parents. History is truthful and messy
REBASE   ⚠️ REPLAYS commits onto a new base, creating NEW commits with new
         hashes. History is linear and edited
SQUASH   collapse a branch into one commit
FAST-FORWARD  ⚠️ no merge commit needed because the branch is strictly ahead
CHERRY-PICK   ⚠️ copy one commit elsewhere — creates a duplicate, and is a
         common source of "why does this appear twice"
```
> **⚠️ GOTCHA — the golden rule of rebasing: never rebase commits that others have
> pulled.** ⚠️ **Rebase rewrites hashes, so anyone who has the old commits now has
> divergent history**, **and the usual recovery is messy.** **⚠️ Rebase freely on your own
> unpushed work; use merge on shared branches.**
> **⚠️ And if you must force-push a shared branch, use `--force-with-lease` rather than
> `--force`** — **it refuses if someone else has pushed since your last fetch.**

**⚠️ Branching strategies, honestly:**
```
⚠️ TRUNK-BASED  short-lived branches, merge to main daily, feature flags for
   incomplete work. ⚠️ The approach the DORA research associates with high
   performance, and the one most compatible with CI
GITHUB FLOW     ⚠️ branch → PR → merge → deploy. Simple; suits continuous deploy
GIT FLOW        ⚠️ develop/release/hotfix branches. Designed for versioned
   releases with support windows; ⚠️ widely cargo-culted onto web apps
   where it adds ceremony without benefit — its own author has said as much
```
**⚠️ Long-lived branches are the underlying problem in all merge-hell stories** —
⚠️ **integration pain grows superlinearly with branch age**, **so the fix is smaller,
shorter branches rather than better merge tooling.**

---
