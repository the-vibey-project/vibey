* **Large tasks are sliced into the four CDD layers before any runs:** `build.decompose` no longer hands the
  queue one flat list. A plan of more than eight items is grouped into epics, then phases, then a project (never
  more than the four layers of ADR-0039), each group runs to completion before the next, and every job records its
  `slice_path`. The whole plan is sliced, and judged, before any item is enqueued. ADR-0092, #1666.
