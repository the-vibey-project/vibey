* **engines:** a worker's shutdown no longer crashes on a session it cannot reap. #1297 made
  the worker end every live engine session on its way out, by awaiting a reap of each one
  in a process-wide registry; an entry registered under another event loop raised
  "Future attached to a different loop" and turned a clean exit into exit 1 (CI's `gates`
  job on develop, 2026-10-01). Shutdown now ends each session on its own: another loop's
  group is killed without being awaited, an entry with no process is reported
  (`engine_session_unreapable`), and a reap that fails is reported
  (`engine_session_end_failed`) while the rest still end. The adapter's tests now start
  and end with the registry empty, which is the leak that exposed it.
