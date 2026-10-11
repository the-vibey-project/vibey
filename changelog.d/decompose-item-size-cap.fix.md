* **A plan item may touch at most 12 paths:** the local DECOMPOSE for the ministry section came
  back as one walking-skeleton item listing 25 paths and all eleven criteria. Its BUILD session
  used all sixteen turns (about 199k input tokens), changed one line of a file the spec forbids
  touching, and was retried. Decompose now rejects, and re-asks naming the item and its path
  count, an item with more than 12 distinct paths in `files_touched_hint`, and the prompt says
  to split larger jobs into a chain of build pieces (each after the first depends on the one
  before it, and the last runs the full verification) and that the walking skeleton is the
  thinnest working slice. Plans whose items are within the limit are unaffected.
