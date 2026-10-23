* **Fedora support:** `vibey install` now recognises Fedora (and `ID_LIKE=fedora` derivatives) and
  installs the local stack with `dnf` — PostgreSQL (`postgresql-server`) and Ollama — and the CI
  `desktop` job builds and tests krypton desktop on `fedora:latest`. An RPM spec for the desktop
  app is declared in `clients/desktop/packaging/fedora/`, to be published to a Fedora COPR on the
  operator's word (ADR-0019). Contributed by @montionugera (#1645, closes #1188).
