* **`VIBEY_OLLAMA_THINK` and `VIBEY_OLLAMA_RETRY_CONTEXT`:** two settings for the sovereign
  DESIGN and DECOMPOSE client. `VIBEY_OLLAMA_THINK` sets the reasoning level of the *first*
  request, where before only the retry could be told to reason lightly, so a first attempt no
  longer has to spend itself reasoning before it is retried. And a reply cut short because the
  prompt filled the window now gets a retry that opens a larger one, up to
  `VIBEY_OLLAMA_RETRY_CONTEXT` (default 32768), where before it asked again inside the same
  window and failed the same way: live, a 6504-token prompt in an 8192 window left 1688 tokens for
  the reasoning and the answer, and the retry was given the same 1688. `vibey llm tail` also
  shows how long a response spent loading the model and reading the prompt, which a token rate
  never reveals.
