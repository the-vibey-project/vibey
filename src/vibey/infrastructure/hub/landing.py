# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's front door: what a browser shows at `http://127.0.0.1:8765/`.

`krypton` starts the hub and opens that address, and a person who is not a developer
reads whatever is there. Before this page it was `{"detail":"Not Found"}`. The page says
what the hub is, that nothing is broken, and where to go next. It carries no data and asks
for no credential, so it can be served to anyone the hub already answers; every route that
holds anything still needs the host's token or a paired device's key (ADR-0067).

The hub sends `default-src 'none'` on every response, which also forbids a page its own
styling. This page keeps that policy and adds the hash of its single style block, so the
only style that runs is the one written here; there is no script and no external file.
"""

import base64
import hashlib
from typing import Final

STYLE: Final = """
:root{color-scheme:light dark;--bg:#fbfbfd;--fg:#16181d;--muted:#5b6270;--card:#fff;--line:#e3e6ee;--accent:#5b5bd6}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#eceef3;--muted:#9aa3b2;--card:#171a21;--line:#272b35;--accent:#8e8ef2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:40rem;margin:0 auto;padding:4rem 1.25rem 3rem}
h1{font-size:1.75rem;margin:0 0 .25rem}
.ok{display:inline-block;width:.6rem;height:.6rem;border-radius:50%;background:#2fa66a;margin-right:.5rem}
.lede{color:var(--muted);margin:0 0 2rem}
section{background:var(--card);border:1px solid var(--line);border-radius:.75rem;padding:1.1rem 1.25rem;margin:0 0 1rem}
h2{font-size:1rem;margin:0 0 .35rem}
p{margin:.25rem 0}
code{font:.9em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);border:1px solid var(--line);border-radius:.35rem;padding:.1em .4em}
a{color:var(--accent)}
footer{color:var(--muted);font-size:.875rem;margin-top:2rem}
"""
"""The page's only style. Its hash is what the policy admits."""

BODY: Final = """<main>
<h1><span class="ok"></span>The vibey hub is running</h1>
<p class="lede">Nothing is broken, and there is nothing to click here. This is where your
krypton apps connect.</p>
<section>
<h2>Use it from an app</h2>
<p><strong>On this computer:</strong> open the krypton desktop app, or the Chat panel in VS Code
and type <code>@krypton /new</code>. They find this hub by themselves.</p>
<p><strong>On your phone or another computer:</strong> run <code>vibey hub pair</code> here, then
type the six digits it shows into the app.</p>
</section>
<section>
<h2>Start a project</h2>
<p>From a terminal: <code>vibey new my-project</code>. From an app: press Start a project
(a device can do this once this computer's <code>vibey.toml</code> sets
<code>[hub] projects_root</code>).</p>
</section>
<section>
<h2>Is it healthy?</h2>
<p><a href="/health/ready">/health/ready</a> answers when the database does.
<code>vibey doctor</code> checks everything else and says what to do about it.</p>
</section>
<footer>New to vibey? <a href="https://the-vibey-project.github.io/vibey/">Read the guide</a>.</footer>
</main>"""
"""The page's content: plain words, no data, no script."""


class HubLandingPage:
    """The hub's front door, as one document."""

    def render(self) -> str:
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>vibey hub</title>"
            f"<style>{STYLE}</style></head><body>{BODY}</body></html>"
        )

    def content_security_policy(self) -> str:
        digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
        return (
            "default-src 'none'; "
            f"style-src 'sha256-{digest}'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        )


HUB_LANDING_PAGE: Final = HubLandingPage()
"""The page `vibey serve` mounts at the hub's root."""
