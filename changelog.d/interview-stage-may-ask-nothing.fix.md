* **A DESIGN interview stage with nothing left to ask asks nothing:** the sovereign interview
  prompt demanded one to four questions at every stage and the schema and decoder refused an
  empty list, so a model whose intake already stated every decision reasoned for most of a minute
  and invented a filler question (Q13, "add a ministry link to the header?", after the decisions
  had ruled it out). The prompt now says to ask none when the ledger already settles the stage
  and never to ask to fill one, and an empty list is accepted. The ledger records the stage as
  settled (a new `StageSettled` event, published with its stage and cycle only) so it is not
  asked again on every replay, and the interview goes on to the next stage with no gate.
