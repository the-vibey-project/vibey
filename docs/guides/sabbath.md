# The Sabbath

From sundown on Friday to sundown on Saturday, vibey rests. It writes no code, merges
nothing and ships nothing. This is sub-doctrine 8.i. The heartbeat keeps going the whole
time, so at sundown on Saturday everything starts again by itself.

## What happens, in plain words

- **Sundown is worked out for your machine.** vibey calculates the time the sun sets where
  the computer is, for that exact day. It uses the same method as the US weather service's
  (NOAA's) sunset calculator.
- **Workers stop taking jobs.** Jobs already in the queue wait where they are. Nothing
  fails and nothing is lost.
- **Commands that would start work say no, politely.** `vibey new` and `vibey work` tell
  you it is the Sabbath and when it ends, then stop with exit code 75 ("try again later").
  Commands that only read, like `vibey status` and `vibey doctor`, still work.
- **The merge train and the promotion hold.** Their runs say "held for the Sabbath until
  ..." on the run page and finish green: paused, not failed.
- **The heartbeat keeps beating.** It writes "resting until <Saturday sundown>" every time,
  so anything watching sees that vibey is resting, not dead.
- **At sundown on Saturday it wakes up.** The first heartbeat after sundown records that
  the Sabbath has ended. It starts the held merge train and promotion again, and restarts
  every lane that was paused.

## Where does vibey think I am?

Run `vibey sabbath` (or `vibey-gh sabbath status`). It shows the zone, where the location
came from, how accurate it is, and when the current or next rest ends. vibey looks, in this
order:

1. **Your own setting**, if you gave one (most accurate). Put it in this machine's
   `vibey.toml`. **Never commit it:**

   ```toml
   [sabbath]
   latitude  = 34.97    # EXAMPLE only
   longitude = -82.44
   ```

2. **Your computer's location service**, if it is installed and allowed: CoreLocation on a
   Mac (through the small `CoreLocationCLI` helper) or GeoClue on Linux.
3. **Your time zone's main city**, read from your computer's own time-zone files. This
   needs no internet, but it can be tens of minutes off. For example, every clock in
   `America/New_York` would use New York City's sunset. So vibey starts the rest earlier
   and ends it later, by 45 minutes unless you change it, to be safe.

vibey never looks up your location over the internet. It checks again every week, and at
once if your time zone changes. If it cannot place your machine at all, `vibey doctor` says
FAIL and the fixed times apply: Friday 18:00 to Saturday 19:00 local, widened.

## Pausing a lane so it restarts by itself

A long job you run yourself (a "lane") can ask to be restarted after the Sabbath:

```bash
vibey-gh sabbath register-lane --name docs-batch --cwd ~/work/docs -- ./run-batch.sh
```

At sundown on Saturday the heartbeat runs `./run-batch.sh` in `~/work/docs`. When it
succeeds, the lane is forgotten. If it fails, the heartbeat tries again on the next beat.

## Settings

All the keys are in [`[sabbath]`](../reference/configuration.md#sabbath). The design and
its reasons are in
[ADR-0070](../architecture/decisions/0070-the-sabbath-kept-where-the-machine-stands.md).
