---
name: weather-monitor
description: Track weather changes for a single location and detect escalation.
metadata:
  hermes:
    tags: [Weather, Monitor, Intelligence, Escalation]
version: 0.1.0
author: Hermes
---

# Weather Monitor

Tracks weather state for a **single location** over time and detects escalation events. Does NOT pull data itself (delegates to `weather-pull`). Does NOT send emails (delegates to `weather-email-trigger`). Just maintains state and decides if the situation changed.

## When to Use

- Scheduled cron / heartbeat wants to know "did the weather get worse since last check?".
- Another skill needs a stable ID like `current_level: watch|warning|emergency|none` without re-implementing the logic.
- Pre-flight check before `weather-email-send` fires — confirms escalation is real.

## Scope

- **Single home location at a time.** Driven by `HOME_LAT` / `HOME_LON` / `HOME_COUNTY` env vars.
- **Never auto-expand scope.** If the user asks for another city, that's a separate run — don't poll that city for this skill.

## Prerequisites

- `weather-pull` must be runnable (returns the structured data this skill consumes).
- State file at `~/.openclaw/workspace/state/weather-<HOME_ZIP>.json` (write with `write_file`, read with `read_file`).

## How to Run

Invoke through `terminal` + `read_file`/`write_file`. State updates happen every run. Caller decides polling cadence (the skill itself has no clock).

## Quick Reference

- State path: `~/.openclaw/workspace/state/weather-<HOME_ZIP>.json`
- Escalation levels (low → high): `none` < `watch` < `warning` < `emergency`
- SPC categories (low → high): TSTM < MRGL < SLGT < ENH < MDT < HIGH
- NWS alert severities: Extreme > Severe > Moderate > Minor > Unknown

## Procedure

1. **Call `weather-pull`** through the terminal tool. Get the structured summary.

2. **Read prior state** through `read_file`:
   ```
   path: ~/.openclaw/workspace/state/weather-<HOME_ZIP>.json
   ```

3. **Compute current escalation level** from the fresh data:
   - `emergency` — Tornado Warning, Flash Flood Emergency, or SPC HIGH in active alerts.
   - `warning` — Severe Thunderstorm Warning, Flash Flood Warning, or SPC MDT.
   - `watch` — Tornado Watch, Severe Thunderstorm Watch, or SPC ENH/SLGT in the day's outlook for the county.
   - `none` — no alerts, MRGL or below, no imminent threat.

4. **Compare to prior state.** If `current > prior`, that's an ESCALATION. If `current < prior`, that's a DE-ESCALATION. If equal, no change.

5. **Build event records** for any changes:
   - `{event_type: escalation|de_escalation, from: <prior>, to: <current>, at: <utc_iso>, headline: <nws headline>, area: <HOME_COUNTY>}`

6. **Append events** to the state file's `events[]` array (cap at 50 most recent to avoid unbounded growth).

7. **Write state file** through `write_file`:
   ```json
   {
     "last_checked_utc": "2026-07-09T15:50:00Z",
     "current_level": "watch",
     "spc_day1_categorical": "ENH",
     "active_alert_count": 1,
     "events": [
       {"event_type": "escalation", "from": "none", "to": "watch", "at": "...", "headline": "...", "area": "<HOME_COUNTY>"}
     ],
     "last_pulled_data": { /* the full weather-pull summary */ }
   }
   ```

8. **Return** to caller:
   - `level`: current level
   - `changed`: bool
   - `change`: the event record if changed, else null
   - `prior_level`: what it was before this run
   - `recommended_action`: text hint for the email-trigger skill (e.g. "fire level 2 urgent update" or "stay silent")

## Pitfalls

- **Don't compare alert counts; compare levels.** A new Severe Thunderstorm Warning replacing a Tornado Watch is a DE-ESCALATION in our ladder, not an escalation — both are `warning` level. Trust the level, not the count.
- **SPC outlooks are FORECAST, not active alerts.** Day 1 HIGH = high risk forecast for the day, not an emergency NOW. Map SPC categories to `watch` unless an active warning is also present.
- **Time zones.** NWS API returns UTC; SPC products use Central Time; local news uses ET. Always normalize to UTC for state storage. Display in local time for humans.
- **State file must be writable.** If the path doesn't exist, the run with `write_file` (which creates parents) is fine. If a permission error, surface it — don't silently no-op.
- **Don't conflate "active alert for county" with "alert for the polygon that includes home."** Tornado Warnings are polygon-based. Check if the geometry contains the home lat/lon, not just the county name.

## Verification

```bash
python -c "
import json, os
zip = os.getenv('HOME_ZIP', '00000')
p = os.path.expanduser(f'~/.openclaw/workspace/state/weather-{zip}.json')
if os.path.exists(p):
    d = json.loads(open(p).read())
    print('OK level:', d.get('current_level'), 'events:', len(d.get('events', [])))
else:
    print('NO STATE FILE — run the skill first')
"
```

Expected: `OK level: <none|watch|warning|emergency> events: <N>`. If `NO STATE FILE`, run the procedure once. If `events` is 0, no escalation has been detected yet — that's fine for quiet days.