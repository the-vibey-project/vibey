The `exporter/` package renders rows (a list of `dict[str, str]`) as text. `exporter/render.py`
has `render_json` and `render_csv`; `exporter/cli.py` has `run(argv, rows)`, which picks the
format with a hard-coded if/elif. Replace that with a registry and add a Markdown format.

1. Create `exporter/registry.py` with class `FormatRegistry`:
   - `register(name, renderer, replace=False)` stores a renderer (a function from rows to str)
     under `name.lower()`. Registering a name that already exists raises `ValueError`, unless
     `replace=True`.
   - `get(name)` returns the renderer; the lookup is case-insensitive; an unknown name raises
     `KeyError`.
   - `names()` returns the registered names as a sorted list.
   - `__contains__` works too, so `"csv" in registry` is case-insensitive.
2. In `exporter/registry.py` also add `default_registry() -> FormatRegistry`, which returns a
   NEW registry each call holding `json`, `csv` and `md`.
3. In `exporter/render.py` add `render_markdown(rows)`. With no rows it returns `""`. Otherwise
   the columns are the keys of the first row. Output is a header line `| a | b |`, a separator
   line `| --- | --- |`, then one line per row, each line ending in `"\n"`. A `|` inside a cell
   is written as `\|`. Missing keys in a later row render as an empty cell.
4. Change `run` in `exporter/cli.py` to `run(argv, rows, registry=None)`. When `registry` is
   None use `default_registry()`. It must look the format up in the registry (no if/elif), so a
   format registered by a caller works. Behaviour that stays the same: the default format is
   `json`, `--format` without a value gives `(2, "usage: --format NAME\n")`, and an unknown format
   gives `(2, "unknown format: NAME\n")` with NAME lower-cased.
