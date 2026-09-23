"""spec file -> GitHub issue (title from '## Title', rules inlined). Prints the issue number."""

import re
import subprocess
import sys
from pathlib import Path

import storm_paths

spec = Path(sys.argv[1]).read_text()

# Never a literal: the storm root is derived from this tool's own location (12.h).
tpl = (storm_paths.storm(__file__) / "SPEC-TEMPLATE.md").read_text()
rules = tpl.split("## Hard repository rules (always)", 1)[1].strip()
title = re.search(r"^## Title\n(.+)$", spec, re.M).group(1).strip()
body = spec.split("\n", 2)[2] if spec.startswith("## Title") else spec
body = re.sub(r"^## Title\n.+\n", "", spec, count=1, flags=re.M)
body = re.sub(r"See /private/tmp/\S+SPEC-TEMPLATE\.md\.?", rules, body)
body = (
    "Part of the **QwenStorm for 3.0.0**: making ratified sub-doctrine 8.b true at runtime. "
    "A local qwenloop lane implements this issue; the result is reviewed and verified "
    "before it becomes a pull request.\n\n" + body.strip() + "\n"
)
out = subprocess.run(
    [
        "gh",
        "issue",
        "create",
        "-R",
        "the-vibey-project/vibey",
        "--title",
        title,
        "--label",
        "qwenstorm",
        "--body",
        body,
    ],
    capture_output=True,
    text=True,
)
if out.returncode:
    sys.exit(out.stderr)
print(out.stdout.strip().rsplit("/", 1)[-1], title)
