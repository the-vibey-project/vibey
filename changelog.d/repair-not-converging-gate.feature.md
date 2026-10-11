* **A repair that cannot change the failure parks a `repair_not_converging` gate instead of
  repairing again:** a real run spent about four hours and twenty sessions on one work item whose
  build failed the same way every time (a `node_modules` holding nothing but a Vitest cache, so
  the Next.js package could not be found), because the repair rounds were only counted, and
  `--auto-answer` granted more each time the count ran out. Verify and integrate now also compare
  each failure with the last two raised for the item, reading paths, ids, numbers and whitespace
  as the same. A failure that has survived two repairs unchanged parks the item with the failure
  quoted and a pointer at the environment, where the old behavior raised a third identical
  finding. The gate is never auto-answered, so `--autonomous` stops there. Any answer resumes the
  repairs with a fresh count: what was raised before a person's answer is no longer held against
  the item. A finding with no recorded text never counts as unchanged.
