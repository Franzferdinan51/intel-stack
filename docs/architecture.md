# Architecture

## System Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                       INTELLIGENCE STACK                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ weather-pull │ -> │weather-monitor│ -> │weather-email-│              │
│  │              │    │              │    │  trigger     │              │
│  │ • NWS        │    │ • State file │    │ • Scope      │              │
│  │ • SPC        │    │ • Escalation │    │ • Cooldown   │              │
│  │ • FEMA       │    │ • Events     │    │ • Level map  │              │
│  │ • Radar      │    │              │    │              │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                      │
│         │  fresh data       │  state diff       │  decision            │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │              STATE FILE (JSON, on disk)                  │         │
│  │  ~/.openclaw/workspace/state/weather-<HOME_ZIP>.json     │         │
│  └──────────────────────────────────────────────────────────┘         │
│                              │                                         │
│                              ▼                                         │
│                    ┌──────────────────┐                                 │
│                    │ weather-email-   │                                 │
│                    │ send             │                                 │
│                    │ • HTML templates │                                 │
│                    │ • AgentMail SDK  │                                 │
│                    │ • Fan-out        │                                 │
│                    └────────┬─────────┘                                 │
│                             │                                           │
│                             ▼                                           │
│              ┌─────────────────────────────┐                            │
│              │  ALERT FAN-OUT              │                            │
│              │  • AGENTMAIL_INBOX (sender) │                            │
│              │  • ALERT_RECIPIENTS (list)  │                            │
│              │  • Telegram Home (heads-up) │                            │
│              └─────────────────────────────┘                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Per Tick

```
1. CRON FIRES (every 15 min during active weather, every 60 min otherwise)
        │
        ▼
2. weather-pull
   - Reads HOME_LAT / HOME_LON from env
   - Hits NWS API, SPC, FEMA, radar
   - Returns: {current, forecast_7day, active_alerts, spc_day1, ...}
        │
        ▼
3. weather-monitor
   - Reads prior state from ~/.openclaw/workspace/state/weather-<ZIP>.json
   - Computes current_level from the pulled data
   - Compares to prior_level
   - Appends events if changed
   - Writes updated state
   - Returns: {level, changed, change, recommended_action}
        │
        ▼
4. weather-email-trigger (only if changed or forced)
   - Checks geographic scope: is the alert for HOME_COUNTY?
   - Checks cooldowns: was an email sent recently at this level?
   - Maps monitor level → email level (1/2/3/4)
   - Returns decision: {fire, level, requires_confirmation, body_data}
        │
        ▼
5. weather-email-send (only if fire=true and not requires_confirmation)
   - Loads HTML + plain-text template for the chosen level
   - Substitutes live values
   - Dry-run check (default)
   - Sends via AgentMail SDK to all ALERT_RECIPIENTS
   - Returns message_ids
        │
        ▼
6. STATE UPDATED with last_email = {level, at_utc, message_ids}
```

## Skill Contracts

Each skill exposes one JSON-shaped contract:

### `weather-pull` output

```json
{
  "current": {"temp_f": 69, "wind_mph": 37, "humidity_pct": 90, "pressure_mb": 1002, "conditions": "Light Rain"},
  "forecast_7day": ["...", "..."],
  "active_alerts": [{"event": "Tornado Warning", "severity": "Extreme", "expires": "...", "headline": "..."}],
  "spc_day1": {"categorical": "MDT", "tornado_prob": 15, "wind_prob": 45, "hail_prob": 30},
  "afd_discussion": "...",
  "fema_ipaws": [],
  "local": "...",
  "escalation_signal": "emergency",
  "pulled_at": "2026-07-09T15:50:00Z",
  "sources_ok": ["nws_api", "nws_point", "spc_day1", "radar"]
}
```

### `weather-monitor` output

```json
{
  "level": "emergency",
  "prior_level": "warning",
  "changed": true,
  "change": {"event_type": "escalation", "from": "warning", "to": "emergency", "at": "...", "headline": "..."},
  "recommended_action": "fire level 3 storm alert"
}
```

### `weather-email-trigger` output

```json
{
  "fire": true,
  "level": 3,
  "level_name": "storm_alert",
  "requires_confirmation": false,
  "subject_hint": "Storm Alert: <Area> - Tonight 9 PM-Midnight - ...",
  "body_data": {"headline": "...", "area": "<HOME_COUNTY>", ...},
  "reason": "escalation warning -> emergency, in-scope, cooldown OK"
}
```

### `weather-email-send` output

```json
{
  "sent_count": 3,
  "message_ids": ["<am-001>", "<am-002>", "<am-003>"],
  "level": 3
}
```

## State File Schema

`~/.openclaw/workspace/state/weather-<HOME_ZIP>.json`:

```json
{
  "last_checked_utc": "2026-07-09T15:50:00Z",
  "current_level": "emergency",
  "spc_day1_categorical": "MDT",
  "active_alert_count": 1,
  "events": [
    {
      "event_type": "escalation",
      "from": "warning",
      "to": "emergency",
      "at": "2026-07-09T15:50:00Z",
      "headline": "Tornado Warning issued",
      "area": "Montgomery County, OH"
    }
  ],
  "last_email": {
    "level": 3,
    "at_utc": "2026-07-09T15:48:00Z",
    "message_ids": ["<am-001>"]
  },
  "last_pulled_data": { /* full weather-pull output */ }
}
```

## Failure Modes

| Failure | Detection | Recovery |
|---|---|---|
| NWS API down | `sources_ok` excludes `nws_api` | Skip send. Alert operator via Telegram. |
| AgentMail API down | `send()` throws | Retry next cron tick. State unchanged. |
| State file corrupted | JSON parse error | Reset to `{"current_level": "none"}`. No email until next escalation. |
| Wrong home location in config | Scope filter rejects all alerts | Operator must fix `HOME_LAT/LON/COUNTY` env vars. |
| Recipient list empty | `send()` raises | Operator must set `ALERT_RECIPIENTS`. No send. |