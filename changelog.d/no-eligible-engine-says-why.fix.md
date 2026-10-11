* **A job no engine can take now says why:** a worker that could not place a job deferred it
  with "No engines meet requirements for project ..." and nothing else, so an engine that was not
  conformant, a login check gone stale, an open circuit, the engine a retry must rotate away from
  and an engine left out of `--engines` all read the same, and a job could be deferred every five
  minutes for an hour with no way to tell which. The message now lists each engine and the rule
  that turned it down, names an engine the worker may use but has no health record for yet, and
  says so when no engine has one. The rules are the ones that already decided eligibility; only
  the explanation is new.
