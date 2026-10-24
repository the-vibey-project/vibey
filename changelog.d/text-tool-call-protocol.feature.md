* **A model with no tool-calling can be driven through a text protocol:** `tool_protocol = "auto"` (also `native`,
  `text`) carries tool calls as `<tool_call>` text for a model its Ollama reports without `tools`, instead of sending a
  tool list Ollama rejects. The run says when it is in use. Measured on a small BUILD task it is about twice as slow
  per turn and did not make Llama 3.1 8B or DeepSeek Coder 1.3B build correctly (0 of 8 and 0 of 3, against 1 of 3 for
  `gpt-oss:20b`); the method and numbers are in `docs/architecture/evidence/`. ADR-0093, #1662.
