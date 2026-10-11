* **`VIBEY_OLLAMA_TEMPERATURE`:** the sovereign DESIGN and DECOMPOSE client always sampled at
  temperature 0, so every attempt of a job that failed was the same request and failed the same
  way: a `build.decompose` whose plan was rejected (verification ran a script a later item
  creates) used all seven attempts on the same two plans, and granting more would have repeated
  them. The setting (`0` to `2`, default `0`, so nothing changes unless set) lets an operator
  make attempts differ. A bad value exits 2 before any engine starts.
