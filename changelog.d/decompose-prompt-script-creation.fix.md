* **The local DECOMPOSE prompt says an item may verify with a script it creates:** a
  `build.decompose` for a content-import project was rejected seven times because the first item
  verified with `node scripts/import-ministry.js`, a script a later item created. The model's own
  reasoning (in the wire log) was that verification cannot create files, so it "must assume the
  script exists", and it never planned the script in the item that ran it. The prompt now says an
  item is work an engine performs, that its verification runs after that work, that a script it
  creates and lists in `files_touched_hint` counts, and that no item may run a file only a later
  item creates. It also tells the model to list each path once (one attempt repeated the same
  four paths 504 times).
