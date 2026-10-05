#!/usr/bin/env python3
import re
from pathlib import Path

# Path to the PR list file
PR_LIST = "pr_list.txt"

# Regex to parse a line like:
#  #1035 [OPEN] epic(roadmap): the roadmap epics, ...
LINE_RE = re.compile(r"^#?(\d+) \[OPEN\] (.+)$")


def is_draft(title: str) -> bool:
    """Return True if the PR title marks it as a draft."""
    return "draft" in title.lower()


def parse_pr_line(line: str):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    number = int(m.group(1))
    title = m.group(2).strip()
    return number, title


def main():
    text = Path(PR_LIST).read_text(encoding="utf-8")
    lines = text.splitlines()
    open_prs = []
    for line in lines:
        parsed = parse_pr_line(line)
        if not parsed:
            continue
        num, title = parsed
        if is_draft(title):
            continue
        open_prs.append((num, title))
    open_prs.sort()
    print("| PR # | Title |")
    print("|------|-------|")
    for num, title in open_prs:
        # Truncate title to 70 for display clarity
        disp = (title[:67] + "...") if len(title) > 70 else title
        print(f"| {num:<4} | {disp:<70} |")

if __name__ == "__main__":
    main()
