---
name: weather-email-trigger
description: Decide if a weather email should fire for a single home location.
metadata:
  hermes:
    tags: [Weather, Email, Trigger, Intelligence, Scope]
version: 0.1.0
author: Hermes
---

# Weather Email Trigger

Gatekeeper between `weather-monitor` (which detects escalation) and `weather-email-send` (which sends the actual email). Decides IF and WHEN an email should fire for the configured home location. Does NOT pull data, does NOT send emails itself — just the routing decision.

## When to Use

- After a `weather-monitor` run returns `changed: true`.
- Cron / heartbeat asks "should we send an email right now?"
- Operator says "send an update" and the skill picks the right level.

## Scope — STRICT Geographic Filter

- ✅ **ALWAYS fire** for: the home lat/lon, the home county, the home NWS forecast office area.
- ✅ **Fire** for adjacent areas ONLY if the alert polygon or NWS area description **explicitly contains** the home county, ZIP, or city name.
- ❌ **NEVER fire** for: cities the operator didn't ask about — even if the alert mentions them.
- ❌ **NEVER fire** for other states, even nearby ones, unless the polygon overlaps the home point.
- ❌ **NEVER auto-fire** based on the operator mentioning a city in conversation. They can ask for info on another city without that triggering an email blast.

## Prerequisites

- `weather-monitor` state file: `~/.openclaw/workspace/state/weather-<HOME_ZIP>.json`
- `weather-email-send` skill loaded for the actual send.
- Operator confirmation channel: configured chat platform or email.

## How to Run

Invoke through `terminal` + `read_file`. Returns a decision object; caller (orchestrator or human) does the actual send.

## Quick Reference

- Email levels: `1_weather_watch` < `2_urgent_update` < `3_storm_alert` < `4_wake_up_call`
- Mapping from monitor level → email level:
  - `none` → no email
  - `watch` → level 1 (Weather Watch) — only on ESCALATION
  - `warning` → level 2 (URGENT UPDATE) — fire immediately
  - `emergency` → level 3 (Storm Alert) AND consider level 4 (WAKE-UP CALL) if local hour is 22:00-04:00
- Cooldown (env-driven): `COOLDOWN_SAME_LEVEL` minutes between emails at the same level; `COOLDOWN_ESCALATION` minutes between escalations.
- Recipients are owned by `weather-email-send` (configurable list). Do NOT redefine here.

## Procedure

1. **Read monitor state** through `read_file`:
   ```
   path: ~/.openclaw/workspace/state/weather-<HOME_ZIP>.json
   ```

2. **Check the geographic scope filter.** If the `last_pulled_data.active_alerts[].areaDesc` does NOT include the home county/ZIP/city name, return `{fire: false, reason: "out_of_scope"}`.

3. **Check prior sends** in the state file's `last_email` field:
   ```json
   "last_email": {"level": 2, "at_utc": "2026-07-09T15:30:00Z"}
   ```
   If `now - last_email.at_utc < cooldown_for_level(level)`, return `{fire: false, reason: "cooldown"}`.

4. **Map monitor level to email level:**
   - `none` → no email, return `{fire: false, reason: "no_threat"}`
   - `watch` (escalation) → level 1
   - `warning` → level 2
   - `emergency` → level 3; if current local hour is between 22 and 04, also recommend level 4 follow-up

5. **Check operator confirmation policy:**
   - For level 1, 2: AUTO-fire is OK (operator pre-authorized these in the original handoff).
   - For level 3 (Storm Alert): AUTO-fire is OK but ALSO push a heads-up to the operator channel before sending.
   - For level 4 (WAKE-UP CALL): NEVER auto-fire. Return `{fire: true, requires_confirmation: true}` and wait for explicit `go`.

6. **Build the decision object:**
   ```json
   {
     "fire": true,
     "level": 2,
     "level_name": "urgent_update",
     "requires_confirmation": false,
     "subject_hint": "URGENT UPDATE: Level 4 of 5 - <Day> <Date> Severe Storm Threat - <Home Area>",
     "body_data": {
       "headline": "<nws headline>",
       "area": "<HOME_COUNTY>",
       "spc_categorical": "MDT",
       "active_alerts": [...],
       "current_conditions": {...}
     },
     "reason": "escalation to warning, in-scope, cooldown OK"
   }
   ```

7. **Update monitor state** with `last_email` so the cooldown logic works next run:
   ```json
   "last_email": {"level": 2, "at_utc": "<now>"}
   ```
   Write back with `write_file`.

8. **Return the decision.** Caller (human or orchestrator) hands it to `weather-email-send` to send.

## Pitfalls

- **Geographic scope is the #1 trap.** The operator may live-chat about another city's weather without wanting an email blast. This skill MUST refuse out-of-area requests.
- **Cooldown applies per LEVEL.** A level 2 fire doesn't block a level 4 escalation 5 min later — that's a real escalation and should fire.
- **Levels are not monotonic in time.** A watch at 6 PM, warning at 9 PM, watch again at 11 PM (warning expires) is normal. Don't treat back-to-watch as a regression event.
- **Don't redefine the recipient list.** It's owned by `weather-email-send` and the `ALERT_RECIPIENTS` env var. This skill only decides IF/WHEN/WHICH level.
- **Operator can always force-fire.** If the operator says "send it now", skip the cooldown and confirmation gates. Trust the human over the rules.
- **Don't fire on FIRST run with no prior state.** If the state file doesn't exist or has no `current_level`, treat it as `none` and don't fire — wait for the next escalation.

## Verification

```bash
python -c "
import json, os
zip = os.getenv('HOME_ZIP', '00000')
p = os.path.expanduser(f'~/.openclaw/workspace/state/weather-{zip}.json')
if not os.path.exists(p):
    print('NO STATE — run weather-monitor first')
else:
    d = json.loads(open(p).read())
    print('current:', d.get('current_level'), '| last_email:', d.get('last_email'))
"
```

Expected: prints `current: <level> | last_email: <dict or None>`. If `current` is `none`, no email will fire — that's the right answer for a quiet day. If `current` is `warning` or `emergency` and `last_email` is None or old, the next cron tick will fire.