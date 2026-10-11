* **`[publish]` in `vibey.toml` now reaches the project:** `vibey new` copies only an allow-list
  of runtime tables from `vibey.toml` into the project's stored config, and `publish` was not on
  it, so a `[publish] mode = "interview"` was silently dropped and a finished project never
  published. `publish` is on the list, and a `[publish]` table that is wrong (`mode = "sometimes"`)
  is refused when the project is created, not when it finishes.
