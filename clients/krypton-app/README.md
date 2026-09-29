# krypton-app

krypton is every app and interface of [vibey](https://the-vibey-project.github.io/vibey/).
This package carries them and installs one command, `krypton`.

```bash
pip install krypton-app      # brings vibey-engine[hub] with it: the engine and its web hub
krypton                      # start the local vibey hub and open it in your browser
krypton --help
```

## What `krypton` does today

`krypton` is a launcher. It finds the `vibey` command, starts `vibey serve` on
`127.0.0.1:8765` (change it with `--host` and `--port`), waits until the hub answers, and
opens it in your browser. `--no-browser` only starts it.

When the installed vibey-engine has no `vibey serve` yet, `krypton` says so plainly, lists
what you can use instead, and exits with status 1. It never pretends a hub is running.

## Releases

Published by `.github/workflows/krypton-app.yml` alone, by trusted publishing: a dev build
to TestPyPI (environment `testpypi`) on each push to `develop` that changes this tree or the
workflow, and a release to PyPI (environment `pypi`) on each such push to `main`. There is no
schedule. A push GitHub skips publishes nothing: a squash merge whose message quotes an old
`[skip ci]` subject skips every push workflow, which is how the 3.0.0 promotion first
published neither package. Merge a promotion by rebase, or edit the squash message. ADR-0069 records why vibey publishes exactly two packages, `vibey-engine` and
`krypton-app`.
