# 0053 — An unattended run takes direction only from the operator's account, and outside text is contained at the seam it enters

**Status:** proposed · **Date:** 2026-09-23 · **Cites:** sub-doctrine 12.j which this record implements, and SD-01 §2/§4/§7, 12.d, 12.f, 10.f · **Related:** ADR-0046, ADR-0049 · **Evidence:** 195 of the last 200 merged pull requests authored by `adammatthewsteinberger` and 5 by `app/dependabot`; `queue.txt` mapping every lane to an issue number whose body becomes the model's prompt

**Owes:** nothing new as conduct — 12.j is the conduct and is ratified separately (ADR-0020:
the record argues, the canon states). It owes the advertised ADR count in `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

The operator's instruction: during an authorised, fully autonomous storm run, nobody but the
operator's account or CODEOWNERS may make changes; and prevent prompt injection from remote
causing problems.

The operator also made the framing precise, and it matters: *"you are the agent but my account
is what does the changing."* The agent acts as the operator's account, so the control is not a
boundary between the operator and their agent. It is a boundary around the account, and
everything outside it is a stranger — including software that has been trusted for a year.

Two surfaces exist today.

**Authorship.** `vibey-gh merge-train` merges any pull request whose head carries a successful
gate, and ADR-0049's delegated approver approves within a declared grant. Neither asks *whose*
pull request it is. Over the last 200 merged pull requests, 195 were the operator's and 5 were
`app/dependabot` — so the allowlist is narrow by nature, and the one other actor is precisely
the one that should not land unreviewed overnight. A dependency bump is the plainest
supply-chain case and the easiest to wave through, because it looks like exactly the kind of
change that does not need a person.

**Prompt injection.** `queue.txt` maps each lane to an issue number, and `qwenlane.py` takes
that issue's title and body as the model's prompt. An issue can be opened by anyone. Remote text
therefore already reaches a prompt held by an agent carrying the operator's credentials, which
is SD-01 §4's exact scenario rather than a hypothetical one. The repository has one control of
this shape already and it is the right shape: `delivery-estimate.yml` bars `issues` events from
the job holding `contents: write`, with the comment "an issue can be opened by anyone".

## Decision

While an autonomous run is under way with nobody watching, only the operator's own account may
direct it. Everything from anywhere else is data to be acted on, never instruction to be acted
upon.

**The allowlist is declared, narrow, and refuses by default.** `[unattended_approval] authors`
in `.vibey-gh.toml` names the logins a delegated approver may act for, with `@codeowners` as a
sentinel expanding to the accounts in `.github/CODEOWNERS`. `enabled = true` with an empty
`authors` is rejected rather than treated as "anyone", because 12.f is explicit that absence of
a grant is refusal and a default that admitted everybody would make installing the tool the act
of granting. A missing CODEOWNERS file expands to nothing, not to everyone.

**Containment belongs at the seam, not in the reader's judgement.** Text entering from the forge
is marked as what it is before it reaches a prompt, so that the thing reading it is never in the
position of having to notice. A control that depends on a model deciding correctly each time is
not a control; it is a hope with a good track record.

**Ambiguity stops the run.** An unattended pass that cannot establish whose words it is reading
refuses and says so, per SD-01 §7 and 10.f — missing evidence stays unknown, and silence from
the operator means no. This is the same shape as `lane-reap.py` refusing to act when it cannot
read the process table: "I see no stranger" and "I cannot tell" are the same value and opposite
facts.

## Consequences

An outside contribution cannot land overnight. It waits for a person, which is what a pull
request from a stranger has always been for.

Dependabot's pull requests stop merging unattended. This is a real cost — security updates now
wait for a person — and it is the right trade at this scale: the repository has one human, and a
dependency that lands unreviewed while they sleep is the supply-chain compromise this project's
own security policy exists to prevent. An operator who wants them merged unattended adds the
login to `authors`, in a reviewed diff, having decided it.

The refusals are reportable output, not silence (12.d). An unattended run that declined to act
on three pull requests says so, because that is the most useful part of the report.

## Alternatives considered

**Rely on branch protection and CODEOWNERS alone.** They gate who may *approve*, not who may
*author*, and the merge train's job is to act once a gate is green. The gap is precisely between
them.

**Allowlist by organisation membership rather than by login.** Wider than the operator meant,
and it drifts without a diff: somebody joins the organisation and the allowlist silently grows.
A login in a file changes only when somebody changes it.

**Detect injection by scanning text for suspicious phrases.** A denylist of phrasings is a
filter that reports a clean result on everything it has not seen, which is the failure this
project spent a night removing eleven instances of. Containment marks the provenance of text
rather than attempting to judge its content.

**Trust the model to notice.** This is the status quo, and it is the thing SD-01 §4 exists to
replace. Fluency is not evidence of provenance, and a good track record is not a control.
