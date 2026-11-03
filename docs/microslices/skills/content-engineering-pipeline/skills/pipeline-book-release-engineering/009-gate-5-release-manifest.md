---
id: skill-gate-5-release-manifest-4be09ecb53
purpose: gate 5 release manifest
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-4-all-page-visual-evidence-835aa8f0f9"]
links: ["skill-retrospective-lessons-made-executable-d2068f6822"]
---

## Gate 5: release manifest

Write one machine-readable manifest for the exact release attempt. A minimal
manifest contains:

```json
{
  "schema_version": 1,
  "source": {"git_commit": "...", "config": "books/example.toml"},
  "manuscript": {"word_count": 0, "chapters": 0, "warnings": []},
  "steps": [{"name": "pdf", "status": "pass", "command": []}],
  "artifacts": [
    {"kind": "pdf-interior", "path": "output/example.pdf", "sha256": "..."},
    {"kind": "epub", "path": "output/example.epub", "sha256": "..."}
  ],
  "visual_qa": {"page_count": 0, "rendered_pages": 0, "contact_sheets": []},
  "human_review": {"status": "pending", "reviewer": null, "notes": []}
}
```

The manifest is not a marketing document. It is a chain of custody. If the
branch changes, a merge conflict is resolved, or any source file changes after
the report, the old manifest is evidence for the old release attempt and must
not be reused. Rerun the complete graph and issue a new manifest.
