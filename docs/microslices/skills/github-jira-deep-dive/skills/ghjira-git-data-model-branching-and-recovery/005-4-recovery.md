---
id: skill-4-recovery-e110cedfcd
purpose: 4 recovery
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-git-data-model-branching-and-recovery/SKILL.md
requires: ["skill-3-branching-merging-rebasing-52167c7990"]
links: []
---

## §4. ⚠️ Recovery

> **⚠️ The reassuring fact: in Git, committed work is very hard to actually lose.**
> ⚠️ **`git reflog` records where HEAD has been, including states no branch points at.**
> **Almost every "I destroyed everything" situation is recoverable from it.**

```
⚠️ git reflog                     find the hash you were at
⚠️ git reset --hard <hash>        go back there (⚠️ discards uncommitted work)
⚠️ git checkout -b rescue <hash>  safer: make a branch at the lost commit
git cherry-pick <hash>            retrieve one commit
⚠️ git revert <hash>              UNDO a commit by making a new one —
   ⚠️ the correct tool on shared branches, unlike reset
git fsck --lost-found             for dangling objects
⚠️ git stash / git stash list     uncommitted work you set aside
```
**⚠️ What genuinely IS lost**: ⚠️ **uncommitted changes destroyed by `reset --hard` or a
bad `checkout`, untracked files removed by `git clean`, and objects pruned by `gc` after
the reflog expires (default ~90 days for reachable, ~30 for unreachable).**
**⚠️ The practical habit**: ⚠️ **commit early and often on your own branch — it costs
nothing and puts everything in the reflog's reach.** **You can always tidy the history
later** (§3).

---

# PART II — GITHUB
