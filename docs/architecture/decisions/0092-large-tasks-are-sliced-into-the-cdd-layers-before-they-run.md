# 0092 — Large tasks are sliced into the CDD layers before any of them runs, and every lane is given everything its runner can take

**Status:** proposed · **Date:** 2026-10-23 · **Cites:** ADR-0039, ADR-0017, ADR-0018; sub-doctrines 9.c, 10.f, 12.c · **Related:** ADR-0027, ADR-0064, ADR-0075 · **Issue:** #1666

**Owes:** two conduct rules, neither ratified here. (1) A large task is sliced before it is run.
(2) A lane is never launched narrower than its runner allows, and what it lacks is reported. Each is
sub-doctrine material under ADR-0020; the rule is ratified only by the human merge that carries it.

## Context

ADR-0039 measures delivery at four nested scopes: the project vision, the phase or milestone, the
feature set or epic, and the feature, unit or user story. `build.decompose` did not use them. It
turned an accepted spec into one flat list of work items with a dependency graph, so a plan of
sixty items was sixty peers. Nothing said which belonged to which epic or phase, and nothing made a
group finish before the next began: a group ran in whatever order the graph happened to allow.

The same issue asked for something else: every lane always has full access to skills, plugins,
MCP servers, and web search and research tools. Reading the runners showed the lanes did not.
claudeloop's `run --web-search` is off unless given, and the BUILD path (`LoopProcessAdapter`) did
not give it. claudeloop takes skills, plugins and connectors only by name, and vibey names none.
The local runner (`gptossloop`, `qwenloop`) offers its model a fixed tool set with web search but
no MCP, and `claudeloop-local` shares claudeloop's binary yet its backend refuses web search.

## Decision

### Slicing

The work item is the story. Everything above it is a grouping the slicer lays over the existing
graph (`domain/slicing.py`), so validation, the queue and idempotency are unchanged.

- **As many layers as the size needs.** A plan of at most `max_children` items (8) is stories only.
  Larger plans are grouped into epics; more than `max_children` epics into phases; more than
  `max_children` phases into projects. Never more than the four, so every plan sits on at least one.
- **Groups are consecutive runs of a plan already in dependency order**, split as evenly as they
  can be (9 under a cap of 8 is 5 and 4). A group therefore never depends on a later one, and what
  results is acyclic by construction.
- **A group runs to completion before the next.** Each group's entry stories also wait for the
  terminal stories of the group before it, at every layer. Only the boundary is wired; the graph
  supplies the rest transitively.
- **Sliced whole, then run.** The handler judges the slicing like the rest of the plan, then
  enqueues it in the one transaction it already used. No item starts until all of it is sliced.
- **Where an item sits is recorded** in its job payload as `slice_path`, outermost slice first.

### Lanes

- `EngineAffordances` gains `skills` and `web_search`, each with the evidence for it, and
  `full_access_gaps()` names what a lane is not shown to have. Unknown is a gap, not a grant.
- `EngineDescriptor.launch_flags` are the flags every new `run` is given. claudeloop's is
  `--web-search`; `claudeloop-local` lists none, because its backend refuses it.
- The gaps are pinned in a test, so one closes only because a runner's code was read and none
  widens unseen. No flag vibey passes may narrow tools, MCP, plugins or settings.

## Consequences

- A plan's size now decides its depth, and a producer need not choose layers.
- Barriers serialise groups: a phase's stories cannot overlap the previous phase's last ones. That
  is the point, and it costs parallelism across a boundary. Within a group the graph still decides.
- Grouping by position is structural, not semantic. It orders correctly but does not name an epic
  for what it is about. A producer-supplied grouping is the natural next step.
- Every BUILD lane on claudeloop now has web search. `claudeloop-local` keeps running.

## Added after the first draft

- **`[build.slicing] max_children`** is a key, read from the project's stored config.
- **Planner-named epics.** A work item may carry `epic`; consecutive items under one name form one
  named epic (split and numbered if over the cap), and both decomposers ask the model for it.
- **Skills, plugins and MCP for claudeloop** are not narrowed. The SDK documents `skills=None` as
  "not skills off" and `setting_sources=None` as loading every user, project and local setting, and
  claudeloop sets neither; a claudeloop test pins that.
- **`--deep-research`** is passed beside `--web-search`. claudeloop only records it as a flag; no
  tool or cost follows from it.
- **codexloop MCP** is shown: its argv suppresses nothing of Codex's own configuration and its
  doctor checks the servers that configuration declares.

## Not done, and why

- **codexloop skills and web search** are unknown: the `codex` binary is not installed here to
  probe, and nothing in the runner's code shows either. They stay gaps, pinned.
