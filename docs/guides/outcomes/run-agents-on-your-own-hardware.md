---
description: Run vibey's default engine, gptossloop, on the Heretic v2 build of GPT-OSS 20B in Ollama and allow no other; the queue, ledger and model stay on your machine, and web search and page reads can be shut off too.
---

# How do I run AI coding agents entirely on my own hardware?

**Short answer:** run vibey's default engine, `gptossloop`, on the Heretic v2 build of GPT-OSS
20B in Ollama and allow no other; the queue, ledger and model stay on your machine, and web
search and page reads can be shut off too.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone whose code must not reach a vendor's model.
> Pull the default model (12.1 GB) into Ollama and start the worker with
> `--provider gptossloop --engines gptossloop`. Most of the time is the download. Afterwards
> no model but yours can be used, and with three settings nothing reaches another computer.

## The lesson: a workshop with one window

The lamp in the workshop was on, though it was barely four o'clock.

**Daniel:** If the model runs on my machine, nothing leaves it. Right?

**Professor Feynman:** Picture a workshop. The craftsman lives in it, the order book is on the
bench, and the street door is locked. That is the default: the model in Ollama, the queue and
ledger in your PostgreSQL, and no paid engine let in.

**Daniel:** Then I'm done.

**Professor Feynman:** Not quite. There is a window. While planning a design, vibey may look
things up on the web, and a builder may read a public page, because a local model knows only
what it was trained on.

**Daniel:** So I board up the window?

**Professor Feynman:** Three boards, and then you hand the craftsman the books he would have
looked up: a folder of notes. The picture stops working in one place: a real window shows who
looks through it. vibey's is quieter, so check it with `vibey searxng status` and the
`web search:` line the worker prints when it starts.

## Check the machine first

The figures were measured on the stock build, which has the default's architecture and
footprint ([ADR-0099](../../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md));
the [system requirements](../../reference/system-requirements.md#hardware) mark several stale
since 2026-09-30.

- **Apple Silicon:** 24 GB minimum, 32 GB recommended. A 16 GB Mac cannot run it (derived).
- **A discrete GPU:** 12,339 to 12,974 MiB; a 16 GB card is recommended, not verified on CUDA.
- **CPU only:** enough to design, not to build: a worst-case BUILD turn outlasts the
  900-second request timeout.
- **Disk:** about 20 GB free; the download is 12.1 GB (stock: 14 GB).

## Steps

**1. Install vibey and PostgreSQL**, with two database roles
([database roles](../../reference/configuration.md#database-roles); [install](../install.md)).

```bash
vibey install --postgres        # Homebrew, apt or dnf
createdb vibey                  # as the account that owns the database ("owner" below)
# vibey migrate creates vibey_app, the role everything else connects as
VIBEY_PG_MIGRATE_URL=postgresql://owner@localhost:5432/vibey \
VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey vibey migrate
export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey
```

**2. Install Ollama and pull the default model.**

```bash
ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
export VIBEY_OLLAMA_URL=http://127.0.0.1:11434   # DESIGN and BUILD then use one model
vibey doctor --sovereign-fit                      # does the model fit this machine?
```

Then `vibey doctor --engine gptossloop` should no longer say the model "is not served". For
OpenAI's unmodified build, pull `gpt-oss:20b` and set `VIBEY_SOVEREIGN_MODEL=stock`
([the two builds](../local-models-ollama.md));
`VIBEY_OLLAMA_MODEL` names any tag, and `vibey models` lists other families.

**3. Create a project and record conformance.** No engine is selected until it has passed.

```bash
vibey new my-app --repo ~/src/my-app
vibey doctor --engine gptossloop --conformance --record
```

**4. Start a worker that can use only the local engine.**

```bash
vibey worker --provider gptossloop --engines gptossloop
```

`--provider` keeps design and planning local; `--engines` is an allow-list, so no paid engine
can build ([`vibey worker`](../../reference/cli.md#vibey-worker)). Answer what it parks with
`vibey gates` and `vibey answer`. `vibey cost` should show zero spend.

## What leaves the machine, and how to stop it

Always local: PostgreSQL on 5432, Ollama on 11434, and the hub on 8765 for krypton apps. No
telemetry or update check is made. Since
[ADR-0102](../../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md),
three things can reach out:

- **DESIGN research.** For each of `prior-art`, `libraries` and `api-docs` without a file of
  yours, a short query built from the project's objective (file paths and backticks removed)
  goes to a local SearXNG on `127.0.0.1:28180`, which asks public search engines; vibey then
  reads up to three result pages. If SearXNG fails and a Brave key is set, the query goes to
  Brave, said once on standard error.
- **BUILD sessions.** gptossloop's `web_search` uses that SearXNG only; its `web_fetch` reads
  any public page, SearXNG or not.
- **The hub's tools**, for an LLM driving vibey over MCP, recorded as `WebSearched` and
  `WebFetched` without query or URL. Research and session reads write no such record.

The three boards:

```bash
vibey searxng uninstall    # if you installed one; under an editor, set [acp] searxng = "never"
unset VIBEY_BRAVE_API_KEY WEBSEARCH_BRAVE_API_KEY BRAVE_SEARCH_API_KEY
# In your own vibey.toml (~/Library/Application Support/vibey/ on macOS,
# ~/.config/vibey/ on Linux), refuse every page read:
#   [web]
#   allow_hosts = []
```

Then give DESIGN its reading: `prior-art.md`, `libraries.md` and `api-docs.md` in the folder
`VIBEY_EVIDENCE_DIR` names, each starting with a `source:` line; a topic with its file is not
searched. Or start the worker with `--auto-record-research-gaps`, and the spec lists what went
unresearched ([`[design.research]`](../../reference/configuration.md#designresearch)).

## Daniel's teach-back

**Daniel:** The model, queue and record live on my machine, and `--engines gptossloop` keeps
paid engines out. The default model is Heretic v2, not stock `gpt-oss:20b`. Web research is the
one window: no SearXNG, no Brave key and an empty `allow_hosts` board it, and notes replace it.

**Professor Feynman:** Yes. One correction: a builder's page reads need no SearXNG, which is
why `allow_hosts` is one of the boards.

## The evidence

| Claim | Where it is proved |
|---|---|
| The default engine is local and on | [ADR-0064](../../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md) |
| The default model is Heretic v2 | [`sovereign_model.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/sovereign_model.py) |
| Local first; `--engines` confines | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md); [`rotation.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/rotation.py) |
| Research searches, then quotes pages | [`gptossloop_design.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/engines/gptossloop_design.py); [`research.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/web/research.py) |
| An empty `allow_hosts` refuses every host | [`web_tools.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/web_tools.py) |
| No telemetry at runtime | [Network](../../reference/system-requirements.md#network), measured 2026-09-29, before web search existed |
| Research never invents a source | [ADR-0027](../../architecture/decisions/0027-sovereign-design-provider.md) |

## Limits

- **One engine reviews its own work**, and the ledger says so
  ([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
  `VIBEY_FEATURE_QWENLOOP=1` with `--engines gptossloop,qwenloop` adds a second local
  reviewer, at the cost of `qwen3:14b` and its memory.
- **A local model is not a frontier model** ([the honest ceiling](../local-models-ollama.md#the-honest-ceiling)).
- **One machine was measured**, an Apple M5 with 24 GiB.
- **Your project's own build and test commands** run as they always do, network and all.
- **The paid engines' libraries still install**; workers never call them unless allowed. A bare
  `vibey doctor` does check them, and claudeloop's bundled CLI was seen trying
  `api.anthropic.com`; offline, use `--engine gptossloop`.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| `model '…heretic…' is not served by http://127.0.0.1:11434/v1` | The model is not pulled | Step 2's `ollama pull` |
| A `research_evidence` gate: "cannot research 'prior-art'" | No notes, and no search answered | Add `prior-art.md`, then answer the gate |
| `the local SearXNG at … did not answer` | No SearXNG runs | Nothing, if you meant it offline |

## Where next

- [Local models on Ollama](../local-models-ollama.md): server settings and a second local engine.
- [Cap what agents spend](cap-agent-spending.md): if you ever allow a paid engine.

## Say it in one line

vibey runs agents on a local GPT-OSS 20B with no paid engine allowed, and web research, the one door out, closes with three settings.

## Improve this guide

If a step failed on your machine, or a link does not prove its sentence, that is a good first
contribution. This page is
[`docs/guides/outcomes/run-agents-on-your-own-hardware.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/run-agents-on-your-own-hardware.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which step and what you saw.
