---
description: The proposed microslice contract for anything loaded into a model's context, the converter that slices Markdown, the generated tree under docs/microslices, and the context engine that compiles bounded packets.
---

# Load only what a task needs: context microslices

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** A model's context window is finite, so vibey's rule (proposed
> sub-doctrine 10.k, [ADR-0075](architecture/decisions/0075-context-microslices-and-linked-surfaces.md))
> is to load small, linked, identified slices instead of whole documents, and never to cut
> anything silently. Two tools exist today: `slice_markdown.py` splits Markdown into linked slices
> (the generated tree is `docs/microslices/`), and `vibey-skills packet` compiles a bounded context
> packet that lists what it left out. The generated tree has drifted; regenerate it as shown below.

## The lesson

Daniel had pasted a whole skill file into a prompt, and the model had answered about the wrong
half of it.

**Daniel:** Professor, I gave it everything. Why did it miss the part that mattered?

**Professor Feynman:** Think of a library. You ask the librarian how to change a tyre, and she
wheels in the whole shelf on cars. The answer is in there, somewhere. A good librarian hands you
the one page on tyres, tells you which page you must read first, the safety page about the jack,
and says where the next page is if you need it.

**Daniel:** So a slice is one page.

**Professor Feynman:** One page that does one job, with a name that never changes, a note of
where it came from, a limit on its size, and two kinds of link: the pages you must read with it,
and the pages you may read next. You start at the page that matches the task, add the ones it
requires, count how much you are carrying, and follow the optional links only when you need to.

**Daniel:** And if the pages it requires do not fit?

**Professor Feynman:** That is the rule that matters most. You do not quietly tear out the safety
page to make room. You split the work, or you stop and say it does not fit. Never a silent cut.

**Daniel:** Does vibey actually do all that?

**Professor Feynman:** Partly, and that is where my librarian is kinder than the tools. The
converter splits a document at its headings and links each piece to the one before and after;
it does not know which piece is the safety page, and it records no size. The skills context
engine does the counting: it builds a packet up to a budget and writes down every piece it left
out and why.

## Do it

Checked on 2026-11-24 in this repository at develop `d91a3791e`, on macOS.

1. Slice one Markdown file into a scratch folder.

   ```bash
   python3 src/vibey_tools/skills/tools/slice_markdown.py docs/style-guide.md ./scratch/ms --level 2
   ```

   You should see `wrote 10 microslices`. The folder holds `001-the-four-promises.md` through
   `010-say-it-in-one-line.md` and an `index.json`.

2. Build the skills context index and search it.

   ```bash
   vibey-skills index build --output ./scratch/vsidx
   ```

   You should see a JSON summary. On the day this page was checked it reported
   `"skill_count": 826`, `"chunk_count": 10482` and `"skills_release": "0.4.0"`.

   ```bash
   vibey-skills search "ledger append-only" --index ./scratch/vsidx --limit 3
   ```

   You should see three ranked lines, each a score, a `plugin/skill` name and the heading path of
   the section. The top hit was `vibey/vibey-chat-driver`.

3. Compile a bounded packet. Write a request file first:

   ```bash
   printf '{"schema_version": 1, "title": "Publish a ledger shard", "objective": "Export a project ledger as a public shard"}\n' > ./scratch/req.json
   vibey-skills packet --request ./scratch/req.json --index ./scratch/vsidx --budget 2000 --output ./scratch/packet.md --manifest ./scratch/packet.json
   ```

   It prints nothing. `./scratch/packet.md` is the packet; `./scratch/packet.json` is its manifest. On the
   day this page was checked, the manifest said `"status": "ok"`, a token estimate of 1,982 against
   the budget of 2,000, 8 chunks included and 52 omitted, each omitted chunk with
   `"reason": "budget"` and its own token estimate.

## Daniel's teach-back

**Daniel:** A slice is a small piece of a document with a fixed id, one purpose, its source, a
size limit, the slices it requires and the ones it links to. You load the matching slice and what
it requires, measure the total, and split or stop rather than cut. The converter makes slices at
headings and chains them in order, and the context engine fills a packet to a budget and lists
everything it left out.

**Professor Feynman:** Right. And remember the honest limit: the converter's links are just
"previous" and "next". Deciding which slice is truly required is still a person's review.

## The contract

This is the implementation contract for proposed sub-doctrine 10.k and ADR-0075, both still
awaiting ratification by the operator's merge. It applies to every skill, agent guide, ADR, bot
script, prompt, ledger and specification that may be loaded into a finite context window.

- **Each slice** answers one question or performs one operation and carries a stable identity, one
  purpose, provenance, bounded size, and explicit `requires` and `links` relationships.
- **Retrieval** starts at the matching slice, follows required safety and acceptance slices,
  records the selected ids and measured size, and follows optional links only when needed.
- **A budget is a gate.** If the closure exceeds its budget, split or park; never silently truncate
  requirements, safety constraints, evidence or uncertainty.
- **Migration is incremental.** Existing large surfaces remain authoritative until replacement
  slices link back to them. New and materially changed content adopts the contract at once.
- **Summaries are routing aids**, not source evidence.

The vibey documentation applies the same idea to its own pages; see
[the documentation style guide](style-guide.md).

## The converter, `slice_markdown.py`

The offline converter, `src/vibey_tools/skills/tools/slice_markdown.py`, reads a Markdown file and
leaves it unchanged. It splits at the headings of one level (`--level 1`, `2` or `3`; default 2),
ignoring headings inside fenced code, and writes:

- one numbered file per section (`001-<slug>.md`, ...), each opening with front matter: `id`
  (the source's name, the heading's slug and a 10-character hash, so the same heading always gets
  the same id), `purpose` (the heading), `source`, `requires` (the previous slice) and `links` (the
  next slice);
- an `index.json` beside them listing every slice.

It does **not** record a slice's size, and its `requires` and `links` are positional, not
semantic. The generated boundaries need review: mechanical splitting is not itself a quality
claim.

For the authoritative skills tree, the batch form slices every `*/skills/*/SKILL.md` and writes a
top-level `manifest.json` with each skill's source, output and slice count:

```bash
python3 src/vibey_tools/skills/tools/slice_markdown.py \
  --all-root src/vibey_tools/skills/plugins \
  --all-output docs/microslices/skills --level 2
```

It prints `wrote N skill manifests` (826 on 2026-11-24).

### The generated tree has drifted

`docs/microslices/` is generated, not in the site's navigation, and published as pages reachable
by URL or search; this page is the way in. The converter **never deletes**: a rerun overwrites the
files it writes and leaves every other file where it is. So a removed plugin, or a skill that lost
a section, leaves stale slices behind. A fresh build compared with the committed tree on
2026-11-24 found three plugin folders that no longer exist in `src/vibey_tools/skills/plugins`
(`actual-food-production-farm-to-food-research`,
`agricultural-machinery-robotics-technology-research`, `social-cultural-agriculture-farming`) and
two orphan slices under `content-engineering-pipeline/skills/pipeline-book-production/` (`005` and
`006`). No test or workflow checks this tree for drift.

To regenerate exactly, remove the output first, then run the batch form from the repository root
with relative paths (an absolute output path is written into every `index.json`):

```bash
rm -rf docs/microslices/skills
python3 src/vibey_tools/skills/tools/slice_markdown.py \
  --all-root src/vibey_tools/skills/plugins \
  --all-output docs/microslices/skills --level 2
```

## The context engine, `vibey-skills`

The context engine is the preferred implementation for bounded retrieval
(`src/vibey_tools/skills/src/vibey_skills/context_engine.py`). It does not read
`docs/microslices/`: it indexes the sections of every packaged `SKILL.md` directly, offline and
deterministically, in a SQLite full-text index.

| Command | What it does | Defaults |
|---|---|---|
| `vibey-skills index build [--output DIR]` | Build the index and print its summary. | `.vibey-skills/index` |
| `vibey-skills index inspect DIR` | Print an index's summary. | |
| `vibey-skills search QUERY [--index DIR] [--limit N] [--json]` | Rank indexed skill sections. | `--limit 20` |
| `vibey-skills packet --request FILE --output FILE --manifest FILE [--index DIR] [--budget N]` | Compile a packet within a token budget and write its manifest. | budget from the request's `maximum_context_tokens`, else 6,000; allowed 1,000 to 32,000 |
| `vibey-skills evaluate --cases FILE [--index DIR] [--top-k N]` | Score retrieval against a gold case set. | `--top-k 10` |

A packet request is a JSON object with `schema_version: 1` and optional fields such as `title`,
`objective`, `requirements`, `acceptance_criteria`, `phase`, `languages`, `paths`,
`required_skills` and `excluded_skills`; an unknown field is refused. The manifest records every
included chunk and every omitted chunk with its reason, so nothing is cut without a record.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `--all-root and --all-output must be provided together` | Only one batch flag was given. | Pass both. |
| `source and destination are required unless --all-root is used` | Single-file mode needs both paths. | Give the source file and an output folder. |
| Slices for a plugin that no longer exists | The converter never deletes. | Remove the output folder and regenerate. |
| `budget must be between 1000 and 32000` | The packet budget is out of range. | Pick a `--budget` in that range. |
| `unknown request field(s): [...]` | The request file has a field the engine does not know. | Remove it; see the list above. |
| `no authoritative SKILL.md files under ...` | The index was pointed at a folder with no skills. | Build from the packaged plugins (the default). |

## Where next

- [ADR-0075](architecture/decisions/0075-context-microslices-and-linked-surfaces.md), for the
  decision and its open questions.
- [The documentation style guide](style-guide.md), for how vibey's own pages are kept small and
  linked.
- [The vibey-skills README](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/skills/README.md),
  for installing and browsing the skills the engine indexes.

## Say it in one line

vibey loads small, linked context slices instead of whole documents and never cuts silently; the
converter slices Markdown, and vibey-skills packet fills a budget and lists what it left out.
