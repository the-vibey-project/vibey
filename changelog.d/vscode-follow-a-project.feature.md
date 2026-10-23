* **The chat now narrates a running project:** after `/new`, `/reply` or `/resume`, krypton follows the project and tells
  you each phase it enters, any job that fails, when no worker is running it, and the moment it needs you or is done,
  so a conversation drives a project to completion. `/follow` watches again; `vibey.followPollSeconds` and
  `vibey.followMinutes` tune it. `/pause` now stops only that project's worker, and the commands work over a paired hub.
