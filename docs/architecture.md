# Architecture

## System Overview

The Intelligence Stack is a **multi-domain** alerting pipeline. Each domain (weather, DEFCON, seismic, civic, ...) follows the same 4-skill chain:

```
┌────────────────────────────────────────────────────────────────────────┐
│                       INTELLIGENCE STACK                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  WEATHER DOMAIN                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ weather-pull │ -> │weather-monitor│ -> │weather-email-│              │
│  │              │    │              │    │  trigger     │              │
│  │ • NWS        │    │ • State file │    │ • Scope      │              │
│  │ • SPC        │    │ • Escalation │    │ • Cooldown   │              │
│  │ • FEMA       │    │ • Events     │    │ • Level map  │              │
│  │ • Radar      │    │              │    │              │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  weather-email-send (4-level ladder, inline CSS)         │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                        │
│  DEFCON DOMAIN                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ defcon-pull  │ -> │defcon-monitor│ -> │defcon-email- │              │
│  │              │    │  -email      │    │  trigger     │              │
│  │ • State file │    │ • Escalation │    │ • Transition │              │
│  │ • ClawdWatch │    │ • 6h cooldown│    │ • DEFCON 1 = │              │
│  │ • Web        │    │ • DEFCON 1/2 │    │   op confirm │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  defcon-email-send (2-level ladder, action list, repo     │         │
│  │  links in footer)                                         │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                        │
│  INBOX HEALTH (separate, runs daily)                                   │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  agentmail-daily-healthcheck (anti-injection rules)       │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Per Tick

Both domains share the same flow. Here's the DEFCON example:

```
1. CRON FIRES (every 15 min)
        │
        ▼
2. defcon-pull
   - Reads DEFCON_STATE_PATH (env var)
   - Tries ClawdWatch at localhost:3444
   - Falls back to web_extract on defconlevel.com
   - Returns: {level, threat_score, active_threats, per_domain_scores, ...}
        │
        ▼
3. defcon-monitor-email
   - Reads prior state from ~/.openclaw/workspace/state/defcon-email.json
   - Computes current_alert_level from the pulled data
   - Compares to prior (escalation vs de-escalation vs no change)
   - Appends events if changed
   - Writes updated state
   - Returns: {alert_level, defcon_level, changed, recommended_action}
        │
        ▼
4. defcon-email-trigger (only if changed AND transition to 1/2)
   - Checks trigger filter (must be transition TO 1 or 2)
   - Checks 6-hour cooldown
   - Maps alert_level → email level (level_2_high or level_1_emergency)
   - Returns decision: {fire, level, requires_confirmation}
        │
        ▼
5. defcon-email-send (only if fire=true and not requires_confirmation)
   - Loads HTML + plain-text template for the chosen level
   - Substitutes live values
   - Dry-run check (DEFCON_DRY_RUN=1)
   - Sends via AgentMail SDK to all DEFCON_ALERT_RECIPIENTS
   - Returns message_ids
        │
        ▼
6. STATE UPDATED with last_email = {level, at_utc, message_ids}
```

The weather pipeline is structurally identical, with these differences:
- Geographic scope filter (only fires for home county/zone)
- 4-level ladder instead of 2
- 30-min cooldown (more frequent than DEFCON's 6 hours)
- DEFCON 1-equivalent is weather level 4 (WAKE-UP CALL)

## Skill Contracts

Each skill exposes one JSON-shaped contract.

### DEFCON Domain

#### `defcon-pull` output

```json
{
  "level": 2,
  "level_label": "HIGH",
  "threat_score": 78,
  "last_updated_utc": "2026-07-09T15:50:00Z",
  "source": "state_file",
  "active_threats": [
    {"id": "geopol-2026-07", "category": "geopolitical", "description": "...", "level": 2, "severity": "HIGH"}
  ],
  "per_domain_scores": {
    "geopolitical": {"value": 18, "max": 20, "detail": "..."},
    "cyber": {"value": 12, "max": 15, "detail": "..."}
  },
  "escalation_signal": "high",
  "sources_ok": ["state_file", "clawdwatch"]
}
```

#### `defcon-monitor-email` output

```json
{
  "alert_level": "high",
  "defcon_level": 2,
  "changed": true,
  "change": {"event_type": "escalation", "from": "none", "to": "high", "at": "...", "headline": "..."},
  "prior_alert_level": "none",
  "recommended_action": "fire level_2_high"
}
```

#### `defcon-email-trigger` output

```json
{
  "fire": true,
  "level": "level_2_high",
  "defcon_level": 2,
  "requires_confirmation": false,
  "subject_hint": "DEFCON 2 ALERT: High Threat Level — Action Required",
  "body_data": {"headline": "...", "threat_score": 78, "active_threats": [...], ...},
  "reason": "escalation to DEFCON 2, transition detected, cooldown OK"
}
```

#### `defcon-email-send` output

```json
{
  "sent_count": 3,
  "message_ids": ["<am-001>", "<am-002>", "<am-003>"],
  "level": "level_2_high"
}
```

### Weather Domain (Reference)

#### `weather-pull` output

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

#### `weather-monitor` output

```json
{
  "level": "emergency",
  "prior_level": "warning",
  "changed": true,
  "change": {"event_type": "escalation", "from": "warning", "to": "emergency", "at": "...", "headline": "..."},
  "recommended_action": "fire level 3 storm alert"
}
```

#### `weather-email-trigger` output

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

#### `weather-email-send` output

```json
{
  "sent_count": 3,
  "message_ids": ["<am-001>", "<am-002>", "<am-003>"],
  "level": 3
}
```

## State File Schemas

### DEFCON state

`~/.openclaw/workspace/state/defcon-email.json`:

```json
{
  "last_checked_utc": "2026-07-09T15:50:00Z",
  "current_alert_level": "high",
  "current_defcon_level": 2,
  "threat_score": 78,
  "escalation_signal": "high",
  "active_threats_count": 4,
  "events": [
    {
      "event_type": "escalation",
      "from": "none",
      "to": "high",
      "at": "2026-07-09T15:50:00Z",
      "headline": "Composite score crossed threshold",
      "threats": ["..."]
    }
  ],
  "last_email": {
    "level": "level_2_high",
    "at_utc": "2026-07-09T15:50:00Z",
    "message_ids": ["<am-001>"]
  },
  "last_pulled_data": { /* full defcon-pull output */ }
}
```

### Weather state

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
| NWS API down (weather) | `sources_ok` excludes `nws_api` | Skip send. Alert operator via Telegram. |
| DEFCON state file missing | pull returns `null` | Skip send. Treat as `alert_level: none`. |
| ClawdWatch down | pull returns `state_file` only | Continue. State file is authoritative. |
| AgentMail API down | `send()` throws | Retry next cron tick. State unchanged. |
| State file corrupted | JSON parse error | Reset to `{"current_*: "none"}`. No email until next escalation. |
| Wrong home location in config (weather) | Scope filter rejects all alerts | Operator must fix `HOME_LAT/LON/COUNTY` env vars. |
| Recipient list empty | `send()` raises | Operator must set `ALERT_RECIPIENTS` (or `DEFCON_ALERT_RECIPIENTS`). No send. |
| DEFCON 1 false positive | Operator override required | Level 1 NEVER auto-fires — `requires_confirmation: true` gate prevents this. |