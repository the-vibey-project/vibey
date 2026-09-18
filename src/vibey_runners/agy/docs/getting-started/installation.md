# Installation

Python 3.12+.

## PyPI (recommended)

`agyloop` is not a PyPI project of its own. It ships inside the `vibey`
distribution, which installs every `*loop` runner and every family tool in one
step (vibey ADR-0037):

```bash
pip install vibey
pipx install vibey
```

Then:

```bash
agyloop --help
agyloop doctor
```

## TestPyPI

Runtime dependencies still resolve from real PyPI. The dev channel publishes the
whole family as `vibey-dev`:

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ vibey-dev
```

## Clone / editable (contributors)

```bash
git clone https://github.com/the-vibey-project/vibey.git
cd vibey/src/vibey_runners/agy
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pre-commit install
agyloop --help
```

Or with uv:

```bash
uv sync --extra dev --extra docs
uv run agyloop --help
```

Auth is **either** `GOOGLE_API_KEY` (Gemini Developer API) **or** Application
Default Credentials with a Vertex / Enterprise flag. `agyloop doctor` reports
the lane; it never guesses. See [Configuration](configuration.md).
