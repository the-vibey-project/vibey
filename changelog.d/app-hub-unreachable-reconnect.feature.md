* **The phone app says what to do when the hub is not running, and reconnects by itself (#1186):** instead of "Is
  `vibey serve` running", it explains that the hub on your computer is not running, shows `vibey hub start` with a Copy
  button, and notes that closing a krypton app never stops the hub. It asks `/health/live` again after 2, 4, 8 ... up to
  60 seconds (30 while the hub answers), only while the app is in front, loads the screen again when the hub answers, and
  shows reachable or not, the address and since when on Home and Doctor. A phone still cannot start or stop a hub: the
  hub API has no such route, and none was added.
