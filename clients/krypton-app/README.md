# krypton-app

krypton is every app and interface of [vibey](https://the-vibey-project.github.io/vibey/).
This package carries them and installs one command, `krypton`.

```bash
pip install krypton-app      # brings vibey-engine with it
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

Published by `.github/workflows/krypton-app.yml` alone: nightly from `develop` to TestPyPI
(environment `testpypi`), stable from `main` to PyPI (environment `pypi`), by trusted
publishing. ADR-0068 records why vibey publishes exactly two packages, `vibey-engine` and
`krypton-app`.
