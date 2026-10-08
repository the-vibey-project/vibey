* **docs:** the analytics start-up no longer prints its own source at the top of every published page. A comment in
  `analytics.ts` spelled out a closing script tag, which ends an inline script early wherever it appears; the comment
  is reworded and a test now refuses that markup in any asset the release workflow inlines.
