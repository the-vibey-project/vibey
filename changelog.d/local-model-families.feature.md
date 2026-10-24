* **`vibey models` and eight named model families:** Qwen Coder, DeepSeek Coder, Codestral, StarCoder, Gemma, Llama,
  CodeLlama and CodeGemma, each with a starting Ollama tag, plus what the Ollama on this machine reports each model can
  do. Capabilities come from Ollama's own `/api/show`, never a table, because tool-calling cannot be read off a model's
  template. ADR-0093, #1662.
