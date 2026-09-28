---
id: skill-2-git-s-data-model-5cf78d0cba
purpose: 2 git s data model
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-git-data-model-branching-and-recovery/SKILL.md
requires: ["skill-1-the-tool-is-not-the-process-4da4e2e372"]
links: ["skill-3-branching-merging-rebasing-52167c7990"]
---

## §2. ⚠️ Git's Data Model

**⚠️ Learn this and the commands stop being magic. Git is a content-addressed object store
plus refs.**
```
⚠️ FOUR OBJECT TYPES, all keyed by hash of their content
  BLOB    file contents (no name, no metadata — just bytes)
  TREE    a directory: names → blobs and other trees
  COMMIT  a snapshot: one tree + parent commit(s) + author + message
  TAG     annotated tag object

⚠️ COMMITS ARE SNAPSHOTS, NOT DIFFS. Git computes diffs on demand.
   ⚠️ This is the single most clarifying fact about Git

⚠️ REFS are just files containing a hash
  branch  = a movable ref to a commit
  HEAD    = a ref to the current branch (or a commit, when "detached")
  tag     = a ref that doesn't move
```
> **⚠️ GOTCHA — a branch is not a container of commits.** ⚠️ **It's a 41-byte file with a
> hash in it.** **"Deleting a branch" deletes a pointer, not the commits** (§4).
> **⚠️ This is why branching is cheap, why "which branch is this commit on" is a
> surprisingly awkward question, and why rewriting history creates NEW commits rather
> than editing old ones — objects are immutable and keyed by their content.**

**⚠️ The three areas**: **working tree → INDEX (staging area) → repository.** ⚠️ **The
index is the concept people skip and then don't understand `git add`, partial staging, or
why `git status` shows two sections.**
**⚠️ Remotes and remote-tracking branches**: ⚠️ **`origin/main` is YOUR last-known copy of
the remote's `main`, not the remote itself.** **`fetch` updates it; `pull` = fetch +
merge (or rebase).**

---
