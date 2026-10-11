* **The claudeloop stream viewer no longer crashes when its thinking indicator ticks during
  teardown:** the 0.5-second thinking tick queried `#thinking-bar` with no guard, so a tick that
  landed while the screen was being replaced or closed raised `NoMatches`, which showed up as an
  intermittent `test_prev_turn_replay` failure on the release commit. It now waits until the bar
  exists, like the live and replay ticks, and retries on the next interval.
