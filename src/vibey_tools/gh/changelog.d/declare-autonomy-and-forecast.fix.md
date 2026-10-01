- **Fix:** `vibey-gh doctor` no longer reports two tables it misjudged. `[autonomy]` (the
  operator's standing grant, #1300) is now a section vibey-gh reads and validates
  (`AutonomyConfig`): a `standing_grant` whose `never` list is empty is refused, because a
  grant is read narrowly and one that names no bounds has none to read. `[estimate.forecast]`
  was always read by the loader, but `doctor` called it "silently ignored" because its keys
  carry no `forecast_` prefix; `doctor` now knows that table's keys and still names a stray
  one in it.
