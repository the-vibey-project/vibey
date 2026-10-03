# 0081 — vibey's chat, inside GitHub, resilient to the parts around it failing

**Status:** accepted · **Date:** 2026-10-03 · **Issue:** [#1384](https://github.com/the-vibey-project/vibey/issues/1384) · **Cites:** sub-doctrines 8.a, 10.l, 12.d, 12.e, 12.h and 12.j; SD-01 §4 · **Related:** ADR-0075, ADR-0080 · **Evidence:** `develop` at `e7cf4d351`, read 2026-10-03

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; `properdocs.yml` nav entries for this record and for
`docs/continuation/chat.md`; `docs/llms.txt` regenerated from that nav. All are in the
change that carries this record.

## Context

The operator asked to be able to talk to vibey's own agent from inside GitHub — in issue and
pull-request comments, and from the Actions tab — and for it to be "resilient to
destruction". The continuation lane (ADR-0080) already runs an open-weights model on
GitHub-hosted CPU runners; the chat is the same machinery answering a person instead of a
schedule. Three facts shape it. A comment-triggered workflow on a public repository runs
with the base repository's secrets for anyone who can comment. The handle `@vibey` belongs to
an unrelated GitHub user, so a mention would notify a stranger. And the model runs at about
three tokens a second, so a reply takes minutes.

## Decision

1. **Triggers.** `/vibey <request>` at the start of an issue or pull-request comment, or a
   review comment, and a `workflow_dispatch` with a message and an optional issue or pull
   request to answer in (the Actions tab and the mobile app). `/vibey act <request>` may
   answer with a draft pull request. The trigger, the trusted associations, the caps and the
   reply file are declared in `[chat]` in `scripts/continuation_prompts.toml` (12.h).
2. **Who is answered (12.j).** Only the associations `[chat] trusted` names (owner, members,
   collaborators); every other commenter and every bot is ignored without a reply. Dispatching
   already requires write access.
3. **Three jobs, so the model can write nothing.**
   - `gate` decides, reacts, and gathers the thread as text through the API — a pull
     request's own code is never checked out.
   - `think` runs the model with `contents: read` and no secret; it hands over a reply file
     and a patch.
   - `reply` runs on a fresh runner, always, and defuses the *whole* comment before posting
     it, since every file `think` handed over is untrusted. A patch goes through the one
     shared guard (`[authority] protected`, `continuation_prompts.py guard`) that the weekly
     lane uses, and opens only a draft.
   A person's words reach a shell only through `env:`, never `${{ }}` interpolation.
4. **Resilient to destruction.** Each way it could stop has its answer:
   - a model tag that cannot be pulled falls back along `[run] models`;
   - an unreachable Ollama installer falls back to Ollama's own GitHub release;
   - a model run that fails or times out still produces a reply that says so — a person is
     never left waiting in silence (12.e);
   - a lane disabled by hand is not re-enabled over a person's choice, but the weekly
     keepalive files one tracking issue saying so;
   - a lane deleted, or stripped of a guard — the trust check, the shared guard, the
     defusing, the refusal to check out pull-request code, GitHub-hosted runners — fails
     `scripts/continuation_prompts.py check` on every pull request, and the meta tests pin
     the model job's permissions and the absence of interpolated input;
   - the whole design is in the repository, so the Rebuild prompt re-creates it.

## Consequences

- Replies are slow and short-winded: a heartbeat-grade model on a CPU, answering from a
  bounded, cut-loud context (ADR-0075). A future operator can point `[run] runs_on` and
  `[run] models` at faster hardware without touching the guards.
- A review comment on a fork's pull request gets a read-only token from GitHub, so the reply
  job cannot post there; it fails visibly rather than silently.
- Replies are model output, marked as such in every comment.
