---
description: See when vibey rests from sundown Friday to sundown Saturday, where it thinks your machine is, and how to run one command through the rest when you must.
---

# The Sabbath: see when vibey rests, and work through it when you must

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** From sundown Friday to sundown Saturday, where your machine
> stands, vibey starts no new work, merges nothing and ships nothing (sub-doctrine 8.i). Run
> `vibey sabbath` to see when the next rest ends. Nothing is lost: queued jobs wait, and at
> sundown Saturday everything restarts by itself. To run one command through the rest, add
> `--ignore-sabbath`. Reading this page takes five minutes.

## The lesson

It was a Friday afternoon, and the light through the Professor's window had already turned
orange, when Daniel looked up from a failed command.

**Daniel:** Professor, `vibey new` just refused me. Exit code 75. Did I break something?

**Professor Feynman:** You broke nothing. Think of a shop that closes from sundown Friday to
sundown Saturday. The door is locked, but the stock is still on the shelves and the orders
still sit in the tray. On Saturday evening the shopkeeper opens up and carries on where he
stopped.

**Daniel:** So the jobs in the queue just wait?

**Professor Feynman:** They wait where they are. Nothing fails. The workers stop taking new
jobs, and commands that would start work say no, politely, and tell you when the rest ends.
Commands that only look, like `vibey status` and `vibey doctor`, still answer.

**Daniel:** Whose sundown, though? Mine or the server's?

**Professor Feynman:** The machine's. vibey works out sunset for the place where the computer
stands, on that exact day, with the same method the US weather service uses. A laptop that
flies to Tokyo keeps Tokyo's Sabbath.

**Daniel:** And if it does not know where it is?

**Professor Feynman:** Then it guesses from your time zone's main city and widens the rest by
90 minutes on each edge, to be safe. It never looks you up on the internet.

Daniel thought about the queue.

**Daniel:** How does anything know it should start again?

**Professor Feynman:** The heartbeat keeps beating the whole time. Each beat says "resting
until Saturday sundown". The first beat after sundown restarts the held merge train, the
promotion, and any long job you asked to be woken. That is where the shop picture stops
working: a shopkeeper has to walk back in, and vibey does not.

## Do it

Checked on macOS with vibey-engine 0.4.0 on 2026-11-24.

1. See where vibey thinks you are and when the rest ends.

   ```bash
   vibey sabbath
   ```

   You should see four lines. On the machine this page was checked on, with no location set
   and no location service installed, it printed (the zone line is left out here):

   ```text
   sabbath: enabled
   location: time zone America/New_York reference city (zone.tab) (40.71, -74.01; about 500 km, coarse)
   next rest ends: 2026-11-28T18:00:10.787711-05:00
   ```

   `coarse` means vibey only knows your time zone's main city, so the rest is widened.
   `vibey-gh sabbath status` prints the same window as the merge train and promotion see it.

2. Optional: give vibey your real location, so the rest is exact. Put it in this machine's own
   `vibey.toml`, or in `~/.config/vibey/sabbath.toml`. **Never commit it.**

   ```toml
   [sabbath]
   latitude  = 34.97    # EXAMPLE only
   longitude = -82.44
   ```

   Run `vibey sabbath` again. The location line now names your override and no longer says
   `coarse`.

3. Optional: ask for a long job of your own to be restarted after the rest.

   ```bash
   vibey-gh sabbath register-lane --name docs-batch --cwd ~/work/docs -- ./run-batch.sh
   ```

   At sundown on Saturday the heartbeat runs `./run-batch.sh` in `~/work/docs`. When it
   succeeds the lane is forgotten; when it fails, the heartbeat tries again on the next beat.

## Daniel's teach-back

**Daniel:** From sundown Friday to sundown Saturday, worked out for wherever the computer is,
vibey takes no new work and merges nothing, but nothing is thrown away. Commands that would
start work stop with exit 75 and say when the rest ends. The heartbeat keeps running, so the
first beat after sundown restarts what was held. If vibey does not know where I am, it uses my
time zone's city and rests longer to be safe. If I truly must, `--ignore-sabbath` runs one
command through it.

**Professor Feynman:** Exactly right. One addition: `--ignore-sabbath` is for that one command
only, and no file can switch it on for you.

## What happens during the rest

- **Sundown is worked out for your machine.** vibey calculates sunset where the computer is,
  for that exact day, with the NOAA sunset method (solar zenith 90.833 degrees).
- **Workers stop taking jobs.** Jobs already in the queue wait where they are. Nothing fails
  and nothing is lost.
- **Commands that would start work say no, politely.** `vibey new` and `vibey work` say it is
  the Sabbath and when it ends, then stop with exit code 75 (`EX_TEMPFAIL`, "try again
  later"). Commands that only read, such as `vibey status`, `vibey doctor` and
  `vibey sabbath`, still work.
- **The merge train and the promotion hold.** Their runs say "held for the Sabbath
  (sub-doctrine 8.i): the window opened ... and resumes ..." and finish green: paused, not
  failed.
- **The heartbeat keeps beating.** It writes "resting until <Saturday sundown>" every time,
  so anything watching sees that vibey is resting, not dead.
- **At sundown on Saturday it wakes up.** The first heartbeat after sundown records that the
  Sabbath has ended, starts the held merge train and promotion again (unless
  `resume_dispatch = false`), and restarts every lane that was registered.
  `vibey-gh sabbath resume --dispatch` does the same by hand.

## Where does vibey think I am?

`vibey sabbath` (or `vibey-gh sabbath status`) shows the zone, where the location came from,
how accurate it is, and when the current or next rest ends. vibey looks, in this order:

1. **Your own setting**, if you gave one (most accurate): `latitude` and `longitude` in this
   machine's `vibey.toml`, in the per-host file named by `local_config`
   (`~/.config/vibey/sabbath.toml` by default), or in `VIBEY_SABBATH_LATITUDE` and
   `VIBEY_SABBATH_LONGITUDE`. Never commit coordinates.
2. **Your computer's location service**, if it is installed and allowed: CoreLocation on a Mac
   (through the small `CoreLocationCLI` helper) or GeoClue on Linux (its `where-am-i` agent).
3. **Your time zone's main city**, read from your computer's own time-zone table
   (`zone1970.tab`, or `zone.tab`). This needs no internet, but it can be tens of minutes off:
   every clock in `America/New_York` uses New York City's sunset. So vibey starts the rest
   earlier and ends it later, by 90 minutes unless you change `coarse_margin_minutes`.

vibey never looks up your location over the internet. It keeps the answer for a week, and
drops it at once if your time zone changes. If it cannot place your machine at all,
`vibey doctor` says FAIL and the fixed times apply: Friday 14:00 to Saturday 23:00 local,
widened. The code is
[`vibey_gh/sabbath_location.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/sabbath_location.py).

## Turning it off for one run

`VIBEY_SABBATH_ENABLED=false` (also `0`, `no`, `off`) switches the rest off for that process
only, without touching any file. Automated checks use this: the Helm cluster-smoke step in CI
sets it so `vibey new` does not decline on a Friday evening. Turning it off anywhere else is a
declared act (prefer `enabled = false` in the file), never a missing key.

For a single command, `--ignore-sabbath` on `vibey new`, `vibey work` and `vibey worker` runs it
through a window that would have rested it. It is the operator's choice for that one command
and nothing more: no `vibey.toml` key can supply it, so a file cannot switch the Sabbath off for
a run nobody is watching. When a window would have held, the command says so on stderr, naming
when the rest would have ended; outside a window it is silent. `vibey worker --ignore-sabbath`
claims jobs through the window for as long as that worker runs, and a worker started without
the flag still rests.

## Settings

The `[sabbath]` table is read from your local `vibey.toml` by the engine, and from
`.vibey-gh.toml` by the merge train, the promotion and the heartbeat. The full reference is
[`[sabbath]`](../reference/configuration.md#sabbath).

| Key | Default | What it does |
|---|---|---|
| `enabled` | `true` | Turning it off is a declared act, never a missing key. |
| `timezone` | `""` | The zone the civil day is read in; empty reads the host's own zone. |
| `latitude`, `longitude` | unset | An exact location. Set both or neither, never in a committed file. |
| `local_config` | `~/.config/vibey/sabbath.toml` | A per-host file with `latitude` and `longitude`. |
| `location_service` | `true` | Ask CoreLocation or GeoClue when installed. |
| `offset_minutes` | `0` | Widens every window toward rest, both edges (0 to 240). Never narrows. |
| `coarse_margin_minutes` | `90` | Extra widening when only the zone's city is known (0 to 240). |
| `fallback_opens`, `fallback_closes` | `"14:00"`, `"23:00"` | Friday open and Saturday close when no sundown can be computed. |
| `resume_dispatch` | `true` | Restart the held merge train and promotion at the first beat after the rest. |
| `lanes_dir` | `~/.local/state/vibey/sabbath-lanes` | Where registered lanes are kept. |

This repository's own `.vibey-gh.toml` declares `enabled = false` for its merge train,
promotion and heartbeat (checked 2026-11-24, set in #1244). That file governs this repository's
automation only; your own `vibey.toml` governs your engine.

The design and its reasons are in
[ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `vibey new` or `vibey work` exits 75 and names when the rest ends | The Sabbath is in force where this machine stands. | Wait, or run that one command with `--ignore-sabbath`. |
| `vibey sabbath` says `coarse` | vibey only knows your time zone's main city, so the rest is widened. | Set `latitude` and `longitude` in this machine's `vibey.toml` or `~/.config/vibey/sabbath.toml`. |
| `vibey doctor` prints `sabbath  FAIL: no location source answered` | vibey could not place the machine at all, so the fixed Friday 14:00 to Saturday 23:00 window applies. | Set `latitude` and `longitude` in this machine's `vibey.toml`, or install CoreLocationCLI (macOS) or GeoClue (Linux). |
| A CI job running `vibey new` fails every Friday evening | The job hits the rest like any other caller. | Set `VIBEY_SABBATH_ENABLED=false` for that one process, as the cluster-smoke step does. |
| A registered lane did not restart | Its resume command failed. | The heartbeat retries on the next beat; run the command by hand to see why it fails. |

## Where next

- [`[sabbath]` in the configuration reference](../reference/configuration.md#sabbath), for every
  key and the environment overrides.
- [ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md), for
  why the rest follows the machine and never the operator's home.
- [The CLI reference for `vibey sabbath`](../reference/cli.md), for the exact help text.

## Say it in one line

vibey rests from sundown Friday to sundown Saturday where the machine stands, loses nothing,
wakes by itself, and lets you run one command through with `--ignore-sabbath`.
