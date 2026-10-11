* **How many work items a plan has follows the spec, not a number:** the work-plan check
  re-asked any item that claimed more than six acceptance criteria or listed more than twelve
  paths, and its message dictated the answer ("split it into a chain of build pieces"), while the
  prompt said "Aim for 2 to 4 items". The two disagreed, so a spec with nine criteria that
  belonged together was sent back again and again, and each regenerated plan split the work in a
  way the spec never asked for. Both caps and the target count are gone, and so is the cap on what
  folding a check-only item may give another item. The prompt now says the opposite: there is no
  target, keep work that belongs together in one item, split where the work really divides (a
  different concern or layer, something that must exist first, or more than one engine session
  can finish), and never split to make items smaller or merge dependent pieces to make fewer. What
  is still checked is what makes a plan unsound: every criterion claimed, dependencies that come
  first, files that exist or are planned, and verification that can run.
