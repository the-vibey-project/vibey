* **daily lanes:** the backlog killer runs every 90 minutes instead of once a day, sixteen
  runs a day from two interleaved three-hourly schedules. Its pick rotates through the ranked
  window by 90-minute slot rather than by date, so the day's runs no longer all choose the same
  issue. The interval is `[backlog_killer] interval_minutes` in `scripts/daily_lanes.toml`, and
  a test fails if the workflow's schedules stop firing once per declared interval (ADR-0083,
  amended).
