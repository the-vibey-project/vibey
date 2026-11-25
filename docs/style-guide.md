---
description: How vibey's documentation is written. Bottom line first, taught the Feynman way through a running conversation between Professor Feynman and his student Daniel, and checked against the code.
---

# How we write vibey's documentation

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Every page answers "what is this and what do I do?" in its
> first screen, teaches the idea through a short conversation between **Professor Feynman** and
> his student **Daniel**, gives commands you can copy with the output you should see, and states
> nothing the code does not do. If a page and the code disagree, the page is wrong.

This page is the contract for anyone, person or model, who writes or edits a page here.

## The four promises

1. **Bottom line first.** A reader who stops after the first screen still leaves with the answer.
2. **Taught, not listed.** We explain an idea the way Feynman did: in plain words, with one
   everyday picture, to someone new, and then we check the explanation by having the student
   say it back.
3. **Works when pasted.** Every command is complete, runs as written, and is followed by what
   you should see.
4. **True today.** Every fact comes from the code, the tests or a decision record, and a page
   says so when something is not built yet.

## The kinds of page

| Kind | Examples | BLUF | Feynman and Daniel | Notes |
|---|---|---|---|---|
| Front door | `README.md`, `docs/index.md` | Yes, with the install command and the "drive it with another LLM" steps | One short scene | The two standard blocks below appear here in full |
| Guide | `docs/guides/*` | Yes | Yes, the lesson carries the page | Ends with Daniel's teach-back |
| Concept | `docs/plans/*`, case studies | Yes | Yes, opening lesson, then the precise text | The precise text stays precise |
| Reference | `docs/reference/*`, package READMEs | Yes | A short "how to read this page" exchange only | Lookup first: tables, every flag, every default |
| Record | decision records, the canon, the changelog, the paper | No change | No | History and law are not rewritten for style |
| Agent file | `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | No | No | Facts only; generated sections stay generated |

## The shape of a page

In this order. Leave out a section only when it would be empty.

1. **Front matter** with a one-sentence `description:`. Quote it if it contains a colon.
2. **The title.** Say what the reader will be able to do.
3. **The BLUF block**, a `> [!IMPORTANT]` callout that opens `**Bottom Line Up Front (BLUF):**`.
   At most five lines: what this is, who it is for, the one thing to do, how long it takes,
   and what you will have afterwards.
4. **The lesson.** Professor Feynman and Daniel (see below).
5. **Do it.** Numbered steps. One action per step. Each command in its own fenced block with
   the language set, followed by "You should see:" and the real output.
6. **Daniel's teach-back.** Three to five sentences in Daniel's words that restate the idea,
   and one line from the Professor that confirms it or fixes the one thing Daniel got wrong.
7. **The details.** Tables, flags, defaults, limits, links to the decision record.
8. **When it goes wrong.** The message you see, what it means, the command that fixes it.
9. **Where next.** Two or three links, each saying why you would follow it.
10. **Say it in one line.** A single sentence under 240 characters that a reader could post to
    tell someone else what they learned. No hashtags, no hype.

## The bottom line, properly

- Lead with the answer, not the history.
- Name the command. If there is one command, show it.
- Give a number where you can: minutes, versions, counts.
- Say what is not done. "Not built yet" is a complete and useful sentence.

## Professor Feynman and Daniel

The lesson is a short story with two people in it.

- **Professor Feynman** teaches. He is curious, warm and exact. He distrusts jargon, reaches for
  an everyday picture (a kitchen, a post office, a ledger in a shop), and says "I don't know"
  when that is the truth. He never explains with a word he has not first explained.
- **Daniel** is his student: bright, new to this, and unafraid to say "I don't follow." He asks
  the question the reader is too polite to ask. At the end he explains the idea back.

How the lesson is written:

- **A narrator sets the scene in one or two sentences**, in the plain, companionable voice of an
  old-fashioned storyteller: a place, a small detail, a reason for the conversation. Then the
  two of them talk. The narrator may step in between exchanges to move the scene along.
- **Speech is marked by name in bold**: `**Daniel:**` and `**Professor Feynman:**`.
- **One idea per lesson.** If the page has three ideas it has three short scenes.
- **The Feynman method, in order:** name the idea; explain it to a beginner with one picture;
  find the gap (Daniel's question exposes it); go back to the source and close it; have Daniel
  say it again more simply.
- **The picture must be true.** An analogy that misleads is cut. Say where the picture stops
  working.
- **Length:** 150 to 400 words for a guide's lesson, under 120 for a reference page.
- **Keep it kind.** Daniel is never the butt of a joke. A wrong answer is the most useful
  moment in the lesson.
- **No real quotations.** These conversations are written for this documentation. They are not
  things the historical Richard Feynman said, and no page presents them as such. The site says
  so once, on its front page.

A small example:

> The kettle had just clicked off when Daniel put the question he had been carrying all morning.
>
> **Daniel:** Professor, why does vibey keep a ledger? The work is in the files.
>
> **Professor Feynman:** Suppose you run a shop and keep the day's sales on a slate. Somebody
> wipes one line. Can you tell?
>
> **Daniel:** No.
>
> **Professor Feynman:** Now write each sale in a bound book, in ink, and on each line also write
> a number worked out from the line above. Change one line and every number after it is wrong.
> That is the ledger: you may add a line, and you may never change one.
>
> **Daniel:** So if an agent crashes, the book still says what it had finished.
>
> **Professor Feynman:** That is the whole trick. The picture stops working in one place: the shop
> book is one copy, and ours is checked by the database itself.

## Written to be read on a phone

People meet these pages in a feed, on a small screen, between other things.

- The first sentence is the hook. It states a real problem or a real result.
- Paragraphs are one to three sentences.
- One idea per paragraph, one action per step.
- Headings are things a person would search for.
- Tables for comparison, lists for steps, prose for reasons.
- A claim about what vibey can do links to what proves it: a test, a file, a decision record.
- A goal is labelled as a goal. We do not describe what we hope to build as if it were built.

## Written for the person at the keyboard

- Show the shortest path to a first success, and say how long it takes.
- Commands are complete and safe to paste. No `<placeholders>` without saying what goes there.
- After a command, show what success looks like.
- Name the file a setting lives in and the exact key.
- Every error a reader is likely to meet has its message, its cause and its fix.
- Say which operating systems and versions a page was checked on.

## The two standard blocks

These two blocks are the same words wherever they appear. Copy them; do not rephrase them. If
the code changes, change them here first and then everywhere.

### Install vibey with one command

<!-- standard-block:install:start -->
> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** One command installs vibey and gets a new macOS or Linux
> machine ready to run a first project on your own hardware. About 15 minutes, plus the model
> download of roughly 12 GB.
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --full
> ```
>
> It installs `uv` and Python if you lack them, then vibey with its hub, PostgreSQL, a local
> database, Ollama, the default model, and the connection to your editors, and ends by running
> `vibey doctor`. Each step is announced first and can be skipped (`VIBEY_FULL_POSTGRES=0`,
> `VIBEY_FULL_DATABASE=0`, `VIBEY_FULL_OLLAMA=0`, `VIBEY_FULL_MODEL=0`, `VIBEY_FULL_CONNECT=0`).
> On Linux it asks for your sudo password, and on macOS it needs Homebrew. Run it again to repair
> an install.
>
> **Afterwards, two things are yours:** add the `export VIBEY_PG_URL=...` line it prints to your
> shell profile, and require `scram-sha-256` in `pg_hba.conf` (`vibey doctor` says so until you do).
> Without `--full`, the same command installs only vibey, and `vibey doctor` lists what is missing.
<!-- standard-block:install:end -->

### Let another LLM drive vibey

<!-- standard-block:llm-driver:start -->
> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Four steps let Claude Code run your vibey projects: start the
> hub, say where projects live, connect Claude Code, and ask it. About 5 minutes after the install.
>
> 1. **Start the hub** in a terminal where `VIBEY_PG_URL` is exported (the installer printed the
>    line): `vibey hub start`
> 2. **Say where projects live.** Add this to your own `vibey.toml` (macOS:
>    `~/Library/Application Support/vibey/vibey.toml`, Linux: `~/.config/vibey/vibey.toml`):
>    `[hub]` then `projects_root = "~/vibey-projects"`. Without it, starting a project from the
>    LLM is refused.
> 3. **Connect Claude Code** from the folder you will work in:
>    `vibey connect --client claude_code --yes`. It writes `./.mcp.json` there and saves the old
>    file as `.vibey.bak`. Leave out `--client` and it writes the config for every client it knows.
> 4. **Ask.** Run `claude` in that folder, approve the `vibey` server, and type: *Use the vibey
>    tools: list my vibey projects and any open gates, then tell me what each one is waiting on.*
>
> Claude Code gets 16 tools: start a project, start work, pause work, abandon a project, list
> projects, status, gates, answer a gate, queue, ledger, budget, lanes, loops, doctor, and search
> and fetch the web through the hub. The hub refuses it the gates that spend
> money, and its instructions say to abandon a project only after you confirm. One known gap: over
> MCP it can answer the deployment opt-in gate, which asks "deploy or stay local"; only ACP refuses
> that ([`SECURITY.md`](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md)). Codex, Cursor, VS Code,
> Claude Desktop, Gemini CLI and any ACP client such as Zed work the same way through
> `vibey connect --client <name>` or `vibey acp`.
<!-- standard-block:llm-driver:end -->

## Before you open the pull request

- Run the commands on the page.
- `uv run pytest tests/meta -q -o addopts="" -p no:cacheprovider` passes.
- `uv run vibey-gh corpus-index --check` passes.
- The page is in `properdocs.yml` if it is new.
- A change to a skill or a procedure is made in the Claude, Cursor, Codex and Antigravity trees
  in the same pull request.

## Say it in one line

vibey's docs put the answer first, teach it as a conversation, and never say more than the code does.
