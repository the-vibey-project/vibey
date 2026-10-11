* **`gptossloop` DECOMPOSE places a criterion no work item claims with one short question,
  instead of regenerating the whole plan:** a local model that splits a plan into a chain of
  build pieces drops acceptance criteria, and the plan check answered every drop by asking for
  the entire plan again -- seven attempts and about eight minutes ending in an
  `attempts_exhausted` gate, for the sake of two ids. Now each criterion nothing claims is put to
  the model alone: which of this plan's items builds it, answered from an enum of those item
  ids (a grammar small enough to compile, so it cannot be malformed or name an item that is not
  there). The criterion is added to that item's acceptance and checked criteria, and the plan
  check then runs over the result as before, so an answer that names no item still refuses the
  plan, naming the criterion. An item that lists a criterion in its verification but forgot to
  claim it is now credited with it rather than re-asked. Every other rule (missing files,
  dependency order, the size caps) re-asks as it did.
