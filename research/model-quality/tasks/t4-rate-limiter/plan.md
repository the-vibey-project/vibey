Refactor limiter.py so its state is no longer module-level globals. Behaviour must not change:
every existing call to the module-level functions must give exactly the results it gives today,
including edge cases (window boundaries, rejected hits, configure on a limiter that already has hits).

1. Add a class RateLimiter to limiter.py with the constructor RateLimiter(limit: int = 3,
   window: float = 60.0). It validates its arguments exactly as configure does today (ValueError).
   Its methods are configure(limit, window), allow(key, now) -> bool, remaining(key, now) -> int
   and reset(key=None), with the same semantics as the functions of the same names today.
2. Every instance has its own state: two RateLimiter objects must never see each other's hits or
   settings.
3. Add a module-level DEFAULT_LIMITER = RateLimiter(). The module-level functions configure, allow,
   remaining and reset keep their names and signatures and now delegate to DEFAULT_LIMITER.
4. No mutable module-level state other than DEFAULT_LIMITER may remain.

Keep the existing tests in test_limiter.py passing. Run them with `python -m pytest -q`, and fix
anything until they pass. Then finish.
