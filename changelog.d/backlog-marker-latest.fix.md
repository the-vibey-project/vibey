- **Backlog loop:** the hourly cleanup compares an issue against the verdict it posted most
  recently, not the first one it ever posted. While a changed verdict waited for its
  expectations commit, the loop had re-posted the same status report every hour (#1204 got six
  identical copies between 2026-09-27 and 2026-09-29). The guard now has tests.
