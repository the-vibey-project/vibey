* **`vibey llm tail` shows every phase, and follows each new session by itself:** the tail
  followed only the sovereign DESIGN and DECOMPOSE calls, so it went quiet exactly when BUILD
  began, an hour into a run. The worker now notes each engine session in the wire log (a
  `session` record naming that run's `events.jsonl`; ids and paths only), and the tail follows
  the newest one: every tool call and a one-line result (a failing shell command shows the tail
  of its output), the streamed answer, the model's reasoning, and each turn's time and tokens.
  When a new run starts, it switches to it by itself, finishing the old one first. The runner
  now records each turn's reasoning as an event (capped at 4000 characters), which it had only
  counted. Nothing changes unless the wire log is on (`-vvv` or `VIBEY_LLM_WIRE_LOG`).
