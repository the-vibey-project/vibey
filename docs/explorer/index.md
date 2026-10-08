---
description: Look inside a vibey project's ledger in your browser, block-explorer style. Search every public decision, question, finding and phase change, read it in plain words, check its digest yourself, and see exactly what was left out.
---

# Ledger explorer

A block explorer for software work. Every vibey project keeps an append-only ledger of
what happened to it. This page opens every project's **public, scrubbed ledger** for anyone, with
no account and no key; the key, if you hold it, opens the rest.

<div id="ledger-explorer-app" data-base="data/" data-guide="../guides/ledger-publication/">
  <noscript>
    <p>The explorer needs JavaScript. The same records are plain JSON under
    <code>explorer/data/&lt;project&gt;/</code>: <code>manifest.json</code>,
    <code>index.json</code> and <code>records/&lt;event id&gt;.json</code>.</p>
  </noscript>
</div>

## How to use it

- **Pick a project** from the library on the front page. Each row shows its phase, how many
  records are public and how many were withheld.
- **Search** with the box at the top: a word (`cancel`), a sequence number (`#12`), an event
  id, or a digest. A search for one exact record opens it directly. Press <kbd>/</kbd> from
  anywhere to jump to the box.
- **Narrow** with the kind chips (decisions, findings, questions and so on) and the phase strip
  (design, build, review). Every view has its own link, so you can send someone to exactly
  what you are looking at.
- **Open a record** to read what it says in plain words, then check it. Use <kbd>←</kbd> and
  <kbd>→</kbd> to walk the ledger one record at a time.

## What you can trust, and why

- **Each record can be checked by you.** Your browser recomputes the record's SHA-256 digest
  from the payload on screen and says whether it matches. Nothing here asks you to take the
  page's word for it.
- **The gaps are counted, not hidden.** The bar on the first screen shows how much of the
  ledger is public and how much was withheld, and why. The chain head covers every event,
  withheld ones included, so anyone holding the full ledger can confirm this is a true slice.
- **Nothing is sent anywhere.** The page reads static files; what you search for stays in
  your browser.

## What the key unlocks

Everyone sees the same scrubbed ledger: the decisions, questions, answers, findings and phase
changes, with local paths, email addresses and credentials removed, and engine chatter, spend and
text from outside withheld. Nothing publicly safe is hidden.

The whole database is also kept, **sealed with AES-256**, on the repository's `vibey-state` branch
([ADR-0086](../architecture/decisions/0086-state-sync.md)). Anyone can download that file; only the
holder of the state key can open it. On a project page, **Have the key? Unlock the withheld
events** asks for the key and then shows that project's complete ledger, every event, in the same
view. The key is typed into the page, held in that tab's memory and never sent anywhere; closing
the tab or pressing **Lock** forgets it. The page recomputes the hash chain itself, so a sealed
copy that was altered is reported as altered.

[What gets published](../guides/ledger-publication.md) lists every rule the publication policy
applies, and what it removes.

## Publish the ledgers

One command exports every project through the publication policy and writes the explorer's data
and its project registry; which projects are listed is declared in
`scripts/explorer_publish.toml`, and what is shown of each is the policy's decision alone:

```bash
uv run python scripts/explorer_publish.py
```

To publish a single project by hand, the explorer reads what `vibey ledger site` writes:

```bash
vibey ledger export <project-id> --out ledger/<name>.jsonl
vibey ledger site --from ledger/<name>.jsonl --out docs/explorer/data/<name> --json-only
```

Then add the project to `docs/explorer/data/projects.json`. Publishing is a decision: the
export is a *projection* (default-deny, with local paths and email addresses taken out), but
the answers you typed during design are published as you typed them, so read the shard before
you commit it.

Until a project does, the page shows a clearly marked **sample**, built by
`scripts/explorer_sample.py` through the same exporter and policy. It describes no real project.
