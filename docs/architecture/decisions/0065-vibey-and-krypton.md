# 0065 — vibey and krypton

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrine 9.e, drafted in the change that carries this record and awaiting the operator's ratifying merge (Constitution Article II.3) · **Related:** ADR-0020 · **Evidence:** `develop` at `0a2f856e`, read 2026-09-25

**Owes:** the conduct is sub-doctrine 9.e, drafted in the same pull request for the
operator's ratifying merge (ADR-0020: the record argues, the canon states). This record
also owes the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.
Both are done in the change that carries it.

## Context

The design-system lane is redrawing vibey's logo mark as the krypton atom: krypton-84,
atomic number 36, with its 36 electrons in four shells of 2, 8, 18 and 8. On 2026-09-25
the operator ruled, in their words: *"the codename for vibey should be krypton please
make that law please"*.

A name the project uses for itself binds every later surface that names the project, and
it survives any rewrite of the code. Under ADR-0020 that makes it a governing rule, so it
belongs in the canon, not only in a design file.

## Decision

1. **The name is canon.** Sub-doctrine 9.e, filed under 9 (*The vibe*) beside the other
   entries on the project's identity and craft, says that the project and its
   engine are **vibey**, and every app and interface a person uses is **krypton**.
2. **The emblem is the krypton atom** (Z = 36, four shells), and the logo mark draws it.
3. **The commands and the repository keep their names.** The published packages are
   `vibey-engine` and `krypton-app` ("Four names, two packages", below); no `vibey`
   package is published.
4. **Nothing beyond the ruling is decided here.** Which packages publish, and from which
   branch to which index, is ruled below. Release names, branch names and build labels
   are not ruled, and this record leaves them open.
5. **The name appears where the project describes itself.** `README.md` and
   `docs/index.md` each gain one line naming vibey and krypton and citing 9.e.

## Consequences

- Readers of the README and the docs home page learn both names, and the logo mark has
  a ratified meaning.
- Any later use of either name beyond this (release names, build labels) needs
  the operator's ruling first. It then amends 9.e or is recorded beside it.
- The logo artwork itself belongs to the design-system lane. This record fixes the name
  and the emblem, not the drawing.


## Revision before merge

The operator clarified the ruling on 2026-09-25: *"the PROJECT and ENGINE are called \"vibey\", all apps/uis are called \"krypton\""*. Sub-doctrine 9.e states that: vibey names the project and engine, krypton names every app and interface, and command names are unchanged. The later ruling on packages is recorded in "Four names, two packages". The VS Code extension's display name changes from "Vibey" to "krypton" in the client-suite lane that raises the extension to the Beauty Law.

## Four names, two packages

On 2026-09-25 the operator registered trusted publishers on PyPI (environment `pypi`) and TestPyPI (environment `testpypi`) for the repository `the-vibey-project/vibey`:
- `vibey-engine`, published by `vibey-engine.yml`;
- `krypton-app`, published by `krypton-app.yml`.

The operator ruled that the canon names exactly four names:

| Name | What it names |
|---|---|
| `vibey` | the project and its engine |
| `vibey-engine` | the engine's package |
| `krypton` | every app and interface |
| `krypton-app` | the apps' package |

Only the two packages are published, each with its own workflow. Stable releases go from `main` to PyPI and nightly ones from `develop` to TestPyPI (ADR-0028). No `vibey` package is published under the new scheme, since that name is taken on TestPyPI.

This supersedes in part ADR-0037's single `vibey` distribution. The packaging change itself is its own pull request and ADR; until it lands, publishing continues as today, and nothing claims otherwise.

## Always lowercase

The operator ruled on 2026-09-25 that krypton is always fully lowercase: exactly `krypton` or `krypton-app`, never capitalised. 9.e states it for both names.
