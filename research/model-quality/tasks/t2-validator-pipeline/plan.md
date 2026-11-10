`signup/service.py` validates a `SignupForm` with a chain of inline `if` checks and stops at
the first problem. Replace this with a validator pipeline that reports every problem at once.

1. Create `signup/validation.py` containing:
   - `ValidatorPipeline` with `add(validator) -> ValidatorPipeline` (returns itself so calls can
     be chained) and `run(form) -> list[str]`. A validator is a function that takes a
     `SignupForm` and returns a list of error messages (empty when fine). `run` calls the
     validators in the order added and returns all their messages concatenated in that order.
   - Three validator functions `validate_username`, `validate_email`, `validate_age`.
   - `default_pipeline() -> ValidatorPipeline` returning a new pipeline with those three, in that
     order.
2. `validate_username` returns `"username must be 3-20 characters"` when the length is outside
   3..20, and separately `"username may only contain letters, digits and _"` when the name has
   any character that is not an ASCII letter, digit or underscore. Both can apply at once, in
   that order. (An empty username fails both.)
3. `validate_email` returns `["invalid email"]` unless there is exactly one `@`, with a non-empty
   part before it and a part after it that contains a `.` which is neither its first nor its
   last character.
4. `validate_age` returns `["age must be between 13 and 120"]` when the age is outside 13..120.
5. In `SignupService.register` (in `signup/service.py`) use `default_pipeline()`. If it reports
   any errors, raise `SignupError(errors)` with all of them and do not store the user. Only when
   validation passes, check for a taken username (compared case-insensitively) and raise
   `SignupError(["username already taken"])`. Otherwise register as before.
