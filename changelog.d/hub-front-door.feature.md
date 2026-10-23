* **The hub has a front door:** `krypton` opens `http://127.0.0.1:8765/` in a browser, and that address answered
  `{"detail":"Not Found"}`. `GET /` now returns a plain page that says the hub is running and where to go next
  (the desktop app, `@krypton /new` in VS Code, `vibey hub pair` for a phone, `vibey new` in a terminal). It holds
  no data, asks for no credential, has no script and sits outside the API contract; its Content-Security-Policy
  admits its one style block by hash, and every other route keeps `default-src 'none'`.
