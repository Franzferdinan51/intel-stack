# Workflows

Pre-built cron definitions and orchestrator scripts that drive the Intelligence Stack.

## Files

| File | Type | What it does |
|---|---|---|
| `cron-weather-watchdog.json` | Hermes cron | Runs 1x daily at 08:00. Pulls **broad weather patterns** (SPC Day 1-3, NWS AFD, 7-day forecast) for early heads-up. Posts a Telegram brief every day. Emails only fire on real escalation (active warning, SPC HIGH Day 1). Level 4 requires operator confirmation. |
| `cron-defcon-watchdog.json` | Hermes cron | Runs `defcon-pull → monitor-email → trigger → send` 3x daily (08:00, 14:00, 20:00). Emails only fire on transitions to DEFCON 2 or 1. DEFCON 1 requires operator confirmation. Always posts a one-line Telegram summary. |
| `agentmail-daily-healthcheck.json` | Hermes cron | Daily inbox sweep with anti-injection rules (does NOT download attachments) |
| `orchestrate_alert.py` | Python script | Single-shot pipeline runner for weather (manual operator trigger) |
| `alert-ladder.md` | Markdown ref | Visual 4-level weather + 2-level DEFCON escalation reference |

## Quick Setup

### 1. Wire the weather watchdog cron

```bash
# Hermes cron format: paste this into your cron jobs list
# Adjust the schedule based on your cadence preference:
#   - */15 * * * *  = every 15 min (recommended during SPC ENH+ days)
#   - 0 * * * *     = every hour (recommended quiet days)
python ~/.hermes/skills/weather-monitor/scripts/cadence.py
```

### 2. Test the orchestrator in dry-run

```bash
# Set env vars
export HOME_LAT=39.8645108
export HOME_LON=-84.1321902
export HOME_ZIP=45424
export HOME_COUNTY="Montgomery County, OH"
export AGENTMAIL_API_KEY=am_us_xxx
export AGENTMAIL_INBOX=weatherbot@agentmail.to
export ALERT_RECIPIENTS=alice@example.com,bob@example.com

# Dry-run
python scripts/orchestrate_alert.py --dry-run

# Force a level-2 send (after approval)
python scripts/orchestrate_alert.py --send --level 2
```

### 3. Schedule the daily health check

Drop `agentmail-daily-healthcheck.json` into your Hermes cron list. It will fire at 09:00 local time every day.

## Exit Codes (orchestrate_alert.py)

| Code | Meaning |
|---|---|
| 0 | No action needed (level=none) |
| 1 | Error (missing config, etc.) |
| 2 | Escalation detected but email not sent (cooldown, out of scope, or requires confirmation) |
| 3 | Email sent successfully |

## Anti-Spam Cooldowns

| Rule | Default | Override env var |
|---|---|---|
| Same level | 30 min | `COOLDOWN_SAME_LEVEL` |
| Escalation | 5 min | `COOLDOWN_ESCALATION` |

These match the values documented in `.env.example`.