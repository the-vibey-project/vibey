* **The in-memory AWS adapter and its test pass the lint and provenance gates:** two unused imports in
  `vibey.infrastructure.aws.adapter`, an unsorted import block and a deprecated
  `datetime.utcnow()` in `tests/unit/test_aws_client_port.py`, the formatting of both files, and the
  fingerprint header that `aws/__init__.py` and that test were missing. They came in unchecked with
  the continuation lane's backlog run and turned `ruff check`, `ruff format --check` and the
  provenance check red on develop. No behaviour changes.
