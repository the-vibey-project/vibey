* **promote:** `[promotion] schedules` declares when the promotion workflow runs on a clock,
  beside following every successful merge train: for example a monthly release on the 1st
  (`"17 8 1 * *"`) as well as the weekly backstop. Each entry is checked as a five-field cron.
  The default is the weekly backstop alone, so a repository that sets nothing renders the
  same workflow as before.
