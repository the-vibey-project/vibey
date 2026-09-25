# 0062 — vibey and Krypton

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
   engine are **vibey**, and every app and interface a person uses is **Krypton**.
2. **The emblem is the krypton atom** (Z = 36, four shells), and the logo mark draws it.
3. **"vibey" stays the name of what ships.** The distribution, the command and the
   repository keep their names. The ruling adds a name and renames nothing.
4. **Nothing beyond the ruling is decided here.** The operator did not say whether
   releases, branches or builds carry either name, so this record leaves that open.
5. **The name appears where the project describes itself.** `README.md` and
   `docs/index.md` each gain one line naming vibey and Krypton and citing 9.e.

## Consequences

- Readers of the README and the docs home page learn both names, and the logo mark has
  a ratified meaning.
- Any later use of either name beyond this (release names, build labels, a product surface) needs
  the operator's ruling first. It then amends 9.e or is recorded beside it.
- The logo artwork itself belongs to the design-system lane. This record fixes the name
  and the emblem, not the drawing.


## Revision before merge

The operator clarified the ruling on 2026-09-25: *"the PROJECT and ENGINE are called \"vibey\", all apps/uis are called \"krypton\""*. Sub-doctrine 9.e states that: vibey names the project and engine, Krypton names every app and interface, and package and command names are unchanged. The VS Code extension's display name changes from "Vibey" to "Krypton" in the client-suite lane that raises the extension to the Beauty Law.

## The `krypton-app` distribution

On 2026-09-25 the operator registered **`krypton-app`** as a trusted publisher on both indexes: repository `the-vibey-project/vibey`, workflow `release.yml`, environment `pypi` on PyPI and `testpypi` on TestPyPI. The apps therefore ship as their own distribution, beside `vibey`, and follow the same channels (ADR-0028):
- stable from `main` to PyPI;
- nightly from `develop` to TestPyPI.

`vibey` stays the one distribution of the project and engine (ADR-0037). The client-suite release lane adds the `krypton-app` build and publish jobs to `release.yml`, using the two environments above. Until something is built there is nothing to publish, and no job claims otherwise.
