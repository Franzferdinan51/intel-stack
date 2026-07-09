# FAQ

## Why a separate stack repo?

This stack started as inline skills in a private agent runtime. The original skills were tightly coupled to a specific person, location, and recipient list. By splitting them into a standalone repo with env-driven configuration, anyone can clone it and adapt it for their own home location, recipient list, and escalation rules.

## Why 8 skills, not 1?

Each skill has one job. The architecture supports **multiple domains** — currently weather (4 skills, 4-level ladder) and DEFCON (4 skills, 2-level ladder). All 8 share the same pull → monitor → trigger → send chain.

| Domain | Skills | Levels |
|---|---|---|
| Weather | weather-pull, weather-monitor, weather-email-trigger, weather-email-send | 4-level ladder (Watch / URGENT UPDATE / Storm Alert / WAKE-UP CALL) |
| DEFCON | defcon-pull, defcon-monitor-email, defcon-email-trigger, defcon-email-send | 2-level ladder (level 2 high / level 1 emergency) |

This separation lets you swap any layer independently. Want to add a Discord bot instead of email? Replace `*-email-send` and keep everything else. Want to use a different data source? Replace `*-pull`. Want different escalation rules? Replace `*-email-trigger`.

The same pattern extends to seismic, civic, air-quality, financial, or any other domain — just add 4 more skills. See [`extending.md`](extending.md).

## Why a strict geographic scope?

The #1 trust-killer for an automated alerting system is a wrong-region email. If a Tornado Warning hits Columbus and your stack sends an email about it to your Huber Heights recipients, you've trained everyone to ignore your emails — including the real ones. The scope filter prevents this by hard-rejecting anything outside the configured home area.

## Why HTML emails instead of plain text?

Three reasons:
1. **Scannability.** Color-coded alert blocks (`.alert-danger`, `.alert-warn`) draw the eye to the most important info first.
2. **Structure.** CSS stat grids + section dividers make a phone-friendly summary that doesn't require scrolling.
3. **Plain-text fallback.** We always send BOTH `text` and `html` so screen readers and text-only clients still work.

## Why AgentMail and not Gmail/SMTP directly?

- **No SMTP setup.** AgentMail handles deliverability, DKIM, SPF, bounce handling.
- **API-first.** No IMAP/POP3 parsing, no app passwords, no OAuth dance.
- **Single inbox per account.** Cleaner mental model than a full mailbox.
- **Free tier available.** Good for low-volume alerting.

If you want to swap to SendGrid, Postmark, or AWS SES, just replace the SDK calls in `weather-email-send`. The skill contract is the same.

## Why not just use NWS's CAP/ATOM feeds?

NWS publishes CAP (Common Alerting Protocol) feeds that are machine-readable. We use them indirectly via the `api.weather.gov/alerts/active` endpoint, which returns GeoJSON. This is more reliable than scraping CAP URLs and gives us polygon geometry for the geographic scope filter.

## Can I add a Slack or Discord channel?

Yes — replace `weather-email-send` with a `weather-slack-send` or `weather-discord-send` skill. Keep `weather-pull`, `weather-monitor`, and `weather-email-trigger` as-is. The trigger skill doesn't care what transport carries the alert.

## How do I test without spamming real recipients?

Set `WEATHER_DRY_RUN=1` in `.env`, or pass `--dry-run` to the orchestrator. The email renders but never sends. The orchestrator exits with code 0 (no action) or 2 (would-have-fired) so you can integrate it into CI.

## What's the minimum cadence?

15 min during active weather (SPC ENH+ or any active warning). 60 min otherwise. Polling faster than that wastes API calls — NWS doesn't refresh data faster than that for most products.

## What's the failure recovery story?

Each skill is idempotent. The state file is the single source of truth. If anything fails mid-pipeline:
- Pull fails → cron logs error, state unchanged, no email.
- Monitor fails → prior state preserved, next cron tick retries.
- Trigger fails → state unchanged, next cron tick retries.
- Send fails → state NOT updated with `last_email`, so retry is possible.

This means the worst case is a missed email, never a duplicate.

## How is this different from existing weather apps?

| | This Stack | Weather Apps |
|---|---|---|
| Source | NOAA + SPC + FEMA + local radar | Usually one of those |
| Escalation | Custom 4-level ladder | Push notification binary |
| Targeting | Your exact home lat/lon | "Your area" (city/county) |
| Send channel | Email + Telegram, configurable | App push only |
| Self-hosted | ✅ Yes | ❌ No |
| Open source | ✅ MIT | ❌ Proprietary |
| Customizable | ✅ Replace any layer | ❌ Black box |

## What's next on the roadmap?

See [`README.md`](../README.md) → "Roadmap" section. Top items: ATOM/CAP feed support, ML-based escalation prediction, SMS gateway, generic `intelligence-pull` for non-weather domains.

## How do I contribute?

See [`README.md`](../README.md) → "Contributing" section. TL;DR: open issues for bugs, PRs for fixes, but never submit real recipient emails, API keys, or anything that could identify a private individual.