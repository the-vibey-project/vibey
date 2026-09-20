# Installation

Requires **Python 3.12+** on **macOS or Linux**, and a Cursor account with
`CURSOR_API_KEY` for live runs.

`cursorloop` is not a PyPI project of its own. It ships inside the `vibey`
distribution, which installs every `*loop` runner and every family tool in one
step (vibey ADR-0037):

```bash
pipx install vibey
# or
pip install vibey
```

From a clone:

```bash
git clone https://github.com/the-vibey-project/vibey.git
cd vibey/src/vibey_runners/cursor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Next: [Quickstart](quickstart.md).
