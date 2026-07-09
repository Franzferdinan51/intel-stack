# Workflows

Pre-built cron definitions and orchestrator scripts that drive the intelligence stack.

## Files

| File | Type | What it does |
|---|---|---|
| `cron-weather-watchdog.json` | Hermes cron | Runs `weather-pull → monitor → trigger → send` every 15 min during active weather, every hour otherwise |
| `agentmail-daily-healthcheck.json` | Hermes cron | Daily inbox sweep with anti-injection rules (does NOT download attachments) |
| `orchestrate_alert.py` | Python script | Single-shot pipeline runner (manual operator trigger) |
| `alert-ladder.md` | Markdown ref | Visual 4-level escalation reference |

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