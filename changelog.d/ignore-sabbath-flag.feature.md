* **`--ignore-sabbath`:** `vibey new`, `vibey work` and `vibey worker` take a flag that runs
  that one command through the Sabbath window (sub-doctrine 8.i), which would otherwise
  decline with exit 75 or leave the worker claiming nothing. It is the operator's choice
  for one command and is never stored: there is no `vibey.toml` key for it. When a window
  would have held, the command says so on stderr and names when the rest would have ended.
  Before, the only way through was `VIBEY_SABBATH_ENABLED=0`, which switches the check off
  silently for a whole shell.
