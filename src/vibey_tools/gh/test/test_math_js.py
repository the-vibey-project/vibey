# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""math.js turns the paper's ```latex fences into readable HTML on the documentation site.

Three fences of the research paper printed as raw LaTeX on the site: two `table`
environments, which the script did not know, and a theorem followed by its proof in one
fence, which it refused because it matched a fence only as a single environment. These
tests run the real script under node with a minimal DOM and read what each fence becomes.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from vibey_gh.install import SOURCE_RELEASE_ASSETS

MATH_JS = SOURCE_RELEASE_ASSETS / "javascripts" / "math.js"
NODE = shutil.which("node")

# A DOM with just what math.js touches: createElement, querySelectorAll over the fences,
# and replaceWith. Each fence's replacement is serialised as {class, html, children}.
HARNESS = r"""
const fs = require("fs");
const fences = JSON.parse(fs.readFileSync(0, "utf8"));
const el = (tag) => ({ tag, className: "", innerHTML: "", textContent: "", children: [],
  append(...c) { this.children.push(...c); } });
const outs = fences.map(() => null);
const codes = fences.map((text, i) => ({ textContent: text,
  parentElement: { replaceWith: (x) => { outs[i] = x; } } }));
global.window = {};
global.document = { readyState: "complete", createElement: el,
  querySelectorAll: () => codes, addEventListener() {} };
// Runs this repository's own math.js (the path passed in), exactly as a page loads it.
require("vm").runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const ser = (n) => n && { cls: n.className, html: n.innerHTML, text: n.textContent,
  children: n.children.map(ser) };
process.stdout.write(JSON.stringify(outs.map(ser)));
"""

pytestmark = pytest.mark.skipif(NODE is None, reason="node is needed to run math.js")


def _render(*fences: str) -> list[dict | None]:
    assert NODE is not None
    done = subprocess.run(
        [NODE, "-e", HARNESS, str(MATH_JS)],
        input=json.dumps(list(fences)),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)


DISPATCH_TABLE = r"""\begin{table}[t]
\centering\small
\begin{tabular}{@{}p{1.45in}rrr@{}}
\textbf{Surface} & \textbf{Single} & \textbf{Hybrid} & \textbf{Mux.}\\
Model turns (turns/s) & 0.1162 & 0.2597 & 0.1297\\
\end{tabular}
\caption{Bounded local dispatch experiments.}
\label{tab:dispatch-experiments}
\end{table}"""


def test_a_table_becomes_an_html_table_with_its_header_alignment_and_caption() -> None:
    (out,) = _render(DISPATCH_TABLE)
    assert out is not None
    assert out["cls"] == "latex-env latex-table"
    html = out["html"]
    assert html.startswith("<table><caption><strong>Table 1.</strong> Bounded local")
    assert "<thead><tr><th>Surface</th>" in html
    assert '<th style="text-align:right">Single</th>' in html
    assert '<td style="text-align:right">0.1162</td>' in html
    assert "\\begin" not in html and "\\textbf" not in html


def test_a_wide_table_with_rules_shielded_brackets_code_and_math() -> None:
    fence = r"""\begin{table*}[t]
\begin{tabular}{@{}p{1.3in}p{2.3in}@{}}
\textbf{Requirement} & \textbf{Minimum}\\
\hline
Python & 3.12 (declared $\geq$3.12)\\
Install & with {[}hub{]} 211.0 MB\\
\end{tabular}
\caption{Record \texttt{docs/minimum-specs.json}; a <b> stays text.}
\end{table*}"""
    (out,) = _render(fence)
    assert out is not None
    assert out["cls"] == "latex-env latex-table latex-table-wide"
    html = out["html"]
    assert '<span class="arithmatex">\\(\\geq\\)</span>3.12' in html
    assert "with [hub] 211.0 MB" in html
    assert "<code>docs/minimum-specs.json</code>" in html
    assert "&lt;b&gt;" in html and "<b>" not in html
    assert "\\hline" not in html


def test_a_theorem_and_its_proof_in_one_fence_are_both_converted() -> None:
    fence = r"""\begin{theorem}[Bounded convergence]
Every lineage stops within $A\,(1+k_{\max})$ repairs.
\end{theorem}
\begin{proof}[Proof sketch]
The measure $\mu$ strictly decreases.
\end{proof}"""
    (out,) = _render(fence)
    assert out is not None
    assert out["cls"] == "latex-group"
    theorem, proof = out["children"]
    assert theorem["cls"] == "latex-env latex-theorem"
    assert theorem["html"].startswith("<p><strong>Theorem 1 (Bounded convergence).</strong>")
    assert proof["html"].startswith("<p><strong>Proof sketch.</strong>")


def test_a_proof_without_a_title_keeps_its_label() -> None:
    (out,) = _render("\\begin{proof}\nObvious.\n\\end{proof}")
    assert out is not None
    assert out["html"].startswith("<p><strong>Proof.</strong> Obvious.")


def test_what_is_not_understood_is_left_as_source() -> None:
    unknown = "\\begin{mystery}\nx\n\\end{mystery}"
    half_known = "\\begin{theorem}\nx\n\\end{theorem}\n\\begin{mystery}\ny\n\\end{mystery}"
    stray_text = "prose first\n\\begin{theorem}\nx\n\\end{theorem}"
    no_tabular = "\\begin{table}\n\\caption{empty}\n\\end{table}"
    assert _render(unknown, half_known, stray_text, no_tabular) == [None, None, None, None]


def test_a_display_math_environment_is_escaped_before_it_reaches_the_page() -> None:
    (out,) = _render("\\begin{align}\na &< b\n\\end{align}")
    assert out is not None
    assert out["cls"] == "arithmatex"
    assert "&amp;&lt; b" in out["html"]
